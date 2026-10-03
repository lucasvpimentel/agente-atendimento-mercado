import os
import uuid

import streamlit as st

import src.config  # noqa: F401  (carrega o .env)
from src import agent
from src.ui import destacar_protocolos, listar_clientes, mensagem_de_erro

st.set_page_config(page_title="Atendimento Bom Preço", page_icon="🛒")
st.title("🛒 Atendimento Bom Preço & Cia")

if not os.getenv("OPENAI_API_KEY"):
    st.error("Defina OPENAI_API_KEY no arquivo .env para usar o assistente.")
    st.stop()

clientes = dict(listar_clientes())
cliente = st.sidebar.selectbox(
    "Cliente logado (simulação)", [None, *clientes],
    format_func=lambda c: "Não identificado" if c is None else f"{c} — {clientes[c]}")

# Trocar de cliente cria um agente e uma conversa novos (a memória é por thread).
if st.session_state.get("cliente_atual", "__nenhum__") != cliente:
    st.session_state.update(cliente_atual=cliente, agente=agent.criar_agente(cliente),
                            thread_id=str(uuid.uuid4()), mensagens=[])
mensagens = st.session_state.mensagens

if pergunta := st.chat_input("Como posso ajudar?"):
    mensagens.append({"role": "user", "texto": pergunta})
    try:
        with st.spinner("Consultando..."):
            resp = agent.conversar(st.session_state.agente, pergunta, st.session_state.thread_id)
        mensagens.append({"role": "assistant", "texto": resp["texto"], "ferramentas": resp["ferramentas"]})
    except Exception as erro:  # a UI nunca mostra traceback ao cliente
        st.error(mensagem_de_erro(erro))

for m in mensagens:
    with st.chat_message(m["role"]):
        texto, protocolos = destacar_protocolos(m["texto"])
        st.markdown(texto)
        if m.get("ferramentas"):
            st.caption("🔧 Ferramentas: " + ", ".join(dict.fromkeys(m["ferramentas"])))
        if protocolos and "abrir_ticket" in m.get("ferramentas", []):
            st.warning("Seu caso foi encaminhado para a equipe humana. Protocolo: " + ", ".join(protocolos))
