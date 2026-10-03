import sqlite3
from datetime import datetime

from src.db import get_conn

PRIORIDADES = ("baixa", "media", "alta", "critica")
# Filas da matriz de transbordo do manual (seção 4) + as usadas nos tickets do dataset.
DEPARTAMENTOS = ("sac_emergencial", "financeiro_cobranca", "sac_logistica", "sac_relacionamento",
                 "sac_operacoes", "sac_financeiro", "sac_geral")
# Motivos que nunca podem ficar abaixo de "alta" (item avariado, vencido, risco à saúde, reclamação grave).
MOTIVOS_GRAVES = {"reclamacao_avaria", "produto_vencido", "intoxicacao_alimentar", "reclamacao_grave"}
ACAO_SUGERIDA = "Contatar o cliente, validar o ocorrido e definir estorno, crédito ou reenvio conforme o manual."


def _erro(msg: str) -> dict:
    return {"criado": False, "erro": msg}


def _resumo(con, cliente, pedido_id, motivo, descricao, departamento, prioridade) -> dict:
    pedido = None
    if pedido_id:
        p = con.execute("SELECT pedido_id, status, total, previsao_entrega FROM pedidos WHERE pedido_id = ?",
                        (pedido_id,)).fetchone()
        itens = con.execute(
            "SELECT i.sku, pr.nome, i.quantidade FROM pedido_itens i JOIN produtos pr ON pr.sku = i.sku"
            " WHERE i.pedido_id = ? ORDER BY i.id", (pedido_id,)).fetchall()
        pedido = {**dict(p), "itens": [dict(i) for i in itens]}
    return {
        "cliente": {k: cliente[k] for k in ("cliente_id", "nome", "programa_fidelidade")},
        "pedido": pedido, "problema": motivo, "descricao": descricao,
        "acao_sugerida": f"{ACAO_SUGERIDA} Fila: {departamento} (prioridade {prioridade}).",
    }


def abrir_ticket(cliente_id: str, pedido_id: str | None, motivo: str, descricao: str,
                 prioridade: str, departamento: str, con=None, agora: datetime | None = None) -> dict:
    """Única tool que escreve no banco. Valida tudo antes de gravar e grava em transação."""
    if prioridade not in PRIORIDADES:
        return _erro(f"Prioridade inválida: {prioridade}. Use {', '.join(PRIORIDADES)}.")
    if departamento not in DEPARTAMENTOS:
        return _erro(f"Departamento inválido: {departamento}. Use {', '.join(DEPARTAMENTOS)}.")
    if not descricao.strip() or not motivo.strip():
        return _erro("Motivo e descrição são obrigatórios.")

    propria = con is None
    con = con or get_conn()
    try:
        con.execute("BEGIN IMMEDIATE")
        cliente = con.execute("SELECT cliente_id, nome, programa_fidelidade FROM clientes"
                              " WHERE cliente_id = ?", (cliente_id,)).fetchone()
        if cliente is None:
            raise ValueError(f"Cliente {cliente_id} não encontrado.")
        if pedido_id:
            dono = con.execute("SELECT cliente_id FROM pedidos WHERE pedido_id = ?", (pedido_id,)).fetchone()
            if dono is None:
                raise ValueError(f"Pedido {pedido_id} não encontrado.")
            if dono["cliente_id"] != cliente_id:
                raise ValueError(f"Pedido {pedido_id} não pertence ao cliente {cliente_id}.")
            aberto = con.execute(
                "SELECT ticket_id FROM tickets WHERE pedido_id = ? AND motivo = ? AND status = 'aberto'",
                (pedido_id, motivo)).fetchone()
            if aberto:
                con.rollback()
                return {"criado": False, "ticket_id": aberto["ticket_id"],
                        "aviso": f"Já existe o ticket {aberto['ticket_id']} aberto para este pedido e motivo."}

        ajustada = motivo in MOTIVOS_GRAVES and PRIORIDADES.index(prioridade) < PRIORIDADES.index("alta")
        if ajustada:
            prioridade = "alta"
        agora = agora or datetime.now()
        prefixo = f"TCK-{agora.year}-"
        ultimo = con.execute("SELECT MAX(ticket_id) FROM tickets WHERE ticket_id LIKE ?",
                             (prefixo + "%",)).fetchone()[0]
        ticket_id = f"{prefixo}{(int(ultimo.rsplit('-', 1)[1]) if ultimo else 0) + 1:03d}"
        con.execute(
            "INSERT INTO tickets (ticket_id, cliente_id, pedido_id, data_abertura, status, prioridade,"
            " motivo, descricao, departamento_responsavel) VALUES (?, ?, ?, ?, 'aberto', ?, ?, ?, ?)",
            (ticket_id, cliente_id, pedido_id, agora.isoformat(timespec="seconds"), prioridade,
             motivo, descricao, departamento))
        resumo = _resumo(con, cliente, pedido_id, motivo, descricao, departamento, prioridade)
        con.commit()
    except (ValueError, sqlite3.Error) as e:
        con.rollback()
        return _erro(str(e))
    finally:
        if propria:
            con.close()
    return {"criado": True, "ticket_id": ticket_id, "status": "aberto", "prioridade": prioridade,
            "prioridade_ajustada": ajustada, "departamento": departamento, "resumo": resumo}
