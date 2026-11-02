-- ============================================================
-- LaudoTech — DEV-3 (pré-requisito do seed)
-- Cria origem_amostra e legislacao_origem e garante unicidade
-- do nome em legislacao. PostgreSQL 13+. Idempotente.
-- Executar após database/schema_laudotech.sql.
-- ============================================================

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_legislacao_nome
    ON legislacao (nome);

CREATE TABLE IF NOT EXISTS origem_amostra (
    id   UUID        PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_origem_amostra_nome
    ON origem_amostra (nome);

-- Associativa com id próprio: será referenciada por
-- parametros.fk_legislacao_origem.
CREATE TABLE IF NOT EXISTS legislacao_origem (
    id                UUID PRIMARY KEY,
    fk_legislacao     UUID NOT NULL
        REFERENCES legislacao (id)     ON DELETE RESTRICT,
    fk_origem_amostra UUID NOT NULL
        REFERENCES origem_amostra (id) ON DELETE RESTRICT,
    CONSTRAINT uq_legislacao_origem UNIQUE (fk_legislacao, fk_origem_amostra)
);

COMMIT;
