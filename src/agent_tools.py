"""Ferramentas do agente. O cliente da sessão (já autenticado pelo canal) é fixado aqui: o LLM
nunca escolhe de quem são os dados, então não consegue consultar ou abrir ticket de outro cliente."""
from typing import Literal

from langchain_core.tools import tool

from src.db import get_conn
from src.rag.retriever import buscar_conhecimento
from src.tools import estoque, pedidos, tickets
from src.tools.substituicao import sugerir_substitutos_ia

MOTIVOS = tuple(sorted(tickets.MOTIVOS_GRAVES)) + (
    "atraso_entrega", "cobranca_duplicada", "item_faltante", "agressividade", "duvida_geral", "outro")
Motivo = Literal[*MOTIVOS]
Prioridade = Literal[*tickets.PRIORIDADES]
Departamento = Literal[*tickets.DEPARTAMENTOS]

SEM_CLIENTE = {"erro": "Cliente não identificado. Peça ao cliente para se identificar antes de continuar."}


def _dono_do_pedido(pedido_id: str) -> str | None:
    with get_conn() as con:
        row = con.execute("SELECT cliente_id FROM pedidos WHERE pedido_id = ?", (pedido_id,)).fetchone()
    return row["cliente_id"] if row else None


def criar_tools(cliente_id: str | None) -> list:
    @tool("buscar_produto")
    def buscar_produto(termo: str) -> list[dict]:
        """Busca produtos pelo nome (ex.: 'banana', 'leite integral'). Retorna preço, unidade,
        saldo em estoque, seção/corredor e se está disponível. Use para preço, estoque e localização."""
        return estoque.buscar_produto(termo)

    @tool("consultar_estoque")
    def consultar_estoque(sku: str) -> dict | None:
        """Consulta um produto pelo SKU exato (ex.: 'HORT-001'): preço, saldo, seção, disponibilidade."""
        return estoque.consultar_estoque(sku)

    @tool("sugerir_substitutos")
    def sugerir_substitutos(sku: str) -> dict:
        """Sugere substitutos para um produto INDISPONÍVEL, com o motivo de cada sugestão."""
        return sugerir_substitutos_ia(sku)

    @tool("rastrear_pedido")
    def rastrear_pedido(pedido_id: str) -> dict:
        """Status, motorista, previsão de entrega, itens e totais de um pedido DO CLIENTE ATUAL."""
        if not cliente_id:
            return SEM_CLIENTE
        if _dono_do_pedido(pedido_id) != cliente_id:  # inexistente ou de outro cliente: mesma resposta
            return {"encontrado": False, "aviso": f"Pedido {pedido_id} não encontrado para este cliente."}
        return pedidos.rastrear_pedido(pedido_id)

    @tool("listar_meus_pedidos")
    def listar_meus_pedidos() -> list[dict] | dict:
        """Lista os pedidos do cliente atual (mais recente primeiro). Use quando ele não souber o código."""
        if not cliente_id:
            return SEM_CLIENTE
        return pedidos.listar_pedidos_cliente(cliente_id)

    @tool("buscar_conhecimento")
    def buscar_conhecimento_tool(pergunta: str) -> dict:
        """Busca em políticas, FAQ, promoções e dados da empresa (prazos de troca, frete, formas de
        pagamento, horários, endereços, campanhas). Cite a fonte. Sem trecho relevante: não invente."""
        relevantes = [t for t in buscar_conhecimento(pergunta, k=4) if t["relevante"]]
        if not relevantes:
            return {"trechos": [], "aviso": "Nenhum trecho relevante na base. Não responda por conta própria."}
        return {"trechos": relevantes}

    @tool("abrir_ticket")
    def abrir_ticket(pedido_id: str | None, motivo: Motivo, descricao: str,
                     prioridade: Prioridade, departamento: Departamento) -> dict:
        """Transborda para a equipe humana abrindo um ticket para o cliente atual. Use em avaria,
        produto vencido, suspeita de intoxicação (prioridade critica, sac_emergencial), cobrança duplicada
        (financeiro_cobranca), atraso crítico (sac_logistica), agressividade/Procon (sac_relacionamento)
        ou item faltante sem autorização (sac_operacoes). `descricao` resume o ocorrido."""
        if not cliente_id:
            return SEM_CLIENTE
        return tickets.abrir_ticket(cliente_id, pedido_id, motivo, descricao, prioridade, departamento)

    return [buscar_produto, consultar_estoque, sugerir_substitutos, rastrear_pedido,
            listar_meus_pedidos, buscar_conhecimento_tool, abrir_ticket]
