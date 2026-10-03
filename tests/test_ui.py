import pytest
from streamlit.testing.v1 import AppTest

from src.config import ROOT
from src.ui import (dados_cliente, destacar_protocolos, html_chips, html_cupom, listar_clientes,
                    mensagem_de_erro, primeiro_nome, rotulo_ferramenta, sugestoes, verificar_ambiente)

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


def test_dados_do_cliente_sem_informacao_pessoal_sensivel():
    d = dados_cliente("CLI-1001")
    assert d == {"nome": "Mariana Souza Ribeiro", "programa_fidelidade": "Clube Ouro", "pontos": 1420}
    assert dados_cliente("CLI-0000") is None


def test_primeiro_nome():
    assert primeiro_nome("Mariana Souza Ribeiro") == "Mariana"


@pytest.mark.parametrize("tool,rotulo", [
    ("buscar_produto", "Consultou o estoque"), ("consultar_estoque", "Consultou o estoque"),
    ("sugerir_substitutos", "Buscou substitutos"), ("rastrear_pedido", "Rastreou o pedido"),
    ("listar_meus_pedidos", "Listou seus pedidos"), ("buscar_conhecimento", "Consultou as políticas da loja"),
    ("abrir_ticket", "Abriu um ticket"), ("ferramenta_nova", "ferramenta_nova")])
def test_rotulo_amigavel_para_cada_ferramenta(tool, rotulo):
    assert rotulo_ferramenta(tool) == rotulo


def test_chips_sem_repeticao_e_com_escape():
    html = html_chips(["buscar_produto", "consultar_estoque", "<b>x</b>"])
    assert html.count("Consultou o estoque") == 1
    assert "&lt;b&gt;x&lt;/b&gt;" in html and "<b>x" not in html
    assert html_chips([]) == ""


def test_cupom_traz_o_protocolo_e_e_um_status_acessivel():
    html = html_cupom("TCK-2026-002")
    assert 'class="cupom"' in html and "TCK-2026-002" in html and 'role="status"' in html


def test_sugestoes_dependem_de_o_cliente_estar_identificado():
    logado, anonimo = sugestoes(True), sugestoes(False)
    assert len(logado) == len(anonimo) == 4
    assert any("pedido" in s.lower() for s in logado)
    assert not any("pedido" in s.lower() for s in anonimo)


# --- verificação do ambiente ---
def test_ambiente_ok_nao_reclama_de_nada(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    (tmp_path / "index.faiss").write_bytes(b"")
    monkeypatch.setattr("src.ui.find_spec", lambda nome: object())
    assert verificar_ambiente(tmp_path) == []


def test_ambiente_aponta_faiss_ausente_com_o_comando_de_correcao(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    (tmp_path / "index.faiss").write_bytes(b"")
    monkeypatch.setattr("src.ui.find_spec", lambda nome: None)
    problemas = verificar_ambiente(tmp_path)
    assert len(problemas) == 1 and "pip install -r requirements.txt" in problemas[0]


def test_ambiente_aponta_indice_ausente_e_chave_ausente(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("src.ui.find_spec", lambda nome: object())
    problemas = " ".join(verificar_ambiente(tmp_path))
    assert "build_index.py" in problemas and "OPENAI_API_KEY" in problemas


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


def _markdowns(at):
    return [m.value for m in at.markdown]


def test_app_abre_sem_erros_e_pede_mensagem(app):
    assert not app.exception
    assert len(app.chat_input) == 1


def test_tela_inicial_oferece_sugestoes_clicaveis(app):
    rotulos = [b.label for b in app.button]
    for s in sugestoes(False):
        assert s in rotulos


def test_clicar_numa_sugestao_envia_a_pergunta(app):
    sugestao = sugestoes(False)[0]
    next(b for b in app.button if b.label == sugestao).click().run()
    assert app.chamadas[-1][1] == sugestao
    assert not any(b.label == sugestao for b in app.button)  # some após a primeira mensagem


def test_responde_e_mostra_ferramentas_usadas(app):
    app.chat_input[0].set_value("quanto custa banana?").run()
    textos = [m.markdown[0].value for m in app.chat_message]
    assert "quanto custa banana?" in textos and "R$ 6,99 o kg." in textos
    assert any("Consultou o estoque" in v for v in _markdowns(app))


def test_ticket_mostra_cupom_com_protocolo(app):
    app.chat_input[0].set_value("quero abrir ticket").run()
    cupons = [v for v in _markdowns(app) if 'class="cupom"' in v]
    assert len(cupons) == 1 and "TCK-2026-002" in cupons[0]


def test_erro_do_agente_e_registrado_no_log_com_a_causa(app, caplog):
    with caplog.at_level("ERROR", logger="atendimento"):
        app.chat_input[0].set_value("provoque erro").run()
    assert "boom" in caplog.text


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


def test_cartao_do_cliente_mostra_nome_clube_e_pontos(app):
    app.sidebar.selectbox[0].select("CLI-1001").run()
    lateral = " ".join(m.value for m in app.sidebar.markdown)
    assert "Mariana" in lateral and "Clube Ouro" in lateral and "1.420" in lateral
    assert any("Mariana" in v for v in _markdowns(app))  # saudação na tela inicial


def test_nova_conversa_limpa_historico_e_troca_de_thread(app):
    app.chat_input[0].set_value("oi").run()
    app.sidebar.button[0].click().run()
    assert len(app.chat_message) == 0
    app.chat_input[0].set_value("oi de novo").run()
    assert app.chamadas[-1][2] != app.chamadas[0][2]


def test_sem_chave_da_openai_mostra_erro_e_nao_quebra(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not at.exception
    assert any("OPENAI_API_KEY" in e.value for e in at.error)


def test_ambiente_incompleto_mostra_o_que_fazer_e_nao_quebra(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setattr("src.ui.find_spec", lambda nome: None)
    at = AppTest.from_file(str(APP), default_timeout=15).run()
    assert not at.exception
    assert any("pip install -r requirements.txt" in e.value for e in at.error)
