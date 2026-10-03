import re

from src.db import get_conn

_PROTOCOLO = re.compile(r"TCK-\d{4}-\d{3}")
_PROTOCOLO_SEM_NEGRITO = re.compile(r"(?<!\*)TCK-\d{4}-\d{3}(?!\*)")


def destacar_protocolos(texto: str) -> tuple[str, list[str]]:
    """Põe os protocolos de ticket em negrito e devolve também a lista (sem repetição, em ordem)."""
    protocolos = list(dict.fromkeys(_PROTOCOLO.findall(texto)))
    return _PROTOCOLO_SEM_NEGRITO.sub(lambda m: f"**{m.group()}**", texto), protocolos


def mensagem_de_erro(erro: Exception) -> str:
    """Mensagem para o cliente: nunca expõe o texto da exceção (pode conter chave ou detalhes internos)."""
    nomes = {c.__name__ for c in type(erro).__mro__}
    if nomes & {"AuthenticationError", "PermissionDeniedError"}:
        return "A chave da OpenAI é inválida ou não tem permissão. Verifique OPENAI_API_KEY no arquivo .env."
    if "RateLimitError" in nomes:
        return "Há muitas requisições no momento (limite da API). Tente novamente em instantes."
    if nomes & {"APIConnectionError", "APITimeoutError", "TimeoutError", "ConnectionError"}:
        return "Falha de conexão com o serviço de IA. Verifique a internet e tente de novo."
    return "Ocorreu um erro inesperado. Tente novamente; se persistir, fale com a nossa equipe."


def listar_clientes() -> list[tuple[str, str]]:
    with get_conn() as con:
        return [(r["cliente_id"], r["nome"])
                for r in con.execute("SELECT cliente_id, nome FROM clientes ORDER BY cliente_id")]
