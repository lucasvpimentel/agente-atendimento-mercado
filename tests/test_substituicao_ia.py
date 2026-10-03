import os

import pytest

from src.tools.substituicao import Escolha, Sugestao, sugerir_substitutos, sugerir_substitutos_ia


class LLMFalso:
    """Registra o prompt recebido e devolve uma escolha pronta."""

    def __init__(self, escolha=None, erro=None):
        self.escolha, self.erro, self.prompt = escolha, erro, None

    def invoke(self, prompt):
        self.prompt = prompt
        if self.erro:
            raise self.erro
        return self.escolha


def _candidatos(n):
    return [s["sku"] for s in sugerir_substitutos("HORT-004", limite=n)["substitutos"]]


def test_ia_reordena_e_explica_dentro_dos_candidatos():
    c = _candidatos(10)
    llm = LLMFalso(Escolha(sugestoes=[Sugestao(sku=c[4], motivo="parecido"), Sugestao(sku=c[1], motivo="folha")]))
    r = sugerir_substitutos_ia("HORT-004", limite=2, llm=llm)
    assert [s["sku"] for s in r["substitutos"]] == [c[4], c[1]]
    assert r["substitutos"][0]["motivo"] == "parecido"
    assert r["origem"] == "ia"


def test_prompt_so_leva_os_candidatos_limitados_e_campos_compactos():
    c50 = _candidatos(50)
    llm = LLMFalso(Escolha(sugestoes=[]))
    sugerir_substitutos_ia("HORT-004", limite=3, max_candidatos=5, llm=llm)
    enviados = [s for s in c50 if s in llm.prompt]
    assert enviados == c50[:5]
    assert "secao" not in llm.prompt and "estoque" not in llm.prompt


def test_descarta_sku_inventado_pela_ia():
    c = _candidatos(10)
    llm = LLMFalso(Escolha(sugestoes=[Sugestao(sku="CARN-001", motivo="x"), Sugestao(sku=c[0], motivo="ok")]))
    r = sugerir_substitutos_ia("HORT-004", limite=3, llm=llm)
    assert [s["sku"] for s in r["substitutos"]] == [c[0]]


def test_respeita_limite_mesmo_se_ia_devolver_mais():
    c = _candidatos(10)
    llm = LLMFalso(Escolha(sugestoes=[Sugestao(sku=s, motivo="m") for s in c[:6]]))
    assert len(sugerir_substitutos_ia("HORT-004", limite=2, llm=llm)["substitutos"]) == 2


def test_falha_da_ia_cai_na_regra():
    llm = LLMFalso(erro=RuntimeError("api fora"))
    r = sugerir_substitutos_ia("HORT-004", limite=3, llm=llm)
    assert r["origem"] == "regra"
    assert [s["sku"] for s in r["substitutos"]] == _candidatos(3)


def test_ia_vazia_cai_na_regra():
    r = sugerir_substitutos_ia("HORT-004", limite=3, llm=LLMFalso(Escolha(sugestoes=[])))
    assert r["origem"] == "regra" and len(r["substitutos"]) == 3


@pytest.mark.parametrize("sku", ["HORT-001", "XXXX-999"])
def test_nao_chama_ia_sem_necessidade(sku):
    llm = LLMFalso(erro=AssertionError("não deveria chamar"))
    r = sugerir_substitutos_ia(sku, llm=llm)
    assert r["substitutos"] == [] and llm.prompt is None


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="sem OPENAI_API_KEY")
def test_api_real_escolhe_entre_os_candidatos():
    r = sugerir_substitutos_ia("HORT-004", limite=3)
    permitidos = set(_candidatos(10))
    assert r["origem"] == "ia"
    assert 1 <= len(r["substitutos"]) <= 3
    assert all(s["sku"] in permitidos and s["motivo"] for s in r["substitutos"])
