-- ============================================================
-- LaudoTech — unidade_medida: unicidade da descrição
-- Pré-requisito do seed de unidades (ON CONFLICT) e proteção
-- contra duplicatas semânticas. PostgreSQL 13+. Idempotente.
-- Executar após database/schema_laudotech.sql.
-- ============================================================

BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_unidade_medida_descricao
    ON unidade_medida (descricao);

COMMIT;
