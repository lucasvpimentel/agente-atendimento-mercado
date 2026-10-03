import html
import logging
import uuid

import streamlit as st

from src import agent
from src.config import ROOT
from src.ui import (dados_cliente, destacar_protocolos, html_chips, html_cupom, listar_clientes,
                    mensagem_de_erro, primeiro_nome, sugestoes, verificar_ambiente)

st.set_page_config(page_title="Atendimento Bom Preço", page_icon="🛒")
st.markdown(f"<style>{(ROOT / 'assets' / 'estilo.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)
st.markdown('<div class="marca"><span class="etiqueta">Bom Preço</span>'
            '<span class="marca-sub">Atendimento</span></div>', unsafe_allow_html=True)

if problemas := verificar_ambiente():
    for problema in problemas:
        st.error(problema)
    st.stop()


def nova_conversa():
    st.session_state.update(thread_id=str(uuid.uuid4()), mensagens=[])


with st.sidebar:
    st.markdown('<p class="rotulo">Sua conta</p>', unsafe_allow_html=True)
    clientes = dict(listar_clientes())
    cliente = st.selectbox(
        "Entrar como (simulação)", [None, *clientes],
        format_func=lambda c: "Visitante" if c is None else f"{c} — {clientes[c]}")
    dados = dados_cliente(cliente) if cliente else None
    if dados:
        pontos = f"{dados['pontos']:,}".replace(",", ".")
        st.markdown(f'<div class="cartao"><strong>{html.escape(dados["nome"])}</strong>'
                    f'<span>{html.escape(dados["programa_fidelidade"])} · {pontos} pontos</span></div>',
                    unsafe_allow_html=True)
    st.button("Nova conversa", icon=":material/add:", width="stretch", on_click=nova_conversa)

# Trocar de cliente cria um agente e uma conversa novos (a memória é por thread).
if st.session_state.get("cliente_atual", "__nenhum__") != cliente:
    st.session_state.cliente_atual = cliente
    st.session_state.agente = agent.criar_agente(cliente)
    nova_conversa()
mensagens = st.session_state.mensagens

pergunta = st.chat_input("Escreva sua dúvida") or st.session_state.pop("pendente", None)
if pergunta:
    mensagens.append({"role": "user", "texto": pergunta})
    try:
        with st.spinner("Consultando a loja..."):
            resp = agent.conversar(st.session_state.agente, pergunta, st.session_state.thread_id)
        mensagens.append({"role": "assistant", "texto": resp["texto"], "ferramentas": resp["ferramentas"]})
    except Exception as erro:  # a UI nunca mostra traceback ao cliente; a causa vai para o log
        logging.getLogger("atendimento").exception("Falha ao responder")
        st.error(mensagem_de_erro(erro))

if not mensagens:
    saudacao = f"Olá, {primeiro_nome(dados['nome'])}." if dados else "Olá! Como podemos ajudar?"
    ajuda = ("O que você precisa hoje?" if dados else
             "Tire dúvidas sobre preços e trocas. Entre como cliente na lateral para ver seus pedidos.")
    st.markdown(f'<div class="saudacao"><h1>{html.escape(saudacao)}</h1><p>{ajuda}</p></div>',
                unsafe_allow_html=True)
    colunas = st.columns(2)
    for i, texto in enumerate(sugestoes(bool(dados))):
        colunas[i % 2].button(texto, key=f"sug{i}", width="stretch", on_click=lambda t=texto: st.session_state.update(pendente=t))

for m in mensagens:
    with st.chat_message(m["role"]):
        texto, protocolos = destacar_protocolos(m["texto"])
        st.markdown(texto)
        ferramentas = m.get("ferramentas", [])
        if "abrir_ticket" in ferramentas:
            for protocolo in protocolos:
                st.markdown(html_cupom(protocolo), unsafe_allow_html=True)
        if ferramentas:
            st.markdown(html_chips(ferramentas), unsafe_allow_html=True)

if mensagens:
    st.markdown('<p class="aviso">Respostas geradas por IA. Para casos importantes, '
                'confirme com a nossa equipe.</p>', unsafe_allow_html=True)
