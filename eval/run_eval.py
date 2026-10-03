"""Avaliação ponta a ponta: roda o agente real (GPT-4o-mini + RAG) sobre eval/gold.yaml.

Uso: python -m eval.run_eval [--categoria ticket]
Usa uma cópia temporária do banco, então os tickets abertos nos casos não tocam o supermercado.db.
"""
import argparse
import shutil
import sys
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path

import yaml

GOLD = Path(__file__).parent / "gold.yaml"


def avaliar(caso: dict, resp: dict) -> list[str]:
    """Devolve a lista de falhas do caso (vazia = passou)."""
    espera, texto, usadas = caso["espera"], resp["texto"].lower(), set(resp["ferramentas"])
    falhas = []
    if (alvo := espera.get("usa_alguma")) and not usadas & set(alvo):
        falhas.append(f"não usou nenhuma ferramenta de {alvo} (usou {sorted(usadas) or 'nenhuma'})")
    if proibidas := usadas & set(espera.get("nao_usa", [])):
        falhas.append(f"usou ferramenta proibida: {sorted(proibidas)}")
    if (termos := espera.get("contem_alguma")) and not any(t.lower() in texto for t in termos):
        falhas.append(f"resposta sem nenhum dos termos {termos}")
    for termo in espera.get("nao_contem", []):
        if termo.lower() in texto:
            falhas.append(f"resposta traz termo proibido: {termo}")
    return falhas


def executar(casos: list[dict], criar_agente, conversar) -> list[dict]:
    """Um agente (e uma conversa) novo por caso; exceção vira falha do caso."""
    resultados = []
    for caso in casos:
        try:
            resp = conversar(criar_agente(caso["cliente"]), caso["pergunta"], uuid.uuid4().hex)
            falhas = avaliar(caso, resp)
        except Exception as erro:
            resp, falhas = {"texto": "", "ferramentas": []}, [f"erro ao executar: {erro}"]
        resultados.append({"id": caso["id"], "categoria": caso["categoria"], "pergunta": caso["pergunta"],
                           "resposta": resp["texto"], "falhas": falhas})
    return resultados


def relatorio(resultados: list[dict]) -> str:
    por_categoria = defaultdict(lambda: [0, 0])
    for r in resultados:
        por_categoria[r["categoria"]][1] += 1
        por_categoria[r["categoria"]][0] += not r["falhas"]
    linhas = [f"{cat:<16}{ok}/{total}" for cat, (ok, total) in por_categoria.items()]
    acertos = sum(not r["falhas"] for r in resultados)
    linhas.append(f"\nTotal: {acertos}/{len(resultados)}")
    for r in resultados:
        if r["falhas"]:
            linhas.append(f"\nFALHOU {r['id']}: {r.get('pergunta', '')}")
            linhas += [f"  - {f}" for f in r["falhas"]]
            linhas.append(f"  resposta: {r.get('resposta', '')[:300]!r}")
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--categoria", help="roda só os casos desta categoria")
    args = parser.parse_args()

    casos = yaml.safe_load(GOLD.read_text(encoding="utf-8"))["casos"]
    if args.categoria:
        casos = [c for c in casos if c["categoria"] == args.categoria]

    import src.db
    from src import agent
    from src.config import DB_PATH

    # ignore_cleanup_errors: no Windows o SQLite ainda pode segurar o arquivo ao fim da execução
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        copia = Path(tmp) / "avaliacao.db"
        shutil.copy(DB_PATH, copia)
        src.db.DB_PATH = copia
        resultados = executar(casos, agent.criar_agente, agent.conversar)

    print(relatorio(resultados))
    return int(any(r["falhas"] for r in resultados))


if __name__ == "__main__":
    sys.exit(main())
