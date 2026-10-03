"""Cria supermercado.db a partir de schema.sql e dos YAMLs em data/estruturados."""
import re
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
DB = ROOT / "supermercado.db"
DADOS = ROOT / "data" / "estruturados"
ARQ_PRODUTOS = DADOS / "cat_logo_de_produtos_e_estoque_150_itens.yaml"
ARQ_CLIENTES = DADOS / "base_de_clientes_cadastrados.yaml"
ARQ_PEDIDOS = DADOS / "hist_rico_de_pedidos_mockados.yaml"

# Campos do pedido que o YAML de pedidos deixa indentados dentro do último item.
CAMPOS_PEDIDO = ("subtotal", "taxa_entrega", "desconto", "total", "forma_pagamento",
                 "observacao_cliente", "motivo_cancelamento", "estorno_status")

# ponytail: regra fixa por tipo de ocorrência; ampliar quando surgirem outros tipos.
REGRAS_TICKET = {
    "reclamacao_avaria": ("alta", "sac_logistica"),
}


def carregar_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def carregar_pedidos(path):
    """O YAML de pedidos usa '* ' no lugar de '- ' e deixa campos do pedido dentro do último
    item e ocorrências misturadas em itens. Normaliza para {pedido..., itens, ocorrencias}."""
    texto = re.sub(r"^(\s*)\* ", r"\1- ", path.read_text(encoding="utf-8"), flags=re.M)
    pedidos = []
    for p in yaml.safe_load(texto)["pedidos"]:
        itens, ocorrencias = [], []
        for it in p.pop("itens"):
            if "sku" not in it:  # ocorrência que escapou da lista
                ocorrencias.append(it)
                continue
            for campo in CAMPOS_PEDIDO + ("ocorrencias",):
                if campo in it:
                    valor = it.pop(campo)
                    if campo != "ocorrencias":
                        p[campo] = valor
            itens.append(it)
        p["itens"], p["ocorrencias"] = itens, ocorrencias + (p.get("ocorrencias") or [])
        pedidos.append(p)
    return pedidos


def inserir(con, tabela, linhas):
    if not linhas:
        return
    cols = list(linhas[0])
    con.executemany(
        f"INSERT INTO {tabela} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        [tuple(l[c] for c in cols) for l in linhas],
    )


def main():
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))

    produtos = carregar_yaml(ARQ_PRODUTOS)["produtos"]
    for p in produtos:
        p["disponivel"] = int(bool(p["disponivel"]))
        if p["disponivel"] != int(p["estoque"] > 0):
            print(f"AVISO: {p['sku']} disponivel={p['disponivel']} inconsistente com estoque={p['estoque']}")
    inserir(con, "produtos", produtos)

    clientes = carregar_yaml(ARQ_CLIENTES)["clientes"]
    inserir(con, "clientes", clientes)
    end_cliente = {c["cliente_id"]: c["endereco"] for c in clientes}
    preco = {p["sku"]: p["preco"] for p in produtos}

    pedidos, itens, tickets = [], [], []
    for p in carregar_pedidos(ARQ_PEDIDOS):
        for it in p["itens"]:
            it["subtotal_item"] = round(it["quantidade"] * it["preco_unitario"], 2)
            if abs(it["preco_unitario"] - preco[it["sku"]]) > 0.001:
                print(f"AVISO: {p['pedido_id']}/{it['sku']} preço difere do catálogo")
            itens.append({"pedido_id": p["pedido_id"], **{k: it[k] for k in
                          ("sku", "quantidade", "preco_unitario", "subtotal_item")}})
        subtotal = p.get("subtotal", round(sum(i["subtotal_item"] for i in p["itens"]), 2))
        taxa, desc = p.get("taxa_entrega", 0.0), p.get("desconto", 0.0)
        pedidos.append({
            "pedido_id": p["pedido_id"], "cliente_id": p["cliente_id"],
            "data_pedido": p["data_pedido"], "status": p["status"], "canal": p["canal"],
            "previsao_entrega": p.get("previsao_entrega"), "data_entrega": p.get("data_entrega"),
            "motorista": p.get("motorista"),
            "endereco_entrega": p.get("endereco_entrega") or end_cliente[p["cliente_id"]],
            "subtotal": subtotal, "taxa_entrega": taxa, "desconto": desc,
            "total": p.get("total", round(subtotal + taxa - desc, 2)),
            # ponytail: pedido cancelado sem forma_pagamento no YAML; inferido pelo estorno
            "forma_pagamento": p.get("forma_pagamento") or
                               ("PIX" if "pix" in str(p.get("estorno_status", "")) else "Não informado"),
            "observacao_cliente": p.get("observacao_cliente") or p.get("motivo_cancelamento"),
        })
        for oc in p["ocorrencias"]:
            prio, depto = REGRAS_TICKET.get(oc["tipo"], ("media", "sac_geral"))
            resolvido = not str(oc["resolucao"]).lower().startswith("pendente")
            abertura = p.get("data_entrega") or p["data_pedido"]
            tickets.append({
                "ticket_id": f"TCK-2026-{len(tickets) + 1:03d}", "cliente_id": p["cliente_id"],
                "pedido_id": p["pedido_id"], "data_abertura": abertura,
                "data_fechamento": abertura if resolvido else None,
                "status": "resolvido" if resolvido else "aberto", "prioridade": prio,
                "motivo": oc["tipo"], "descricao": oc["descricao"], "resolucao": oc["resolucao"],
                "departamento_responsavel": depto,
            })

    inserir(con, "pedidos", pedidos)
    inserir(con, "pedido_itens", itens)
    inserir(con, "tickets", tickets)
    con.commit()

    violacoes = con.execute("PRAGMA foreign_key_check").fetchall()
    assert not violacoes, f"violações de FK: {violacoes}"
    print(f"Banco criado: {DB.name}")
    for t in ("produtos", "clientes", "pedidos", "pedido_itens", "tickets"):
        print(f"  {t:<13} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>4} registros")
    con.close()


if __name__ == "__main__":
    main()
