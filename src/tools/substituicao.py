from pydantic import BaseModel, Field

from src.config import OPENAI_MODEL, TEMPERATURE
from src.db import get_conn
from src.tools.estoque import COLUNAS, _produto, consultar_estoque


def sugerir_substitutos(sku: str, limite: int = 3) -> dict:
    """Itens da mesma categoria com estoque, preferindo mesma unidade e preço mais próximo."""
    original = consultar_estoque(sku)
    if original is None:
        return {"aviso": f"Produto {sku} não encontrado.", "substitutos": []}
    if original["disponivel"]:
        return {"aviso": f"{original['nome']} já está disponível.", "substitutos": []}
    with get_conn() as con:
        rows = con.execute(
            f"SELECT {COLUNAS} FROM produtos"
            " WHERE categoria = ? AND estoque > 0 AND disponivel = 1 AND sku != ?"
            " ORDER BY unidade != ?, ABS(preco - ?), sku LIMIT ?",
            (original["categoria"], sku, original["unidade"], original["preco"], limite),
        ).fetchall()
    return {"aviso": None, "substitutos": [_produto(r) for r in rows]}


class Sugestao(BaseModel):
    sku: str
    motivo: str = Field(description="Uma frase curta explicando por que serve como substituto.")


class Escolha(BaseModel):
    sugestoes: list[Sugestao]


PROMPT = """Um cliente de supermercado quer {nome} ({unidade}, R$ {preco:.2f}), que acabou.
Escolha até {limite} substitutos, do mais ao menos adequado, usando SOMENTE os SKUs da lista.
Considere uso culinário, tipo de produto e preço parecido. Se nenhum servir, devolva lista vazia.

Candidatos:
{lista}"""


def _llm_padrao():
    from langchain_openai import ChatOpenAI  # import tardio: testes não precisam de rede
    return ChatOpenAI(model=OPENAI_MODEL, temperature=TEMPERATURE).with_structured_output(Escolha)


def sugerir_substitutos_ia(sku: str, limite: int = 3, max_candidatos: int = 10, llm=None) -> dict:
    """A IA só vê `max_candidatos` itens (já filtrados por categoria/estoque no SQL), em formato
    compacto (sku, nome, unidade, preço). Falha, resposta vazia ou SKU fora da lista → cai na regra."""
    base = sugerir_substitutos(sku, limite=max_candidatos)
    candidatos = {p["sku"]: p for p in base["substitutos"]}
    if not candidatos:
        return {**base, "origem": "regra"}
    original = consultar_estoque(sku)
    lista = "\n".join(f"{p['sku']} | {p['nome']} | {p['unidade']} | R$ {p['preco']:.2f}"
                      for p in candidatos.values())
    try:
        escolha = (llm or _llm_padrao()).invoke(PROMPT.format(
            nome=original["nome"], unidade=original["unidade"], preco=original["preco"],
            limite=limite, lista=lista))
        # ponytail: confia no sku devolvido só se estiver na lista enviada (anti-alucinação)
        validas = [s for s in escolha.sugestoes if s.sku in candidatos][:limite]
    except Exception:
        validas = []
    if not validas:
        return {"aviso": None, "substitutos": base["substitutos"][:limite], "origem": "regra"}
    return {"aviso": None, "origem": "ia",
            "substitutos": [{**candidatos[s.sku], "motivo": s.motivo} for s in validas]}
