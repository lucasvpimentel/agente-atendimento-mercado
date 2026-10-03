# Implementation Plan: Agente de Atendimento e Triagem (RAG + SQL)

Fonte: [docs/especificacao_projeto.md](../docs/especificacao_projeto.md)

## Overview

Agente LangChain (GPT-4o-mini, function calling) com Streamlit na frente. Duas fontes: **SQLite** (determinístico: produtos, clientes, pedidos, tickets) e **FAISS** (semântico: políticas, FAQ, promoções). Ordem abaixo segue o desenvolvimento manual recomendado: ambiente → dados → ferramentas isoladas e testadas → agente → UI → avaliação.

## Estado atual (já feito)

- `schema.sql` + `setup_db.py` geram `supermercado.db` (162 produtos, 8 clientes, 4 pedidos, 11 itens, 1 ticket). Ver kickoff, seção 1 da spec.
- YAMLs movidos para `data/estruturados/` (→ SQLite) e `data/rag/` (→ FAISS).

## Architecture Decisions

- **Ferramentas primeiro, agente depois.** Cada capacidade vira uma função Python pura (`src/tools/*`) testável sem LLM; o agente só as registra como `@tool`. Falha de LLM e falha de SQL ficam separadas.
- **Fatias verticais por funcionalidade** (seção 6 da spec): cada task entrega função + tool + teste, não "todas as queries" e depois "todos os testes".
- **SQL parametrizado sempre**; o LLM nunca escreve SQL livre, só chama tools com argumentos tipados.
- **Embeddings:** `text-embedding-3-small` (OpenAI, mesma chave do LLM). Índice FAISS persistido em `data/index/`.
- **Escrita no banco só via tool de ticket**; demais tools são somente leitura.
- **Estrutura:** `src/` (config, db, tools, rag, agent), `app.py` (Streamlit), `tests/`.

## Divergências spec × dados reais (decidir/registrar)

| Spec | Real | Ação |
|---|---|---|
| `politicas_operacionais.md` | `manual_de_pol_ticas_operacionais.yaml` | Indexar o YAML; atualizar nomes na spec (T9) |
| 150 produtos | 162 no catálogo | Aceitar 162; atualizar spec |
| `cpf` único | CPF mascarado (`123.***.***-01`) | Validação de identidade por CPF só compara máscara; ver Open Questions |
| `promocoes_ativas.yaml`, `faq_supermercado.yaml` | `promo_es_ativas.yaml`, `base_de_conhecimento_supermercado.yaml` | Usar nomes reais |

## Dependency Graph

```
T1 Ambiente/config ──► (schema.sql + setup_db.py ✔)
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
 T2 Estoque/local   T4 Rastreio pedido   T6 Ingestão RAG ──► T7 Tool RAG
        │                 │                                      │
        ▼                 │                                      │
 T3 Substituição          │                                      │
        └────────┬────────┴──────────────────────────────────────┘
                 ▼
          T5 Ticket/transbordo (usa pedidos, clientes)
                 ▼
          T8 Agente LangChain (registra todas as tools)
                 ▼
          T9 UI Streamlit
                 ▼
          T10 Avaliação ponta a ponta + docs
```

## Task List

### Phase 1: Fundação
- [x] T1: Ambiente, dependências e módulo de acesso ao banco

### Checkpoint: Fundação
- [ ] `pip install -r requirements.txt` limpo; `python setup_db.py` ok; `pytest` roda

### Phase 2: Ferramentas SQL (uma fatia por funcionalidade)
- [x] T2: Consulta de estoque e localização
- [x] T3: Sugestão de substituição
- [x] T4: Rastreamento de pedidos

### Checkpoint: SQL
- [x] Os 3 conjuntos de tools passam nos testes contra o banco real, sem LLM

### Phase 3: RAG
- [x] T6: Ingestão e índice FAISS
- [x] T7: Tool de busca semântica

### Checkpoint: RAG
- [x] Perguntas de política/FAQ/promo recuperam o trecho correto no top-k

### Phase 4: Triagem
- [ ] T5: Abertura de ticket e transbordo com resumo estruturado

### Phase 5: Agente e interface
- [ ] T8: Agente LangChain com todas as tools
- [ ] T9: Interface Streamlit

### Checkpoint: End-to-end
- [ ] Os 5 fluxos da seção 6 funcionam na UI

### Phase 6: Qualidade
- [ ] T10: Avaliação, README e atualização da spec

### Checkpoint: Completo
- [ ] Critérios de aceite todos atendidos; pronto para revisão

> Numeração: T5 aparece depois de T7 na ordem de execução porque o resumo do ticket reaproveita as tools de pedido (T4) e a classificação por política (T7). Ordem de execução: T1 → T2 → T3 → T4 → T6 → T7 → T5 → T8 → T9 → T10.

---

## Tasks

### T1: Ambiente, dependências e módulo de acesso ao banco
**Description:** Estrutura `src/`, `tests/`, `requirements.txt`, `.env.example`, `.gitignore`; `src/db.py` com `get_conn()` (row_factory, `PRAGMA foreign_keys=ON`) e `src/config.py` (caminhos, modelo, chave via env).
**Acceptance criteria:**
- [ ] `requirements.txt` com langchain, langchain-openai, langchain-community, faiss-cpu, streamlit, pyyaml, pytest, python-dotenv
- [ ] Chave OpenAI só via `.env` (ignorado pelo git); `.env.example` sem segredo
- [ ] `get_conn()` retorna conexão com FK ligada
**Verification:** `pytest tests/test_db.py` (conecta, conta `produtos` > 0, FK ligada); `python setup_db.py` ok.
**Dependencies:** nenhuma (kickoff já feito)
**Files:** `requirements.txt`, `.env.example`, `.gitignore`, `src/config.py`, `src/db.py`, `tests/test_db.py`
**Scope:** S

### T2: Consulta de estoque e localização
**Description:** `buscar_produto(termo)` e `consultar_estoque(sku)` retornam preço, unidade, saldo, seção, disponibilidade. Busca por nome com `LIKE` normalizado (sem acento, case-insensitive).
**Acceptance criteria:**
- [ ] "banana" retorna HORT-001 com preço 6.99/kg e seção "Banca Central"
- [ ] Termo sem resultado retorna lista vazia, não exceção
- [ ] Item `disponivel=0` aparece marcado como indisponível
**Verification:** `pytest tests/test_estoque.py` (casos acima + SKU inexistente).
**Dependencies:** T1
**Files:** `src/tools/estoque.py`, `tests/test_estoque.py`
**Scope:** S

### T3: Sugestão de substituição
**Description:** `sugerir_substitutos(sku, limite=3)` retorna itens da mesma categoria com `estoque > 0`, priorizando mesma unidade e preço mais próximo.
**Acceptance criteria:**
- [ ] Para HORT-004 (alface, estoque 0) retorna só itens de Hortifrúti disponíveis
- [ ] Nunca retorna o próprio SKU nem item sem estoque
- [ ] Produto disponível → retorna lista vazia com aviso "já disponível"
**Verification:** `pytest tests/test_substituicao.py`.
**Dependencies:** T2
**Files:** `src/tools/substituicao.py`, `tests/test_substituicao.py`
**Scope:** S

### T4: Rastreamento de pedidos
**Description:** `rastrear_pedido(pedido_id)` retorna status, motorista, previsão, itens e totais; `listar_pedidos_cliente(cliente_id)`.
**Acceptance criteria:**
- [ ] PED-84915 → `em_rota`, motorista "Marcos Vinicius…", previsão 09:00
- [ ] PED-84920 → `em_separacao`, sem motorista
- [ ] Pedido inexistente → resultado "não encontrado" explícito
- [ ] Sem expor CPF/telefone/e-mail na resposta
**Verification:** `pytest tests/test_pedidos.py`.
**Dependencies:** T1
**Files:** `src/tools/pedidos.py`, `tests/test_pedidos.py`
**Scope:** S

### T6: Ingestão e índice FAISS
**Description:** Carrega os 3 YAMLs de `data/rag/`, gera um `Document` por entrada (pergunta/resposta, política, promoção) com metadados (`fonte`, `categoria`, `escalar_humano` quando existir), cria embeddings e persiste o índice em `data/index/`. Script `build_index.py` idempotente.
**Acceptance criteria:**
- [ ] Um documento por entrada lógica (sem chunk cortando regra ao meio)
- [ ] Índice persistido e recarregável sem nova chamada de embedding
- [ ] Metadado `fonte` preenchido em todos os documentos
**Verification:** `python build_index.py` imprime nº de documentos por fonte; `pytest tests/test_rag_ingest.py` (parsing sem rede, embeddings mockados).
**Dependencies:** T1
**Files:** `src/rag/ingest.py`, `build_index.py`, `tests/test_rag_ingest.py`
**Scope:** M

### T7: Tool de busca semântica
**Description:** `buscar_conhecimento(pergunta, k=4)` consulta o FAISS e devolve trechos com fonte e flag `escalar_humano`.
**Acceptance criteria:**
- [ ] ≥ 5 perguntas-ouro (ex.: "aceita vale alelo?", "prazo de troca de perecível") retornam o trecho certo no top-4
- [ ] Resposta inclui `fonte` para citação
- [ ] Pergunta fora do domínio retorna trechos de baixa similaridade sinalizados (limiar configurável)
**Verification:** `pytest tests/test_rag_retrieval.py -m integration` (usa embeddings reais, marcado e opcional).
**Dependencies:** T6
**Files:** `src/rag/retriever.py`, `tests/test_rag_retrieval.py`
**Scope:** S

### T5: Triagem e transbordo com resumo estruturado
**Description:** `abrir_ticket(cliente_id, pedido_id, motivo, descricao, prioridade, departamento)` insere em `tickets` (ID `TCK-AAAA-NNN` sequencial) e retorna resumo estruturado (cliente, pedido, itens, problema, ação sugerida). Única tool com escrita.
**Acceptance criteria:**
- [ ] Valida enums (`prioridade`, `departamento`) e existência de cliente/pedido antes de inserir
- [ ] Avaria/produto vencido/reclamação grave → prioridade `alta` ou `critica`
- [ ] Ticket criado em transação; falha não deixa linha parcial
- [ ] Segunda abertura para o mesmo pedido/motivo avisa ticket já aberto (sem duplicar)
**Verification:** `pytest tests/test_tickets.py` (usa cópia temporária do banco).
**Dependencies:** T4, T7
**Files:** `src/tools/tickets.py`, `tests/test_tickets.py`
**Scope:** M

### T8: Agente LangChain com todas as tools
**Description:** `src/agent.py` monta o agente (GPT-4o-mini, function calling) com tools T2–T7 e system prompt: responder em PT-BR, usar SQL para dados exatos, RAG para políticas, nunca inventar preço/estoque/status, transbordar para ticket em casos fora do escopo; memória de conversa por sessão.
**Acceptance criteria:**
- [ ] "Tem alface?" → consulta estoque, informa indisponível e sugere substituto
- [ ] "Onde está o pedido PED-84915?" → status e previsão corretos
- [ ] "Qual prazo de troca?" → resposta com base no RAG
- [ ] "Veio garrafa quebrada no PED-84891" → abre ticket (ou reporta o já existente) e informa o protocolo
- [ ] Agente não vaza dados pessoais de outro cliente
**Verification:** `pytest tests/test_agent_smoke.py -m integration` com os 4 cenários; log das tool calls revisado manualmente.
**Dependencies:** T2, T3, T4, T5, T7
**Files:** `src/agent.py`, `src/prompts.py`, `tests/test_agent_smoke.py`
**Scope:** M

### T9: Interface Streamlit
**Description:** `app.py` com chat, histórico por sessão, indicador das tools usadas e aviso quando houver transbordo.
**Acceptance criteria:**
- [ ] `streamlit run app.py` abre e responde aos 4 cenários de T8
- [ ] Erro de API/chave mostra mensagem amigável, não traceback
- [ ] Protocolo do ticket destacado na resposta
**Verification:** execução manual dos 5 fluxos da spec (seção 6) na UI, com captura de tela.
**Dependencies:** T8
**Files:** `app.py`
**Scope:** S

### T10: Avaliação, README e atualização da spec
**Description:** Conjunto-ouro de ~15 perguntas (estoque, substituição, pedido, política, ticket, fora de escopo) com resultado esperado; script de avaliação; README com setup; atualizar spec com nomes de arquivos e contagens reais.
**Acceptance criteria:**
- [ ] Script reporta acertos por categoria
- [ ] README permite subir o projeto do zero em < 10 min
- [ ] Spec sem divergência com o repositório
**Verification:** `python eval/run_eval.py`; revisar README seguindo-o numa pasta limpa.
**Dependencies:** T9
**Files:** `eval/gold.yaml`, `eval/run_eval.py`, `README.md`, `docs/especificacao_projeto.md`
**Scope:** M

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM inventa preço/estoque | High | Prompt proíbe; respostas numéricas só de tools; teste de regressão em T8/T10 |
| Tool de ticket duplica chamados ou grava lixo | High | Validação + checagem de duplicata + transação (T5) |
| Vazamento de dados de outro cliente | High | Tools de pedido omitem PII; verificar `cliente_id` quando houver identificação |
| Custo/latência de embeddings | Low | Índice persistido, reconstrução só em `build_index.py` |
| Dataset pequeno (4 pedidos, 1 ticket) limita testes | Med | Testes usam banco temporário com fixtures próprias |
| Chave OpenAI no repositório | High | `.env` no `.gitignore`; `.env.example` sem segredo |

## Open Questions

- CPF está mascarado no dado. Validação de identidade será só por `cliente_id`/telefone? Ou aceitar CPF parcial?
- Idioma/tom do agente: formal ou informal? (assumido: cordial, PT-BR)
- Embedding `text-embedding-3-small` está ok, ou prefere modelo local para evitar custo?
- Mais tickets de exemplo no dataset (hoje só 1)? Ajuda a testar T5 e T10.
