"""Cenários ponta a ponta com o GPT-4o-mini e embeddings reais. Rodam num banco temporário."""
import os
import shutil

import pytest

from src.agent import conversar, criar_agente
from src.config import DB_PATH

pytestmark = [pytest.mark.integration,
              pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY")]


@pytest.fixture(autouse=True)
def db_temp(tmp_path, monkeypatch):
    copia = tmp_path / "teste.db"
    shutil.copy(DB_PATH, copia)
    monkeypatch.setattr("src.db.DB_PATH", copia)
    return copia


def test_produto_indisponivel_sugere_substitutos():
    r = conversar(criar_agente("CLI-1001"), "Vocês têm alface crespa hidropônica?")
    assert "sugerir_substitutos" in r["ferramentas"]
    assert r["texto"]


def test_rastreia_pedido_do_cliente():
    r = conversar(criar_agente("CLI-1003"), "Onde está meu pedido PED-84915?")
    assert "rastrear_pedido" in r["ferramentas"]
    assert any(s in r["texto"] for s in ("09:00", "9h", "9:00", "09h", "Marcos"))


def test_politica_vem_do_rag():
    r = conversar(criar_agente("CLI-1001"), "Qual o prazo para pedir troca de um produto perecível?")
    assert "buscar_conhecimento" in r["ferramentas"]
    assert "24" in r["texto"]


def test_avaria_abre_ticket_e_informa_protocolo(db_temp):
    r = conversar(criar_agente("CLI-1003"),
                  "Chegou um pote de queijo estragado no pedido PED-84915, quero resolver.")
    assert "abrir_ticket" in r["ferramentas"]
    assert "TCK-" in r["texto"]


def test_nao_vaza_pedido_de_outro_cliente():
    r = conversar(criar_agente("CLI-1003"), "Quais os itens do pedido PED-84891?")
    assert not any(item in r["texto"] for item in ("Heineken", "Picanha", "Sal Refinado", "169"))


def test_pergunta_fora_do_dominio_nao_inventa():
    r = conversar(criar_agente("CLI-1001"), "Qual a capital da França?")
    assert "Paris" not in r["texto"]
