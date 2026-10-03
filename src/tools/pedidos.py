from src.db import get_conn

# Campos expostos ao agente: sem dados pessoais (CPF, telefone, e-mail, endereço, observação).
CAMPOS = ("pedido_id, status, canal, data_pedido, previsao_entrega, data_entrega, motorista,"
          " subtotal, taxa_entrega, desconto, total, forma_pagamento")


def rastrear_pedido(pedido_id: str) -> dict:
    with get_conn() as con:
        p = con.execute(f"SELECT {CAMPOS} FROM pedidos WHERE pedido_id = ?", (pedido_id,)).fetchone()
        if p is None:
            return {"encontrado": False, "aviso": f"Pedido {pedido_id} não encontrado."}
        itens = con.execute(
            "SELECT i.sku, pr.nome, i.quantidade, pr.unidade, i.preco_unitario, i.subtotal_item"
            " FROM pedido_itens i JOIN produtos pr ON pr.sku = i.sku"
            " WHERE i.pedido_id = ? ORDER BY i.id", (pedido_id,)).fetchall()
    return {"encontrado": True, **dict(p), "itens": [dict(i) for i in itens]}


def listar_pedidos_cliente(cliente_id: str) -> list[dict]:
    with get_conn() as con:
        rows = con.execute(
            "SELECT pedido_id, data_pedido, status, total FROM pedidos"
            " WHERE cliente_id = ? ORDER BY data_pedido DESC", (cliente_id,)).fetchall()
    return [dict(r) for r in rows]
