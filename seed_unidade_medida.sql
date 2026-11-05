-- ============================================================
-- LaudoTech — [DB-Seed] Popular tabela unidade_medida
-- PostgreSQL 13+. Idempotente: pode ser executado várias vezes.
-- Requer: database/migrations/003_unidade_medida_unique.sql
--
-- Fonte: unidades distintas de staging_vmps_validos.csv.
-- Deve rodar ANTES da carga de parametros (fk_unidade_medida).
--
-- MAPA DE NORMALIZAÇÃO (bruto -> padronizado) — referência para a
-- carga de parametros (DEV-6). Espelhado em mapa_unidades.py.
--   * padronizado NULL  = unidade NÃO cadastrada.
--       - ''                   : ensaios adimensionais (pH 793/1190,
--                                Razão de Nitrito e Nitrato 7865,
--                                SUB - Gosto e Odor 7138):
--                                parametros.fk_unidade_medida = NULL.
--       - 'Aus/Pres em 100mL'  : não é unidade cadastrável.
--   * 'ppb' -> 'µg/L' (1 ppb = 1 µg/L em água). Decisão pendente de
--     alinhamento com o time; para manter 'ppb' como unidade própria,
--     troque a linha ('ppb', 'µg/L') por ('ppb', 'ppb') abaixo e em
--     mapa_unidades.py.
-- ============================================================

BEGIN;

WITH mapa (bruto, padronizado) AS (VALUES
    ('µg/L',                'µg/L'),
    ('ug/L',                 'µg/L'),
    ('ppb',                  'µg/L'),
    ('mg/L',                 'mg/L'),
    ('Bq/L',                 'Bq/L'),
    ('UFC/100mL',            'UFC/100mL'),
    ('NMP/100 mL',           'NMP/100mL'),
    ('NMP/100mL',            'NMP/100mL'),
    ('NTU',                  'NTU'),
    ('Pt/Co',                'Pt/Co'),
    ('Intensidade',          'Intensidade'),
    ('células/mL',           'células/mL'),
    ('Aus/Pres em 100mL',    NULL),
    ('',                     NULL)
)
INSERT INTO unidade_medida (id, descricao)
SELECT gen_random_uuid(), p.padronizado
FROM (SELECT DISTINCT padronizado FROM mapa WHERE padronizado IS NOT NULL) AS p
ON CONFLICT (descricao) DO NOTHING;

-- Conferência: aborta a transação se faltar unidade esperada ou se
-- existir descrição vazia, 'Aus/Pres' ou variante não normalizada.
DO $$
DECLARE
    n_esperadas INT; n_invalidas INT;
BEGIN
    SELECT COUNT(*) INTO n_esperadas FROM unidade_medida
     WHERE descricao IN ('µg/L', 'mg/L', 'Bq/L', 'UFC/100mL', 'NMP/100mL',
                         'NTU', 'Pt/Co', 'Intensidade', 'células/mL');

    SELECT COUNT(*) INTO n_invalidas FROM unidade_medida
     WHERE btrim(descricao) = ''
        OR descricao ILIKE 'Aus/Pres%'
        OR descricao IN ('ug/L', 'ppb', 'NMP/100 mL')
        OR descricao LIKE '%' || chr(956) || '%';   -- mu grego (U+03BC)

    IF n_esperadas <> 9 OR n_invalidas <> 0 THEN
        RAISE EXCEPTION
          'Carga unidade_medida inconsistente: esperadas=% (esperado 9), invalidas=% (esperado 0)',
          n_esperadas, n_invalidas;
    END IF;
END $$;

COMMIT;
