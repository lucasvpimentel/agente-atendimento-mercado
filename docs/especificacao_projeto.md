# Especificação Técnica do Produto: Agente Inteligente de Atendimento e Triagem de Suporte com RAG e SQL

---

## 1. Comando Inicial para o Agente de Desenvolvimento (Prompt de Kickoff)

> **Instrução:** Copie e execute o comando abaixo no ambiente do seu assistente de programação para iniciar a estrutura de banco de dados do projeto.

```text
Olá! Estamos construindo um Agente Inteligente de Atendimento e Triagem de Suporte para um supermercado de médio porte.
Nossa stack é: Python, LangChain, OpenAI (GPT-4o-mini), FAISS, SQLite e Streamlit.

Sua primeira tarefa é criar a camada de banco de dados relacional (SQLite):
1. Crie um arquivo `schema.sql` contendo rigorosamente as 5 tabelas especificadas: `produtos`, `clientes`, `pedidos`, `pedido_itens` e `tickets`, com todas as restrições de integridade (PRIMARY KEY, FOREIGN KEY, CHECK, NOT NULL, DEFAULT e índices).
2. Crie um script de automação `setup_db.py` que:
   - Inicialize o banco `supermercado.db` executando o `schema.sql`.
   - Carregue e popule os dados a partir dos arquivos YAML existentes:
     - `catalogo_produtos_150.yaml` -> tabela `produtos`
     - `clientes_cadastrados.yaml` -> tabela `clientes`
     - `pedidos_tickets_sac.yaml` -> tabelas `pedidos`, `pedido_itens` e `tickets`
   - Valide e exiba no console a quantidade de registros inseridos em cada tabela.
Por favor, gere o código completo e executável de `schema.sql` e `setup_db.py`.
```

---

## 2. Visão Geral e Arquitetura

O sistema atua como ponto único de contato digital no atendimento ao cliente de um supermercado de médio porte. Ele combina raciocínio probabilístico e semântico via **RAG (FAISS)** com raciocínio determinístico e preciso via **Consultas Relacionais (SQLite)**, orquestrado por um Agente **LangChain** com *Function Calling*.

```
                         [ Cliente / Streamlit ]
                                    │
                                    ▼
                     [ Agente LangChain (GPT-4o-mini) ]
                       /                            \
        (Consultas Semânticas)             (Consultas Determinísticas)
                     /                                \
                    ▼                                  ▼
         [ FAISS Vector Store ]                [ SQLite Engine ]
        - politicas_operacionais.md           - produtos (150 itens)
        - faq_supermercado.yaml               - clientes (cadastros e fidelidade)
        - promocoes_ativas.yaml               - pedidos e pedido_itens
                                              - tickets (SAC / Transbordo)
```

---

## 3. Matriz de Distribuição dos Artefatos por Formato

| Formato | Artefato | Justificativa Arquitetural |
| --- | --- | --- |
| **SQLite (`.db`)** | `produtos` (150 itens) | Requer precisão numérica, checagem exata de estoque (`estoque > 0`) e filtros determinísticos por categoria. |
| **SQLite (`.db`)** | `clientes` | Permite lookup exato por CPF, telefone ou ID para validação de identidade e clube de fidelidade. |
| **SQLite (`.db`)** | `pedidos` e `pedido_itens` | Relacionamento 1:N com integridade referencial para cálculo de totais, itens e rastreamento de entregas. |
| **SQLite (`.db`)** | `tickets` | Gerenciamento de estado transacional (`aberto`/`resolvido`), histórico de chamados e filas de transbordo. |
| **Markdown (`.md`)** | `politicas_operacionais.md` | Texto denso e não estruturado (regras de troca, cadeia de frio, estorno), ideal para chunking e busca vetorial no FAISS. |
| **YAML (`.yaml`)** | `faq_supermercado.yaml` | Metadados semiestruturados com perguntas frequentes, canais de SAC, endereços físicos e tags semânticas para o RAG. |
| **YAML (`.yaml`)** | `promocoes_ativas.yaml` | Campanhas vigentes, regras de elegibilidade e etiquetas de desconto para consulta semântica e contextual. |

---

## 4. Dicionário de Dados e Tipos do SQLite

### 4.1. Tabela `produtos`

*Catálogo de produtos, precificação, inventário e corredor físico na loja.*

| Campo | Tipo SQLite | Restrições | Descrição |
| --- | --- | --- | --- |
| `sku` | `TEXT` | `PRIMARY KEY NOT NULL` | Código de identificação único (ex.: `'HORT-001'`, `'CARN-003'`) |
| `nome` | `TEXT` | `NOT NULL` | Descrição comercial completa do produto |
| `categoria` | `TEXT` | `NOT NULL` | Categoria de produto (ex.: `'Hortifrúti'`, `'Laticínios & Frios'`) |
| `preco` | `REAL` | `NOT NULL CHECK(preco >= 0)` | Preço unitário de venda em reais |
| `unidade` | `TEXT` | `NOT NULL CHECK(unidade IN ('kg', 'un'))` | Unidade de comercialização (`'kg'` ou `'un'`) |
| `estoque` | `REAL` | `NOT NULL DEFAULT 0 CHECK(estoque >= 0)` | Saldo físico em estoque |
| `secao` | `TEXT` | `NOT NULL` | Localização interna/gôndola (ex.: `'Banca Central'`, `'Corredor 2'`) |
| `disponivel` | `INTEGER` | `NOT NULL DEFAULT 1 CHECK(disponivel IN (0, 1))` | Booleano (`1` se estoque > 0, senão `0`) |

### 4.2. Tabela `clientes`

*Cadastro de usuários, informações para entrega e dados de relacionamento.*

| Campo | Tipo SQLite | Restrições | Descrição |
| --- | --- | --- | --- |
| `cliente_id` | `TEXT` | `PRIMARY KEY NOT NULL` | Identificador único do cliente (ex.: `'CLI-1001'`) |
| `nome` | `TEXT` | `NOT NULL` | Nome completo do cliente |
| `cpf` | `TEXT` | `NOT NULL UNIQUE` | Cadastro de Pessoa Física |
| `telefone` | `TEXT` | `NOT NULL` | Número de WhatsApp/telefone com DDD |
| `email` | `TEXT` | `NOT NULL` | Endereço eletrônico de contato |
| `endereco` | `TEXT` | `NOT NULL` | Endereço residencial padrão para entrega |
| `programa_fidelidade` | `TEXT` | `NOT NULL DEFAULT 'Clube Bronze'` | Categoria de cliente (`'Clube Bronze'`, `'Clube Prata'`, `'Clube Ouro'`) |
| `pontos_acumulados` | `INTEGER` | `NOT NULL DEFAULT 0 CHECK(pontos_acumulados >= 0)` | Saldo ativo de pontos no clube |

### 4.3. Tabela `pedidos`

*Cabeçalho dos pedidos realizados via e-commerce, WhatsApp ou aplicativo.*

| Campo | Tipo SQLite | Restrições | Descrição |
| --- | --- | --- | --- |
| `pedido_id` | `TEXT` | `PRIMARY KEY NOT NULL` | Código do pedido (ex.: `'PED-84920'`) |
| `cliente_id` | `TEXT` | `NOT NULL REFERENCES clientes(cliente_id)` | Chave estrangeira do cliente solicitante |
| `data_pedido` | `TEXT` | `NOT NULL` | Timestamp no formato ISO-8601 (`YYYY-MM-DDTHH:MM:SS`) |
| `status` | `TEXT` | `NOT NULL CHECK(status IN ('em_separacao', 'em_rota', 'entregue', 'cancelado_estornado'))` | Estado operacional do pedido |
| `canal` | `TEXT` | `NOT NULL` | Canal de atendimento de origem (`'App Mobile'`, `'Site Web'`, `'WhatsApp'`) |
| `previsao_entrega` | `TEXT` | `NULL` | Data e hora estimada para chegada |
| `data_entrega` | `TEXT` | `NULL` | Data e hora em que a entrega foi concluída |
| `motorista` | `TEXT` | `NULL` | Identificação do entregador e veículo |
| `endereco_entrega` | `TEXT` | `NOT NULL` | Endereço de entrega selecionado no pedido |
| `subtotal` | `REAL` | `NOT NULL CHECK(subtotal >= 0)` | Valor total bruto dos itens |
| `taxa_entrega` | `REAL` | `NOT NULL DEFAULT 0.0 CHECK(taxa_entrega >= 0)` | Valor do frete aplicado |
| `desconto` | `REAL` | `NOT NULL DEFAULT 0.0 CHECK(desconto >= 0)` | Deduções e cupons aplicados |
| `total` | `REAL` | `NOT NULL CHECK(total >= 0)` | Valor líquido final cobrado |
| `forma_pagamento` | `TEXT` | `NOT NULL` | Método de quitação (ex.: `'PIX'`, `'Cartão de Crédito'`) |
| `observacao_cliente` | `TEXT` | `NULL` | Instruções especiais deixadas pelo cliente |

### 4.4. Tabela `pedido_itens`

*Linhas de itens vinculadas a cada pedido.*

| Campo | Tipo SQLite | Restrições | Descrição |
| --- | --- | --- | --- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Identificador sequencial do registro |
| `pedido_id` | `TEXT` | `NOT NULL REFERENCES pedidos(pedido_id) ON DELETE CASCADE` | Código do pedido associado |
| `sku` | `TEXT` | `NOT NULL REFERENCES produtos(sku)` | Código do produto adquirido |
| `quantidade` | `REAL` | `NOT NULL CHECK(quantidade > 0)` | Volume comprado em unidades ou quilos |
| `preco_unitario` | `REAL` | `NOT NULL CHECK(preco_unitario >= 0)` | Valor unitário no momento do pedido |
| `subtotal_item` | `REAL` | `NOT NULL CHECK(subtotal_item >= 0)` | Subtotal da linha (`quantidade * preco_unitario`) |

### 4.5. Tabela `tickets`

*Registros de ocorrências do SAC para suporte e transbordo ao time humano.*

| Campo | Tipo SQLite | Restrições | Descrição |
| --- | --- | --- | --- |
| `ticket_id` | `TEXT` | `PRIMARY KEY NOT NULL` | Protocolo único do chamado (ex.: `'TCK-2026-001'`) |
| `cliente_id` | `TEXT` | `NOT NULL REFERENCES clientes(cliente_id)` | Chave estrangeira do cliente atendido |
| `pedido_id` | `TEXT` | `NULL REFERENCES pedidos(pedido_id)` | Pedido relacionado (se houver) |
| `data_abertura` | `TEXT` | `NOT NULL` | Data/hora de abertura em formato ISO-8601 |
| `data_fechamento` | `TEXT` | `NULL` | Data/hora de encerramento em formato ISO-8601 |
| `status` | `TEXT` | `NOT NULL CHECK(status IN ('aberto', 'resolvido'))` | Estado atual da solicitação |
| `prioridade` | `TEXT` | `NOT NULL CHECK(prioridade IN ('baixa', 'media', 'alta', 'critica'))` | Grau de urgência da triagem |
| `motivo` | `TEXT` | `NOT NULL` | Classificação do problema (ex.: `'reclamacao_avaria'`, `'atraso_entrega'`) |
| `descricao` | `TEXT` | `NOT NULL` | Resumo circunstanciado gerado pelo agente |
| `resolucao` | `TEXT` | `NULL` | Registro das ações tomadas no encerramento |
| `departamento_responsavel` | `TEXT` | `NOT NULL` | Setor de atendimento (ex.: `'sac_logistica'`, `'sac_financeiro'`) |

---

## 5. DDL Completo (`schema.sql`)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS produtos (
    sku TEXT PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    preco REAL NOT NULL CHECK(preco >= 0),
    unidade TEXT NOT NULL CHECK(unidade IN ('kg', 'un')),
    estoque REAL NOT NULL DEFAULT 0 CHECK(estoque >= 0),
    secao TEXT NOT NULL,
    disponivel INTEGER NOT NULL DEFAULT 1 CHECK(disponivel IN (0, 1))
);

CREATE TABLE IF NOT EXISTS clientes (
    cliente_id TEXT PRIMARY KEY NOT NULL,
    nome TEXT NOT NULL,
    cpf TEXT NOT NULL UNIQUE,
    telefone TEXT NOT NULL,
    email TEXT NOT NULL,
    endereco TEXT NOT NULL,
    programa_fidelidade TEXT NOT NULL DEFAULT 'Clube Bronze',
    pontos_acumulados INTEGER NOT NULL DEFAULT 0 CHECK(pontos_acumulados >= 0)
);

CREATE TABLE IF NOT EXISTS pedidos (
    pedido_id TEXT PRIMARY KEY NOT NULL,
    cliente_id TEXT NOT NULL,
    data_pedido TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('em_separacao', 'em_rota', 'entregue', 'cancelado_estornado')),
    canal TEXT NOT NULL,
    previsao_entrega TEXT,
    data_entrega TEXT,
    motorista TEXT,
    endereco_entrega TEXT NOT NULL,
    subtotal REAL NOT NULL CHECK(subtotal >= 0),
    taxa_entrega REAL NOT NULL DEFAULT 0.0 CHECK(taxa_entrega >= 0),
    desconto REAL NOT NULL DEFAULT 0.0 CHECK(desconto >= 0),
    total REAL NOT NULL CHECK(total >= 0),
    forma_pagamento TEXT NOT NULL,
    observacao_cliente TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id)
);

CREATE TABLE IF NOT EXISTS pedido_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantidade REAL NOT NULL CHECK(quantidade > 0),
    preco_unitario REAL NOT NULL CHECK(preco_unitario >= 0),
    subtotal_item REAL NOT NULL CHECK(subtotal_item >= 0),
    FOREIGN KEY (pedido_id) REFERENCES pedidos(pedido_id) ON DELETE CASCADE,
    FOREIGN KEY (sku) REFERENCES produtos(sku)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY NOT NULL,
    cliente_id TEXT NOT NULL,
    pedido_id TEXT,
    data_abertura TEXT NOT NULL,
    data_fechamento TEXT,
    status TEXT NOT NULL CHECK(status IN ('aberto', 'resolvido')),
    prioridade TEXT NOT NULL CHECK(prioridade IN ('baixa', 'media', 'alta', 'critica')),
    motivo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    resolucao TEXT,
    departamento_responsavel TEXT NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id),
    FOREIGN KEY (pedido_id) REFERENCES pedidos(pedido_id)
);

-- Índices de consulta rápida
CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_cliente ON tickets(cliente_id);
```

---

## 6. Funcionalidades Centrais do Agente

1. **Consulta de Estoque e Localização:**
   * Verifica via SQL o preço, unidade e saldo de qualquer um dos 150 itens, orientando o cliente sobre o corredor/seção.

2. **Sugestão Inteligente de Substituição:**
   * Detecta produtos com saldo `0` (`disponivel = 0`) e faz busca automática por itens similares com estoque positivo na mesma categoria.

3. **Rastreamento de Pedidos:**
   * Consulta status em tempo real (`em_separacao`, `em_rota`, `entregue`), motorista e previsão de entrega baseando-se no código do pedido.

4. **Resolução de Dúvidas Operacionais (RAG):**
   * Recupera semanticamente trechos de `politicas_operacionais.md`, `faq_supermercado.yaml` e `promocoes_ativas.yaml` via FAISS.

5. **Triagem e Transbordo com Resumo Estruturado:**
   * Quando identifica um cenário fora do escopo automático (ex.: item avariado, produto vencido ou reclamação grave), gera um ticket na tabela `tickets` com prioridade alta/crítica e transfere o contexto consolidado para a fila de atendimento humano.
