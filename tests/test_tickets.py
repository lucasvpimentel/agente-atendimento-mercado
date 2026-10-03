import shutil
from datetime import datetime

import pytest

from src.config import DB_PATH
from src.db import get_conn
from src.tools.tickets import abrir_ticket

AGORA = datetime(2026, 10, 3, 9, 30, 0)


@pytest.fixture
def con(tmp_path):
    copia = tmp_path / "teste.db"
    shutil.copy(DB_PATH, copia)
    c = get_conn(copia)
    yield c
    c.close()


def _total(con):
    return con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


def _abrir(con, **kw):
    args = dict(cliente_id="CLI-1003", pedido_id="PED-84915", motivo="atraso_entrega",
                descricao="Pedido em rota passou da previsão.", prioridade="media",
                departamento="sac_logistica", con=con, agora=AGORA)
    return abrir_ticket(**{**args, **kw})


def test_abre_ticket_com_id_sequencial_e_grava_no_banco(con):
    r = _abrir(con)
    assert r["criado"] is True
    assert r["ticket_id"] == "TCK-2026-002"  # o dataset já tem TCK-2026-001
    linha = con.execute("SELECT * FROM tickets WHERE ticket_id = ?", (r["ticket_id"],)).fetchone()
    assert linha["status"] == "aberto" and linha["data_abertura"] == "2026-10-03T09:30:00"
    assert linha["departamento_responsavel"] == "sac_logistica" and linha["data_fechamento"] is None


def test_resumo_estruturado_para_o_atendente_humano(con):
    resumo = _abrir(con)["resumo"]
    assert resumo["cliente"] == {"cliente_id": "CLI-1003", "nome": "Fernanda Albuquerque Lima",
                                 "programa_fidelidade": "Clube Ouro"}
    assert resumo["pedido"]["pedido_id"] == "PED-84915" and resumo["pedido"]["status"] == "em_rota"
    assert len(resumo["pedido"]["itens"]) == 3
    assert resumo["problema"] == "atraso_entrega" and resumo["acao_sugerida"]
    texto = str(resumo).lower()
    assert "cpf" not in texto and "telefone" not in texto and "@" not in texto


def test_avaria_com_prioridade_baixa_e_elevada_para_alta(con):
    r = _abrir(con, cliente_id="CLI-1001", pedido_id="PED-84920", motivo="reclamacao_avaria",
               prioridade="baixa")
    assert r["prioridade"] == "alta" and r["prioridade_ajustada"] is True


def test_prioridade_critica_e_mantida_para_motivo_grave(con):
    r = _abrir(con, motivo="intoxicacao_alimentar", prioridade="critica", departamento="sac_emergencial")
    assert r["prioridade"] == "critica" and r["prioridade_ajustada"] is False


def test_nao_duplica_ticket_aberto_do_mesmo_pedido_e_motivo(con):
    r = _abrir(con, cliente_id="CLI-1002", pedido_id="PED-84891", motivo="reclamacao_avaria",
               prioridade="alta")
    assert r["criado"] is False and r["ticket_id"] == "TCK-2026-001"
    assert "já" in r["aviso"].lower() and _total(con) == 1


def test_ticket_sem_pedido_e_permitido(con):
    r = _abrir(con, pedido_id=None, motivo="duvida_geral")
    assert r["criado"] is True and r["resumo"]["pedido"] is None


@pytest.mark.parametrize("campo,valor", [
    ("prioridade", "urgentissima"),
    ("departamento", "setor_inexistente"),
    ("cliente_id", "CLI-0000"),
    ("pedido_id", "PED-00000"),
    ("pedido_id", "PED-84891"),  # existe, mas é de outro cliente (CLI-1002)
    ("descricao", "  "),
])
def test_entrada_invalida_nao_grava_nada(con, campo, valor):
    r = _abrir(con, **{campo: valor})
    assert r["criado"] is False and r["erro"]
    assert _total(con) == 1


def test_falha_na_insercao_faz_rollback(con):
    con.execute("CREATE TRIGGER falha BEFORE INSERT ON tickets BEGIN SELECT RAISE(ABORT, 'boom'); END")
    r = _abrir(con)
    assert r["criado"] is False and "boom" in r["erro"]
    assert _total(con) == 1
