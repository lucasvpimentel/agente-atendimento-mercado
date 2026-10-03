import yaml

from eval.run_eval import avaliar, executar, relatorio
from src.config import ROOT

CATEGORIAS = {"estoque", "substituicao", "pedido", "politica", "ticket", "privacidade", "fora_de_escopo"}
CHAVES = {"id", "categoria", "cliente", "pergunta", "espera"}
REGRAS = {"usa_alguma", "nao_usa", "contem_alguma", "nao_contem"}


def _gold():
    return yaml.safe_load((ROOT / "eval" / "gold.yaml").read_text(encoding="utf-8"))["casos"]


# --- conjunto-ouro ---
def test_gold_tem_ao_menos_15_casos_com_ids_unicos():
    casos = _gold()
    assert len(casos) >= 15
    assert len({c["id"] for c in casos}) == len(casos)


def test_gold_cobre_todas_as_categorias_e_tem_formato_valido():
    casos = _gold()
    assert {c["categoria"] for c in casos} == CATEGORIAS
    for c in casos:
        assert CHAVES <= c.keys() and c["pergunta"].strip()
        assert c["espera"] and set(c["espera"]) <= REGRAS


# --- avaliação de um caso ---
def _caso(**espera):
    return {"id": "x", "categoria": "estoque", "cliente": None, "pergunta": "?", "espera": espera}


def test_passa_quando_todas_as_regras_sao_atendidas():
    resp = {"texto": "A banana custa R$ 6,99.", "ferramentas": ["buscar_produto"]}
    caso = _caso(usa_alguma=["buscar_produto"], contem_alguma=["6,99"], nao_contem=["Paris"], nao_usa=["abrir_ticket"])
    assert avaliar(caso, resp) == []


def test_falha_se_nenhuma_ferramenta_esperada_foi_usada():
    falhas = avaliar(_caso(usa_alguma=["rastrear_pedido"]), {"texto": "ok", "ferramentas": ["buscar_produto"]})
    assert len(falhas) == 1 and "rastrear_pedido" in falhas[0]


def test_falha_se_usou_ferramenta_proibida():
    falhas = avaliar(_caso(nao_usa=["abrir_ticket"]), {"texto": "ok", "ferramentas": ["abrir_ticket"]})
    assert len(falhas) == 1 and "abrir_ticket" in falhas[0]


def test_texto_ignora_caixa_e_exige_ao_menos_um_termo():
    assert avaliar(_caso(contem_alguma=["ENTREGUE", "entrega"]), {"texto": "Foi entregue ontem", "ferramentas": []}) == []
    assert avaliar(_caso(contem_alguma=["entregue"]), {"texto": "Está em rota", "ferramentas": []})


def test_falha_se_texto_traz_termo_proibido():
    falhas = avaliar(_caso(nao_contem=["Heineken"]), {"texto": "Itens: heineken", "ferramentas": []})
    assert len(falhas) == 1 and "Heineken" in falhas[0]


# --- execução e relatório ---
def test_executa_com_um_agente_novo_por_caso_e_trata_excecao_como_falha():
    casos = [
        {**_caso(contem_alguma=["ok"]), "id": "a", "cliente": "CLI-1001"},
        {**_caso(contem_alguma=["ok"]), "id": "b", "categoria": "pedido"},
    ]
    criados = []

    def criar(cliente):
        criados.append(cliente)
        return cliente

    def conversar(agente, pergunta, thread_id="padrao"):
        if agente is None:
            raise RuntimeError("api fora")
        return {"texto": "ok", "ferramentas": []}

    resultados = executar(casos, criar, conversar)
    assert criados == ["CLI-1001", None]
    assert [r["falhas"] for r in resultados][0] == []
    assert "api fora" in resultados[1]["falhas"][0]


def test_relatorio_conta_acertos_por_categoria_e_lista_falhas():
    resultados = [
        {"id": "a", "categoria": "estoque", "falhas": []},
        {"id": "b", "categoria": "estoque", "falhas": ["faltou 6,99"]},
        {"id": "c", "categoria": "ticket", "falhas": []},
    ]
    texto = relatorio(resultados)
    assert "estoque" in texto and "1/2" in texto and "ticket" in texto and "1/1" in texto
    assert "b" in texto and "faltou 6,99" in texto
    assert "Total: 2/3" in texto
