-- ============================================================
-- LaudoTech — IST Ambiental
-- Migração 001 (DEV-9): Evolução do Schema v2.0 -> v2.2
-- ============================================================
-- Características:
--   - 100% idempotente (pode ser reexecutada sem erro)
--   - Preserva integralmente os 298 ensaios e 713 parâmetros (DEV-3..DEV-7)
--   - Mantém o banco estritamente normalizado (sem colunas/tabelas redundantes)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Unidade de trabalho acreditada em ensaios (RN-05 / RNF-02)
-- ------------------------------------------------------------
ALTER TABLE ensaios
    ADD COLUMN IF NOT EXISTS fk_unidade_medida UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_ensaios_unidade'
    ) THEN
        ALTER TABLE ensaios
            ADD CONSTRAINT fk_ensaios_unidade
            FOREIGN KEY (fk_unidade_medida) REFERENCES unidade_medida (id) ON DELETE RESTRICT;
    END IF;
END $$;

-- Backfill A: ensaios que possuem exatamente 1 unidade distinta em parametros (293 ensaios físicos)
UPDATE ensaios e
SET fk_unidade_medida = sub.fk_unidade_medida
FROM (
    SELECT
        fk_ensaios,
        MIN(fk_unidade_medida::text)::uuid AS fk_unidade_medida
    FROM parametros
    WHERE fk_unidade_medida IS NOT NULL
    GROUP BY fk_ensaios
    HAVING COUNT(DISTINCT fk_unidade_medida) = 1
) sub
WHERE e.id = sub.fk_ensaios
  AND e.fk_unidade_medida IS NULL;

-- Backfill B: ensaios VOC multi-unidade na carga DEV-6 (690 e 691 -> µg/L, padrão GC-MS/planilha)
UPDATE ensaios e
SET fk_unidade_medida = u.id
FROM unidade_medida u
WHERE u.descricao = 'µg/L'
  AND e.id_num IN (690, 691)
  AND e.fk_unidade_medida IS NULL;

-- ------------------------------------------------------------
-- 2. Suporte a múltiplas Classes + NULL em parametros (RN-06)
-- ------------------------------------------------------------
ALTER TABLE parametros
    DROP CONSTRAINT IF EXISTS uq_parametros_leg_origem_ensaio;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_parametros_regra'
    ) THEN
        ALTER TABLE parametros
            ADD CONSTRAINT uq_parametros_regra
            UNIQUE NULLS NOT DISTINCT (fk_legislacao_origem, fk_classe, fk_ensaios);
    END IF;
END $$;

-- ------------------------------------------------------------
-- 3. Unicidade em classe, amostra e resultado_amostra (RNF-03)
-- ------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_classe_leg_origem_nome'
    ) THEN
        ALTER TABLE classe
            ADD CONSTRAINT uq_classe_leg_origem_nome
            UNIQUE (fk_legislacao_origem, nome);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_amostra_codigo'
    ) THEN
        ALTER TABLE amostra
            ADD CONSTRAINT uq_amostra_codigo
            UNIQUE (codigo_amostra);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_resultado_amostra_ensaio'
    ) THEN
        ALTER TABLE resultado_amostra
            ADD CONSTRAINT uq_resultado_amostra_ensaio
            UNIQUE (fk_amostra, fk_ensaios);
    END IF;
END $$;

-- ------------------------------------------------------------
-- 4. Flexibilização de usuario (RF-01) e ampliação de local_coleta
-- ------------------------------------------------------------
ALTER TABLE usuario
    ALTER COLUMN senha_hash TYPE VARCHAR(100);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_usuario_nome'
    ) THEN
        ALTER TABLE usuario
            ADD CONSTRAINT uq_usuario_nome
            UNIQUE (nome_usuario);
    END IF;
END $$;

ALTER TABLE local_coleta
    ALTER COLUMN nome_identificacao TYPE VARCHAR(120);

-- ------------------------------------------------------------
-- 5. Nova tabela log_alteracao (Auditoria RN-10)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS log_alteracao (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_amostra           UUID        NOT NULL REFERENCES amostra (id) ON DELETE CASCADE,
    fk_resultado_amostra UUID        REFERENCES resultado_amostra (id) ON DELETE CASCADE,
    fk_usuario           UUID        NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    campo_alterado       VARCHAR(50) NOT NULL, -- 'conformidade' | 'parecer_geral' | 'minuta'
    valor_anterior       TEXT,
    valor_novo           TEXT        NOT NULL,
    observacao           TEXT,
    data_alteracao       TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 6. Índices de desempenho para histórico e auditoria (RNF-05)
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_amostra_local_data
    ON amostra (fk_local_coleta, data_coleta DESC);

CREATE INDEX IF NOT EXISTS idx_resultado_amostra_ensaio
    ON resultado_amostra (fk_ensaios, fk_amostra);

CREATE INDEX IF NOT EXISTS idx_log_alteracao_amostra
    ON log_alteracao (fk_amostra, data_alteracao DESC);

COMMIT;
