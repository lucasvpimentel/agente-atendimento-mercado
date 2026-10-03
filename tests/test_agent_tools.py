import shutil

import pytest

from src.config import DB_PATH
from src.agent_tools import criar_tools


@pytest.fixture
def db_temp(tmp_path, monkeypatch):
    copia = tmp_path / "teste.db"
    shutil.copy(DB_PATH, copia)
    monkeypatch.setattr("src.db.DB_PATH", copia)
    return copia


def _tools(cliente_id):
    return {t.name: t for t in criar_tools(cliente_id)}


def test_expoe_as_ferramentas_esperadas():
    assert set(_tools("CLI-1001")) == {
        "buscar_produto", "consultar_estoque", "sugerir_substitutos", "rastrear_pedido",
        "listar_meus_pedidos", "buscar_conhecimento", "abrir_ticket"}


def test_ferramentas_de_catalogo_nao_exigem_identificacao():
    r = _tools(None)["buscar_produto"].invoke({"termo": "banana"})
    assert any(p["sku"] == "HORT-001" for p in r)


@pytest.mark.parametrize("nome,args", [
    ("rastrear_pedido", {"pedido_id": "PED-84915"}),
    ("listar_meus_pedidos", {}),
    ("abrir_ticket", {"pedido_id": None, "motivo": "outro", "descricao": "x",
                      "prioridade": "baixa", "departamento": "sac_geral"}),
])
def test_ferramentas_de_conta_exigem_cliente_identificado(nome, args, db_temp):
    r = _tools(None)[nome].invoke(args)
    assert "identific" in str(r).lower()


def test_rastreia_pedido_do_proprio_cliente(db_temp):
    r = _tools("CLI-1003")["rastrear_pedido"].invoke({"pedido_id": "PED-84915"})
    assert r["encontrado"] is True and r["status"] == "em_rota"


def test_pedido_de_outro_cliente_aparece_como_nao_encontrado_sem_vazar_itens(db_temp):
    r = _tools("CLI-1003")["rastrear_pedido"].invoke({"pedido_id": "PED-84891"})  # é do CLI-1002
    assert r["encontrado"] is False
    assert "Heineken" not in str(r) and "Picanha" not in str(r)


def test_lista_so_os_pedidos_do_cliente_da_sessao(db_temp):
    r = _tools("CLI-1002")["listar_meus_pedidos"].invoke({})
    assert [p["pedido_id"] for p in r] == ["PED-84891"]


def test_abrir_ticket_usa_o_cliente_da_sessao_e_grava(db_temp):
    r = _tools("CLI-1003")["abrir_ticket"].invoke({
        "pedido_id": "PED-84915", "motivo": "atraso_entrega", "descricao": "Atrasou.",
        "prioridade": "media", "departamento": "sac_logistica"})
    assert r["criado"] is True and r["resumo"]["cliente"]["cliente_id"] == "CLI-1003"


def test_abrir_ticket_em_pedido_alheio_e_recusado(db_temp):
    r = _tools("CLI-1003")["abrir_ticket"].invoke({
        "pedido_id": "PED-84891", "motivo": "reclamacao_avaria", "descricao": "x",
        "prioridade": "alta", "departamento": "sac_logistica"})
    assert r["criado"] is False and "não pertence" in r["erro"]


def test_abrir_ticket_rejeita_motivo_fora_da_lista():
    t = _tools("CLI-1003")["abrir_ticket"]
    with pytest.raises(Exception):
        t.invoke({"pedido_id": None, "motivo": "inventado", "descricao": "x",
                  "prioridade": "baixa", "departamento": "sac_geral"})


def test_conhecimento_devolve_so_trechos_relevantes(monkeypatch):
    monkeypatch.setattr("src.agent_tools.buscar_conhecimento", lambda p, k=4: [
        {"texto": "A", "fonte": "faq", "referencia": "FAQ-1", "similaridade": 0.6, "relevante": True,
         "escalar_humano": False, "departamento_escalonamento": None},
        {"texto": "B", "fonte": "faq", "referencia": "FAQ-2", "similaridade": 0.1, "relevante": False,
         "escalar_humano": False, "departamento_escalonamento": None}])
    r = _tools(None)["buscar_conhecimento"].invoke({"pergunta": "frete"})
    assert [t["referencia"] for t in r["trechos"]] == ["FAQ-1"]


def test_conhecimento_sem_trecho_relevante_avisa_fora_do_dominio(monkeypatch):
    monkeypatch.setattr("src.agent_tools.buscar_conhecimento", lambda p, k=4: [
        {"texto": "B", "fonte": "faq", "referencia": "FAQ-2", "similaridade": 0.0, "relevante": False,
         "escalar_humano": False, "departamento_escalonamento": None}])
    r = _tools(None)["buscar_conhecimento"].invoke({"pergunta": "capital da França"})
    assert r["trechos"] == [] and r["aviso"]
