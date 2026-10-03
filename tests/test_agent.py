from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src.agent import conversar, criar_agente
from src.prompts import montar_prompt


class LLMFalso(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def _chamada(nome, **args):
    return AIMessage(content="", tool_calls=[{"name": nome, "args": args, "id": "1"}])


def _agente(*respostas, cliente_id="CLI-1001"):
    return criar_agente(cliente_id, llm=LLMFalso(messages=iter(respostas)))


def test_executa_a_ferramenta_pedida_pelo_modelo_e_devolve_a_resposta_final():
    agente = _agente(_chamada("buscar_produto", termo="banana"), AIMessage(content="R$ 6,99 o kg."))
    r = conversar(agente, "quanto custa banana?")
    assert r["texto"] == "R$ 6,99 o kg."
    assert r["ferramentas"] == ["buscar_produto"]


def test_resposta_sem_ferramenta_lista_vazia():
    r = conversar(_agente(AIMessage(content="Olá!")), "oi")
    assert r == {"texto": "Olá!", "ferramentas": []}


def test_ferramentas_do_turno_nao_incluem_as_de_turnos_anteriores():
    agente = _agente(_chamada("buscar_produto", termo="leite"), AIMessage(content="ok"),
                     AIMessage(content="de nada"))
    conversar(agente, "leite?", thread_id="t1")
    assert conversar(agente, "obrigado", thread_id="t1")["ferramentas"] == []


def test_memoria_e_separada_por_thread():
    agente = _agente(AIMessage(content="a"), AIMessage(content="b"))
    conversar(agente, "primeira", thread_id="x")
    conversar(agente, "outra", thread_id="y")
    estado = agente.get_state({"configurable": {"thread_id": "x"}}).values["messages"]
    assert [m.content for m in estado] == ["primeira", "a"]


def test_prompt_identifica_o_cliente_e_proibe_inventar_dados():
    com = montar_prompt("CLI-1001")
    assert "CLI-1001" in com and "Nunca invente" in com and "abrir_ticket" in com
    assert "NÃO está identificado" in montar_prompt(None)
    assert "sem perguntar antes" in com  # substitutos vêm junto com o aviso de indisponibilidade
