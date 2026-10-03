import os

import pytest
from langchain_core.embeddings.fake import DeterministicFakeEmbedding

from src.rag.ingest import carregar_indice, construir_indice
from src.rag.retriever import buscar_conhecimento


@pytest.fixture(scope="module")
def indice_fake(tmp_path_factory):
    destino = tmp_path_factory.mktemp("indice")
    emb = DeterministicFakeEmbedding(size=64)
    construir_indice(emb, destino=destino)
    return carregar_indice(emb, origem=destino)


def test_retorna_k_trechos_com_campos_para_citacao(indice_fake):
    trechos = buscar_conhecimento("qual o valor do frete?", k=3, indice=indice_fake)
    assert len(trechos) == 3
    for t in trechos:
        assert t["texto"] and t["fonte"] and t["referencia"]
        assert isinstance(t["similaridade"], float) and isinstance(t["relevante"], bool)


def test_limiar_decide_o_flag_relevante(indice_fake):
    todos = buscar_conhecimento("frete", indice=indice_fake, limiar=-1e9)
    nenhum = buscar_conhecimento("frete", indice=indice_fake, limiar=1e9)
    assert all(t["relevante"] for t in todos)
    assert not any(t["relevante"] for t in nenhum)


def test_expoe_escalar_humano_e_fila_quando_existem(indice_fake):
    trechos = buscar_conhecimento("intoxicação", k=25, indice=indice_fake)
    fila = next(t for t in trechos if t["departamento_escalonamento"] == "sac_emergencial")
    assert fila["escalar_humano"] is True
    comum = next(t for t in trechos if t["fonte"] == "empresa")
    assert comum["escalar_humano"] is False and comum["departamento_escalonamento"] is None


def test_pergunta_vazia_retorna_lista_vazia(indice_fake):
    assert buscar_conhecimento("   ", indice=indice_fake) == []


# --- integração: embeddings reais da OpenAI sobre o índice de data/index ---
OURO = [
    ("aceita vale alelo?", "FAQ-008"),
    ("qual o prazo de troca de produto perecível?", "2.1 Prazos de Solicitação"),
    ("banana em promoção", "CAMP-HORTI-FRESCO"),
    ("qual o horário do SAC?", "contatos"),
    ("qual o valor do frete?", "FAQ-001"),
    ("passei mal depois de comer a carne", "Suspeita de Intoxicação Alimentar"),
    ("fui cobrado duas vezes no cartão", "Cobrança Duplicada"),
    ("endereço da loja Aldeota", "loja-01"),
]
@pytest.mark.parametrize("pergunta,esperado", OURO)
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY")
def test_perguntas_ouro_recuperam_o_trecho_certo_no_top4(pergunta, esperado):
    trechos = buscar_conhecimento(pergunta, k=4)
    assert any(esperado in t["referencia"] for t in trechos), [t["referencia"] for t in trechos]


@pytest.mark.parametrize("pergunta", ["qual a capital da França?", "como fazer bolo de chocolate"])
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY")
def test_pergunta_fora_do_dominio_vem_sem_trecho_relevante(pergunta):
    assert not any(t["relevante"] for t in buscar_conhecimento(pergunta, k=4))


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY")
def test_pergunta_do_dominio_tem_trecho_relevante():
    assert buscar_conhecimento("qual o valor do frete?", k=4)[0]["relevante"]
