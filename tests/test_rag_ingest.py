from collections import Counter

from langchain_core.embeddings.fake import DeterministicFakeEmbedding

from src.rag.ingest import carregar_documentos, carregar_indice, construir_indice


def _por_fonte(docs):
    return Counter(d.metadata["fonte"] for d in docs)


def test_um_documento_por_entrada_logica():
    contagem = _por_fonte(carregar_documentos())
    assert contagem == {"faq": 10, "promocao": 4, "politica": 8, "empresa": 3}


def test_todo_documento_tem_fonte_e_texto():
    for d in carregar_documentos():
        assert d.metadata["fonte"]
        assert d.page_content.strip()


def test_faq_junta_pergunta_resposta_e_metadados():
    faq = next(d for d in carregar_documentos() if d.metadata.get("id") == "FAQ-001")
    assert "frete" in faq.page_content.lower() and "R$ 14,90" in faq.page_content
    assert faq.metadata["escalar_humano"] is False
    assert faq.metadata["categoria"] == "Compras Online e Delivery"


def test_politica_nao_corta_regra_ao_meio_e_traz_o_titulo():
    docs = [d for d in carregar_documentos() if d.metadata["fonte"] == "politica"]
    troca = next(d for d in docs if "2.1" in d.metadata["secao"])
    assert "24 horas" in troca.page_content and "7 dias" in troca.page_content
    assert "Prazos de Solicitação" in troca.page_content
    assert all(len(d.page_content) < 2500 for d in docs)


def test_matriz_de_transbordo_vira_documento_proprio():
    docs = [d for d in carregar_documentos() if d.metadata["fonte"] == "politica"]
    matriz = next(d for d in docs if "sac_emergencial" in d.page_content)
    assert "Intoxicação" in matriz.page_content and "financeiro_cobranca" in matriz.page_content


def test_promocao_traz_itens_precos_regras_e_vigencia():
    camp = next(d for d in carregar_documentos() if d.metadata.get("id") == "CAMP-HORTI-FRESCO")
    assert "HORT-001" in camp.page_content and "4.99" in camp.page_content
    assert camp.metadata["vigencia_fim"] == "2026-10-04"


def test_promocao_com_itens_sem_sku_nao_quebra():
    camp = next(d for d in carregar_documentos() if d.metadata.get("id") == "CAMP-FIDELIDADE-OURO")
    assert "Frete grátis automático" in camp.page_content


def test_indice_persiste_e_recarrega_sem_reindexar(tmp_path):
    emb = DeterministicFakeEmbedding(size=32)
    construir_indice(emb, destino=tmp_path)
    assert (tmp_path / "index.faiss").exists()
    indice = carregar_indice(emb, origem=tmp_path)
    assert len(indice.similarity_search("frete", k=3)) == 3
