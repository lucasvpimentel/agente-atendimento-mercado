from src.tools.estoque import consultar_estoque
from src.tools.substituicao import sugerir_substitutos


def test_alface_indisponivel_sugere_so_hortifruti_com_estoque():
    r = sugerir_substitutos("HORT-004")
    assert r["aviso"] is None
    assert len(r["substitutos"]) == 3
    for s in r["substitutos"]:
        assert s["categoria"] == "Hortifrúti"
        assert s["estoque"] > 0 and s["disponivel"] is True


def test_nunca_sugere_o_proprio_sku():
    skus = [s["sku"] for s in sugerir_substitutos("HORT-004", limite=50)["substitutos"]]
    assert "HORT-004" not in skus


def test_prioriza_mesma_unidade_e_preco_mais_proximo():
    original = consultar_estoque("HORT-004")  # un, 3.79
    subs = sugerir_substitutos("HORT-004", limite=50)["substitutos"]
    chaves = [(s["unidade"] != original["unidade"], abs(s["preco"] - original["preco"])) for s in subs]
    assert chaves == sorted(chaves)


def test_respeita_limite():
    assert len(sugerir_substitutos("HORT-004", limite=1)["substitutos"]) == 1


def test_produto_disponivel_nao_precisa_de_substituto():
    r = sugerir_substitutos("HORT-001")
    assert r["substitutos"] == []
    assert "disponível" in r["aviso"]


def test_sku_inexistente_retorna_aviso():
    r = sugerir_substitutos("XXXX-999")
    assert r["substitutos"] == []
    assert "não encontrado" in r["aviso"]
