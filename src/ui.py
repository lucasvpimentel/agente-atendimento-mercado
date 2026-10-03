import html
import re

from src.db import get_conn

_PROTOCOLO = re.compile(r"TCK-\d{4}-\d{3}")
_PROTOCOLO_SEM_NEGRITO = re.compile(r"(?<!\*)TCK-\d{4}-\d{3}(?!\*)")

_ROTULOS = {
    "buscar_produto": "Consultou o estoque", "consultar_estoque": "Consultou o estoque",
    "sugerir_substitutos": "Buscou substitutos", "rastrear_pedido": "Rastreou o pedido",
    "listar_meus_pedidos": "Listou seus pedidos", "buscar_conhecimento": "Consultou as políticas da loja",
    "abrir_ticket": "Abriu um ticket",
}


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


def dados_cliente(cliente_id: str) -> dict | None:
    """Só o que a interface exibe: sem CPF, telefone, e-mail ou endereço."""
    with get_conn() as con:
        r = con.execute("SELECT nome, programa_fidelidade, pontos_acumulados FROM clientes"
                        " WHERE cliente_id = ?", (cliente_id,)).fetchone()
    return None if r is None else {"nome": r["nome"], "programa_fidelidade": r["programa_fidelidade"],
                                   "pontos": r["pontos_acumulados"]}


def primeiro_nome(nome: str) -> str:
    return nome.split()[0]


def rotulo_ferramenta(nome: str) -> str:
    return _ROTULOS.get(nome, nome)


def html_chips(ferramentas: list[str]) -> str:
    rotulos = dict.fromkeys(rotulo_ferramenta(f) for f in ferramentas)
    if not rotulos:
        return ""
    chips = "".join(f'<span class="chip">{html.escape(r)}</span>' for r in rotulos)
    return f'<div class="chips">{chips}</div>'


def html_cupom(protocolo: str) -> str:
    return ('<div class="cupom" role="status">'
            '<span class="cupom-rotulo">Atendimento encaminhado à equipe</span>'
            f'<span class="cupom-codigo">{html.escape(protocolo)}</span>'
            '<span class="cupom-nota">Guarde este protocolo para acompanhar o caso.</span></div>')


def sugestoes(identificado: bool) -> list[str]:
    comuns = ["Quanto custa a banana?", "Qual o prazo de troca de um produto?"]
    if identificado:
        return ["Onde está meu pedido?", *comuns, "Tive um problema com meu pedido"]
    return [*comuns, "Quais são as promoções de hoje?", "Qual o horário de atendimento do SAC?"]
