from src.config import DB_PATH, OPENAI_MODEL
from src.db import get_conn


def test_db_path_aponta_para_supermercado_db_na_raiz():
    assert DB_PATH.name == "supermercado.db"
    assert DB_PATH.exists(), "rode `python setup_db.py` antes dos testes"


def test_modelo_padrao_e_gpt_4o_mini():
    assert OPENAI_MODEL == "gpt-4o-mini"


def test_conexao_liga_foreign_keys():
    with get_conn() as con:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_linhas_acessiveis_por_nome_de_coluna():
    with get_conn() as con:
        row = con.execute("SELECT sku, nome FROM produtos LIMIT 1").fetchone()
    assert row["sku"] and row["nome"]


def test_banco_tem_produtos_carregados():
    with get_conn() as con:
        assert con.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0


def test_fk_rejeita_pedido_de_cliente_inexistente():
    import sqlite3
    import pytest
    with get_conn() as con:
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(
                "INSERT INTO pedidos (pedido_id, cliente_id, data_pedido, status, canal,"
                " endereco_entrega, subtotal, total, forma_pagamento)"
                " VALUES ('X', 'CLI-0000', '2026-01-01T00:00:00', 'entregue', 'Site Web', 'x', 0, 0, 'PIX')"
            )
