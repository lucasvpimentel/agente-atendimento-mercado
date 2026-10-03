from src.tools.pedidos import listar_pedidos_cliente, rastrear_pedido


def test_pedido_em_rota_traz_motorista_e_previsao():
    r = rastrear_pedido("PED-84915")
    assert r["encontrado"] is True
    assert r["status"] == "em_rota"
    assert r["motorista"].startswith("Marcos Vinicius")
    assert r["previsao_entrega"] == "2026-10-03T09:00:00"


def test_pedido_em_separacao_nao_tem_motorista():
    r = rastrear_pedido("PED-84920")
    assert r["status"] == "em_separacao"
    assert r["motorista"] is None


def test_pedido_entregue_traz_data_de_entrega():
    assert rastrear_pedido("PED-84891")["data_entrega"] == "2026-10-02T19:55:00"


def test_itens_e_totais_do_pedido():
    r = rastrear_pedido("PED-84920")
    assert r["total"] == 66.99 and r["taxa_entrega"] == 12.0 and r["desconto"] == 5.0
    leite = next(i for i in r["itens"] if i["sku"] == "LATI-001")
    assert leite["nome"].startswith("Leite UHT") and leite["quantidade"] == 6


def test_pedido_inexistente_retorna_nao_encontrado():
    r = rastrear_pedido("PED-00000")
    assert r["encontrado"] is False
    assert "não encontrado" in r["aviso"]


def test_resposta_nao_expoe_dados_pessoais():
    r = rastrear_pedido("PED-84920")
    texto = str(r)
    for proibido in ("cpf", "telefone", "email", "99123-4567", "mariana.ribeiro", "123.***"):
        assert proibido not in texto.lower()


def test_listar_pedidos_do_cliente_mais_recente_primeiro():
    r = listar_pedidos_cliente("CLI-1002")
    assert [p["pedido_id"] for p in r] == ["PED-84891"]
    datas = [p["data_pedido"] for p in listar_pedidos_cliente("CLI-1001")]
    assert datas == sorted(datas, reverse=True)


def test_listar_cliente_sem_pedidos_retorna_lista_vazia():
    assert listar_pedidos_cliente("CLI-0000") == []
