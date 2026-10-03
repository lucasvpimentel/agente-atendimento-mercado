from functools import lru_cache

from src.config import RAG_LIMIAR
from src.rag.ingest import carregar_indice


@lru_cache(maxsize=1)
def _indice_padrao():
    return carregar_indice()


def buscar_conhecimento(pergunta: str, k: int = 4, limiar: float = RAG_LIMIAR, indice=None) -> list[dict]:
    """Top-k trechos de política/FAQ/promoção/empresa para a pergunta.

    `similaridade` é o cosseno (os embeddings da OpenAI são normalizados, então cosseno = 1 - d²/2
    sobre a distância L2 do FAISS). `relevante` = similaridade >= limiar; se nenhum trecho for
    relevante, a pergunta provavelmente está fora do domínio e o agente não deve citá-los.
    """
    if not pergunta.strip():
        return []
    achados = (indice or _indice_padrao()).similarity_search_with_score(pergunta, k=k)
    trechos = []
    for doc, dist in achados:
        sim = round(1 - float(dist) ** 2 / 2, 3)
        meta = doc.metadata
        trechos.append({
            "texto": doc.page_content,
            "fonte": meta["fonte"],
            "referencia": meta.get("id") or meta.get("secao"),
            "similaridade": sim,
            "relevante": sim >= limiar,
            "escalar_humano": meta.get("escalar_humano", False),
            "departamento_escalonamento": meta.get("departamento_escalonamento"),
        })
    return trechos
