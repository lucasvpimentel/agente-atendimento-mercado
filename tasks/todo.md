# Todo: Agente de Atendimento e Triagem (RAG + SQL)

Detalhes e critérios em [plan.md](plan.md). Ordem de execução = ordem da lista.

## Já feito
- [x] Kickoff: `schema.sql` + `setup_db.py` + `supermercado.db`; YAMLs em `data/`

## Phase 1: Fundação
- [x] T1: Ambiente, dependências e módulo de acesso ao banco (S)

### Checkpoint: Fundação
- [x] `pip install -r requirements.txt` limpo; `python setup_db.py` ok; `pytest` roda

## Phase 2: Ferramentas SQL
- [x] T2: Consulta de estoque e localização (S) — dep: T1
- [x] T3: Sugestão de substituição (S) — dep: T2
- [x] T4: Rastreamento de pedidos (S) — dep: T1

### Checkpoint: SQL
- [x] Tools T2–T4 passam nos testes contra o banco real, sem LLM

## Phase 3: RAG
- [x] T6: Ingestão e índice FAISS (M) — dep: T1
- [x] T7: Tool de busca semântica (S) — dep: T6

### Checkpoint: RAG
- [x] Perguntas-ouro de política/FAQ/promo recuperam o trecho correto no top-4

## Phase 4: Triagem
- [x] T5: Abertura de ticket e transbordo com resumo estruturado (M) — dep: T4, T7

## Phase 5: Agente e interface
- [x] T8: Agente LangChain com todas as tools (M) — dep: T2, T3, T4, T5, T7
- [ ] T9: Interface Streamlit (S) — dep: T8

### Checkpoint: End-to-end
- [ ] Os 5 fluxos da seção 6 da spec funcionam na UI

## Phase 6: Qualidade
- [ ] T10: Avaliação, README e atualização da spec (M) — dep: T9

### Checkpoint: Completo
- [ ] Critérios de aceite atendidos; revisão humana
