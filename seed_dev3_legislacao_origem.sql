-- ============================================================
-- LaudoTech — DEV-3: carga de legislacao, origem_amostra e
-- legislacao_origem. PostgreSQL 13+.
-- Idempotente: pode ser executado várias vezes sem duplicar.
-- Requer: database/migrations/002_origem_amostra_legislacao_origem.sql
-- A tabela classe não recebe registros nesta carga.
-- ============================================================

BEGIN;

-- 1) legislacao (2 registros)
INSERT INTO legislacao (id, nome)
SELECT gen_random_uuid(), v.nome
FROM (VALUES
    ('Portaria GM/MS 888/2021'),
    ('Portaria SES/SC 1468/2022')
) AS v(nome)
ON CONFLICT (nome) DO NOTHING;

-- 2) origem_amostra (4 registros, grafia padronizada)
INSERT INTO origem_amostra (id, nome)
SELECT gen_random_uuid(), v.nome
FROM (VALUES
    ('Água Consumo Humano'),
    ('Água Tratada'),
    ('Água Superficial (Água doce)'),
    ('Água Subterrânea')
) AS v(nome)
ON CONFLICT (nome) DO NOTHING;

-- 3) legislacao_origem (6 registros; FKs resolvidas pelo nome)
INSERT INTO legislacao_origem (id, fk_legislacao, fk_origem_amostra)
SELECT gen_random_uuid(), l.id, o.id
FROM (VALUES
    ('Portaria GM/MS 888/2021',   'Água Consumo Humano'),
    ('Portaria GM/MS 888/2021',   'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Consumo Humano'),
    ('Portaria SES/SC 1468/2022', 'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Superficial (Água doce)'),
    ('Portaria SES/SC 1468/2022', 'Água Subterrânea')
) AS v(leg, ori)
JOIN legislacao     l ON l.nome = v.leg
JOIN origem_amostra o ON o.nome = v.ori
ON CONFLICT (fk_legislacao, fk_origem_amostra) DO NOTHING;

-- 4) Conferência: aborta a transação se algum registro esperado faltar.
--    Considera apenas os registros desta carga, para não falhar caso
--    outras legislações sejam cadastradas depois.
DO $$
DECLARE
    n_leg INT; n_ori INT; n_lo INT;
BEGIN
    SELECT COUNT(*) INTO n_leg FROM legislacao
     WHERE nome IN ('Portaria GM/MS 888/2021', 'Portaria SES/SC 1468/2022');

    SELECT COUNT(*) INTO n_ori FROM origem_amostra
     WHERE nome IN ('Água Consumo Humano', 'Água Tratada',
                    'Água Superficial (Água doce)', 'Água Subterrânea');

    SELECT COUNT(*) INTO n_lo
      FROM legislacao_origem lo
      JOIN legislacao     l ON l.id = lo.fk_legislacao
      JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
     WHERE l.nome IN ('Portaria GM/MS 888/2021', 'Portaria SES/SC 1468/2022')
       AND o.nome IN ('Água Consumo Humano', 'Água Tratada',
                      'Água Superficial (Água doce)', 'Água Subterrânea');

    IF n_leg <> 2 OR n_ori <> 4 OR n_lo <> 6 THEN
        RAISE EXCEPTION
          'Carga DEV-3 inconsistente: legislacao=% (esperado 2), origem_amostra=% (esperado 4), legislacao_origem=% (esperado 6)',
          n_leg, n_ori, n_lo;
    END IF;
END $$;

COMMIT;
