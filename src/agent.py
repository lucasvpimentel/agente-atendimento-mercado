from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from src.agent_tools import criar_tools
from src.config import OPENAI_MODEL, TEMPERATURE
from src.prompts import montar_prompt


def criar_agente(cliente_id: str | None = None, llm=None):
    """Agente com memória por `thread_id`. `cliente_id` é o cliente já autenticado pelo canal."""
    if llm is None:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=OPENAI_MODEL, temperature=TEMPERATURE)
    return create_agent(llm, criar_tools(cliente_id), system_prompt=montar_prompt(cliente_id),
                        checkpointer=InMemorySaver())


def conversar(agente, mensagem: str, thread_id: str = "padrao") -> dict:
    """Envia uma mensagem; devolve o texto final e as ferramentas usadas neste turno."""
    mensagens = agente.invoke({"messages": [{"role": "user", "content": mensagem}]},
                              config={"configurable": {"thread_id": thread_id}})["messages"]
    turno = mensagens[max(i for i, m in enumerate(mensagens) if isinstance(m, HumanMessage)):]
    ferramentas = [c["name"] for m in turno if isinstance(m, AIMessage) for c in m.tool_calls]
    return {"texto": mensagens[-1].content, "ferramentas": ferramentas}
