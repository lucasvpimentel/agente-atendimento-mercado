"""Gera o índice FAISS em data/index a partir de data/rag (usa a API de embeddings da OpenAI)."""
from collections import Counter

from src.rag.ingest import carregar_documentos, construir_indice

if __name__ == "__main__":
    contagem = Counter(d.metadata["fonte"] for d in carregar_documentos())
    construir_indice()
    print("Índice criado em data/index")
    for fonte, n in sorted(contagem.items()):
        print(f"  {fonte:<9} {n:>3} documentos")
