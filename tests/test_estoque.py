from src.tools.estoque import buscar_produto, consultar_estoque


def test_busca_banana_retorna_preco_unidade_e_secao():
    achados = {p["sku"]: p for p in buscar_produto("banana")}
    banana = achados["HORT-001"]
    assert banana["preco"] == 6.99
    assert banana["unidade"] == "kg"
    assert banana["secao"] == "Banca Central"
    assert banana["disponivel"] is True


def test_busca_ignora_acento_e_caixa():
    skus = [p["sku"] for p in buscar_produto("HIDROPONICA")]
    assert "HORT-004" in skus


def test_busca_com_varias_palavras_exige_todas():
    skus = [p["sku"] for p in buscar_produto("alface crespa")]
    assert skus == ["HORT-004"]


def test_termo_sem_resultado_retorna_lista_vazia():
    assert buscar_produto("produto-que-nao-existe-xyz") == []


def test_termo_vazio_retorna_lista_vazia():
    assert buscar_produto("   ") == []


def test_item_sem_estoque_vem_marcado_indisponivel():
    alface = consultar_estoque("HORT-004")
    assert alface["disponivel"] is False
    assert alface["estoque"] == 0


def test_busca_lista_disponiveis_antes_dos_indisponiveis():
    resultados = buscar_produto("a")
    flags = [p["disponivel"] for p in resultados]
    assert flags == sorted(flags, reverse=True)


def test_consultar_sku_inexistente_retorna_none():
    assert consultar_estoque("XXXX-999") is None
