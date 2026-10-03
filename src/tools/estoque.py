import unicodedata

from src.db import get_conn

COLUNAS = "sku, nome, categoria, preco, unidade, estoque, secao, disponivel"


def _norm(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _produto(row) -> dict:
    return {**dict(row), "disponivel": bool(row["disponivel"])}


def buscar_produto(termo: str, limite: int = 10) -> list[dict]:
    """Produtos cujo nome contém todas as palavras do termo (sem acento, sem caixa).
    Disponíveis primeiro."""
    palavras = _norm(termo).split()
    if not palavras:
        return []
    # ponytail: varre os ~160 produtos em Python; trocar por FTS5 se o catálogo crescer muito
    with get_conn() as con:
        rows = con.execute(f"SELECT {COLUNAS} FROM produtos ORDER BY nome").fetchall()
    achados = [_produto(r) for r in rows if all(p in _norm(r["nome"]) for p in palavras)]
    achados.sort(key=lambda p: not p["disponivel"])
    return achados[:limite]


def consultar_estoque(sku: str) -> dict | None:
    with get_conn() as con:
        row = con.execute(f"SELECT {COLUNAS} FROM produtos WHERE sku = ?", (sku,)).fetchone()
    return _produto(row) if row else None
