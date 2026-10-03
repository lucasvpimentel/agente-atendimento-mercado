# Agente de Atendimento e Triagem — Supermercado Bom Preço & Cia

Assistente de atendimento para um supermercado de médio porte. Combina **consultas SQL** (preço, estoque, pedidos, tickets) com **busca semântica RAG** (políticas, FAQ, promoções) num agente LangChain com *function calling*, servido por uma interface Streamlit.

Especificação completa: [docs/especificacao_projeto.md](docs/especificacao_projeto.md).

## O que o agente faz

| Funcionalidade | Como |
| --- | --- |
| Preço, estoque e corredor de qualquer produto | SQL (`buscar_produto`, `consultar_estoque`) |
| Sugestão de substitutos para item indisponível | SQL filtra 10 candidatos; IA escolhe e explica (`sugerir_substitutos`) |
| Rastreio de pedidos do cliente | SQL (`rastrear_pedido`, `listar_meus_pedidos`) |
| Políticas, FAQ, promoções, contatos e lojas | RAG com FAISS (`buscar_conhecimento`) |
| Triagem e transbordo para a equipe humana | Ticket com resumo estruturado (`abrir_ticket`) |

## Como rodar

Requisitos: Python 3.12+ e uma chave da OpenAI.

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Crie o `.env` a partir do exemplo e preencha a chave:

```bash
copy .env.example .env          # Linux/macOS: cp .env.example .env
```

Gere o banco e o índice de busca (uma vez, ou quando os dados mudarem):

```bash
python setup_db.py              # cria supermercado.db a partir de data/estruturados
python build_index.py           # cria data/index (usa a API de embeddings da OpenAI)
```

Suba a interface:

```bash
streamlit run app.py
```

Se faltar dependência, índice ou chave, a tela indica o que fazer.

## Variáveis de ambiente (`.env`)

| Variável | Padrão | Uso |
| --- | --- | --- |
| `OPENAI_API_KEY` | — | obrigatória |
| `OPENAI_MODEL` | `gpt-4o-mini` | modelo do agente |
| `TEMPERATURE` | `0.2` | temperatura do agente |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | embeddings do RAG |
| `RAG_LIMIAR` | `0.2` | similaridade mínima para um trecho contar como relevante |
| `DB_PATH` | `supermercado.db` | caminho do banco SQLite |

## Estrutura

```
app.py                  interface Streamlit
assets/estilo.css       tema visual
schema.sql              DDL das 5 tabelas
setup_db.py             cria e popula o supermercado.db
build_index.py          cria o índice FAISS
data/estruturados/      YAMLs que viram tabelas (produtos, clientes, pedidos)
data/rag/               YAMLs indexados no RAG (FAQ, promoções, manual de políticas)
src/agent.py            agente LangChain com memória por conversa
src/agent_tools.py      ferramentas expostas ao modelo
src/tools/              lógica de negócio (estoque, substituição, pedidos, tickets)
src/rag/                ingestão e busca semântica
src/prompts.py          prompt do sistema
eval/                   conjunto-ouro e script de avaliação
tests/                  testes automatizados
tasks/                  plano e lista de tarefas do desenvolvimento
```

## Testes e avaliação

```bash
pytest -m "not integration"     # rápidos, sem rede
pytest                          # inclui os testes com a API da OpenAI (usa a chave do .env)
python -m eval.run_eval         # 18 perguntas ponta a ponta, por categoria
python -m eval.run_eval --categoria ticket
```

A avaliação roda o agente real sobre `eval/gold.yaml` numa **cópia temporária do banco**, então os tickets abertos nos casos não alteram o `supermercado.db`. O resultado depende do modelo e pode variar entre execuções.

## Decisões de projeto

- **O modelo nunca escreve SQL.** Ele só chama ferramentas com argumentos tipados; motivo, prioridade e fila do ticket são listas fechadas.
- **Cliente fixado na sessão.** As ferramentas de pedidos e tickets só enxergam o cliente da conversa; pedido de outro cliente aparece como "não encontrado". Na interface, o seletor "Entrar como" simula a autenticação que um canal real (login, WhatsApp) faria.
- **Sem dados pessoais nas respostas.** CPF, telefone, e-mail e endereço não saem das ferramentas.
- **Fatiamento por unidade lógica, não por tamanho.** Cada pergunta do FAQ, campanha, subseção do manual e linha da matriz de transbordo é um documento. A base é pequena e cada unidade cabe inteira no embedding.
- **Ticket sem duplicata.** Já existindo ticket aberto para o mesmo pedido e motivo, o agente informa o protocolo existente.
- **Memória só em RAM.** A conversa vive enquanto o processo roda; não há histórico em disco.

## Limites conhecidos

- O seletor de cliente é uma simulação, sem autenticação real.
- A sugestão de substitutos só vê 10 candidatos pré-filtrados por categoria e preço; pode oferecer itens pouco parecidos.
- O manual de políticas é Markdown com extensão `.yaml`; o parser depende dos títulos `##` e `###`.
- Os dados são fictícios (162 produtos, 8 clientes, 4 pedidos, 1 ticket).
