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
CREATE INDEX IF NOT EXISTS idx_pedido_itens_pedido ON pedido_itens(pedido_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_cliente ON tickets(cliente_id);
