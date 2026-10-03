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
