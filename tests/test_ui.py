import pytest
from streamlit.testing.v1 import AppTest

from src.config import ROOT
from src.ui import destacar_protocolos, listar_clientes, mensagem_de_erro

APP = ROOT / "app.py"


# --- helpers puros ---
def test_destaca_protocolo_em_negrito_e_lista_os_encontrados():
    texto, protocolos = destacar_protocolos("Abri o ticket TCK-2026-002 para você. Antes: TCK-2026-001.")
    assert "**TCK-2026-002**" in texto and "**TCK-2026-001**" in texto
    assert protocolos == ["TCK-2026-002", "TCK-2026-001"]


def test_texto_sem_protocolo_fica_igual():
    assert destacar_protocolos("Sem ticket aqui.") == ("Sem ticket aqui.", [])


def test_nao_duplica_negrito_em_protocolo_ja_destacado():
    texto, _ = destacar_protocolos("Protocolo **TCK-2026-002**")
    assert texto == "Protocolo **TCK-2026-002**"


class AuthenticationError(Exception): ...
class RateLimitError(Exception): ...
class APIConnectionError(Exception): ...


@pytest.mark.parametrize("erro,trecho", [
    (AuthenticationError("Incorrect API key sk-secret123"), "chave"),
    (RateLimitError("429"), "muitas"),
    (APIConnectionError("timeout"), "conexão"),
    (RuntimeError("boom"), "inesperado"),
])
def test_mensagem_de_erro_amigavel_sem_vazar_detalhes(erro, trecho):
    msg = mensagem_de_erro(erro)
    assert trecho in msg.lower()
    assert "sk-secret123" not in msg and "Traceback" not in msg


def test_lista_clientes_do_banco():
    clientes = listar_clientes()
    assert len(clientes) == 8 and clientes[0][0] == "CLI-1001"


# --- app (AppTest com agente falso) ---
@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    chamadas = []

    def conversar_falso(agente, mensagem, thread_id="padrao"):
        chamadas.append((agente, mensagem, thread_id))
        if "erro" in mensagem:
            raise RuntimeError("boom")
        if "ticket" in mensagem:
            return {"texto": "Abri o ticket TCK-2026-002.", "ferramentas": ["abrir_ticket"]}
        return {"texto": "R$ 6,99 o kg.", "ferramentas": ["buscar_produto"]}

    monkeypatch.setattr("src.agent.criar_agente", lambda cliente_id=None, llm=None: f"agente:{cliente_id}")
    monkeypatch.setattr("src.agent.conversar", conversar_falso)
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    at.chamadas = chamadas
    return at


def test_app_abre_sem_erros_e_pede_mensagem(app):
    assert not app.exception
    assert len(app.chat_input) == 1


def test_responde_e_mostra_ferramentas_usadas(app):
    app.chat_input[0].set_value("quanto custa banana?").run()
    textos = [m.markdown[0].value for m in app.chat_message]
    assert "quanto custa banana?" in textos and "R$ 6,99 o kg." in textos
    assert any("buscar_produto" in c.value for c in app.caption)


def test_ticket_destaca_protocolo_e_avisa_transbordo(app):
    app.chat_input[0].set_value("quero abrir ticket").run()
    assert any("TCK-2026-002" in w.value for w in app.warning)
    assert any("**TCK-2026-002**" in m.markdown[0].value for m in app.chat_message)


def test_erro_do_agente_vira_mensagem_amigavel(app):
    app.chat_input[0].set_value("provoque erro").run()
    assert not app.exception
    assert len(app.error) == 1 and "inesperado" in app.error[0].value.lower()
    assert "boom" not in app.error[0].value


def test_trocar_de_cliente_recria_agente_e_limpa_conversa(app):
    app.chat_input[0].set_value("oi").run()
    app.sidebar.selectbox[0].select("CLI-1002").run()
    assert len(app.chat_message) == 0
    app.chat_input[0].set_value("de novo").run()
    assert app.chamadas[-1][0] == "agente:CLI-1002"
    assert app.chamadas[-1][2] != app.chamadas[0][2]  # thread nova


def test_sem_chave_da_openai_mostra_erro_e_nao_quebra(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not at.exception
    assert any("OPENAI_API_KEY" in e.value for e in at.error)
