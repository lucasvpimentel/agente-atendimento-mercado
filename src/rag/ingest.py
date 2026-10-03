import re
from pathlib import Path

import yaml
from langchain_core.documents import Document

from src.config import EMBEDDING_MODEL, INDEX_DIR, RAG_DIR

ARQ_FAQ = RAG_DIR / "base_de_conhecimento_supermercado.yaml"
ARQ_PROMO = RAG_DIR / "promo_es_ativas.yaml"
ARQ_POLITICAS = RAG_DIR / "manual_de_pol_ticas_operacionais.yaml"


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _docs_faq_e_empresa() -> list[Document]:
    base = _yaml(ARQ_FAQ)
    categorias = {c["id"]: c["nome"] for c in base["categorias"]}
    docs = []
    for f in base["itens_faq"]:
        texto = (f"Pergunta: {f['pergunta']}\nResposta: {' '.join(f['resposta'].split())}\n"
                 f"Palavras-chave: {', '.join(f['palavras_chave'])}")
        docs.append(Document(texto, metadata={
            "fonte": "faq", "id": f["id"], "categoria": categorias[f["categoria_id"]],
            "escalar_humano": f["escalar_humano"],
            "departamento_escalonamento": f.get("departamento_escalonamento")}))

    emp = base["empresa"]
    contatos = "\n".join(f"{k.replace('_', ' ')}: {v}" for k, v in emp["contatos"].items())
    docs.append(Document(f"{emp['nome']} - contatos e canais de atendimento (SAC)\n{contatos}",
                         metadata={"fonte": "empresa", "id": "contatos"}))
    for u in emp["unidades"]:
        docs.append(Document(
            f"{u['nome']}\nEndereço: {u['endereco']}\nTelefone: {u['telefone']}\n"
            f"Estacionamento: {u['estacionamento']}",
            metadata={"fonte": "empresa", "id": u["id"]}))
    return docs


def _docs_promocoes() -> list[Document]:
    docs = []
    for c in _yaml(ARQ_PROMO)["campanhas_ativas"]:
        linhas = [f"Campanha: {c['nome']} ({c['vigencia_inicio']} a {c['vigencia_fim']})",
                  f"Benefício: {c['tipo_beneficio']}", c["descricao"], "Itens e regras:"]
        for i in c["itens"]:
            if "sku" not in i:
                linhas.append(f"- Regra: {i['regra']}")
                continue
            preco = f"R$ {i['preco_regular']:.2f}"
            if "preco_promocional" in i:
                preco += f" por R$ {i['preco_promocional']:.2f}"
            linhas.append(f"- {i['sku']} {i['nome']}: {preco}{'/' + i['unidade'] if 'unidade' in i else ''}."
                          f" Regra: {i['regra']}")
        docs.append(Document("\n".join(linhas), metadata={
            "fonte": "promocao", "id": c["id"],
            "vigencia_inicio": c["vigencia_inicio"], "vigencia_fim": c["vigencia_fim"]}))
    return docs


def _docs_politicas() -> list[Document]:
    """O manual é Markdown (apesar da extensão .yaml): um documento por subseção (###),
    mais um por seção (##) que tenha texto próprio (ex.: a matriz de triagem)."""
    docs, h2, h3, corpo = [], "", None, []

    def fecha():
        texto = "\n".join(l for l in corpo if l.strip() != "---").strip()
        if h2 and texto:
            secao = h3 or h2
            docs.append(Document(
                f"Manual de Políticas Operacionais - {h2}\n{h3 + chr(10) if h3 else ''}\n{texto}",
                metadata={"fonte": "politica", "secao": secao}))

    for linha in ARQ_POLITICAS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(##|###) (.+)", linha)
        if m:
            fecha()
            corpo = []
            if m.group(1) == "##":
                h2, h3 = m.group(2).strip(), None
            else:
                h3 = m.group(2).strip()
        else:
            corpo.append(linha)
    fecha()
    return docs


def carregar_documentos() -> list[Document]:
    return _docs_faq_e_empresa() + _docs_promocoes() + _docs_politicas()


def construir_indice(embeddings=None, destino: Path = INDEX_DIR):
    from langchain_community.vectorstores import FAISS
    embeddings = embeddings or _embeddings_padrao()
    indice = FAISS.from_documents(carregar_documentos(), embeddings)
    indice.save_local(str(destino))
    return indice


def carregar_indice(embeddings=None, origem: Path = INDEX_DIR):
    from langchain_community.vectorstores import FAISS
    # índice é gerado localmente por construir_indice, então a desserialização é confiável
    return FAISS.load_local(str(origem), embeddings or _embeddings_padrao(),
                            allow_dangerous_deserialization=True)


def _embeddings_padrao():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)
