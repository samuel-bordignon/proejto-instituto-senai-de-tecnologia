-- ============================================================
-- LaudoTech — IST Ambiental
-- DEV-3 — [DB-Seed] Popular tabelas legislacao, origem_amostra
--                   e legislacao_origem
-- Banco: PostgreSQL 13+ (usa gen_random_uuid())
-- Dependência: database/schema_laudotech.sql já aplicado
-- Idempotente: pode ser executado várias vezes sem duplicar dados
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1) legislacao (2 registros)
--    PDF: "Portaria GM/MS Nº888 5/21"  -> Portaria GM/MS 888/2021
--    PDF: "Portaria SES nº1468/2022"   -> Portaria SES/SC 1468/2022
-- ------------------------------------------------------------
INSERT INTO legislacao (id, nome)
VALUES
    (gen_random_uuid(), 'Portaria GM/MS 888/2021'),
    (gen_random_uuid(), 'Portaria SES/SC 1468/2022')
ON CONFLICT (nome) DO NOTHING;

-- ------------------------------------------------------------
-- 2) origem_amostra (4 registros)
--    "Agua Tratada" (PDF, sem acento) -> "Água Tratada"
-- ------------------------------------------------------------
INSERT INTO origem_amostra (id, nome)
VALUES
    (gen_random_uuid(), 'Água Consumo Humano'),
    (gen_random_uuid(), 'Água Tratada'),
    (gen_random_uuid(), 'Água Superficial (Água doce)'),
    (gen_random_uuid(), 'Água Subterrânea')
ON CONFLICT (nome) DO NOTHING;

-- ------------------------------------------------------------
-- 3) legislacao_origem (6 registros — 1 por PDF)
--    Depende dos dois blocos anteriores.
-- ------------------------------------------------------------
INSERT INTO legislacao_origem (id, fk_legislacao, fk_origem_amostra)
SELECT gen_random_uuid(), l.id, o.id
FROM (VALUES
    ('Portaria GM/MS 888/2021',  'Água Consumo Humano'),
    ('Portaria GM/MS 888/2021',  'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Consumo Humano'),
    ('Portaria SES/SC 1468/2022', 'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Superficial (Água doce)'),
    ('Portaria SES/SC 1468/2022', 'Água Subterrânea')
) AS par (legislacao_nome, origem_nome)
JOIN legislacao     l ON l.nome = par.legislacao_nome
JOIN origem_amostra o ON o.nome = par.origem_nome
ON CONFLICT (fk_legislacao, fk_origem_amostra) DO NOTHING;

-- ------------------------------------------------------------
-- 4) Trava de consistência
--    Verifica que os registros desta tarefa existem.
--    Não exige totais exatos das tabelas, para que a reexecução
--    continue válida quando outras legislações/origens forem
--    cadastradas em tarefas futuras.
-- ------------------------------------------------------------
DO $$
DECLARE
    v_leg  INT;
    v_ori  INT;
    v_par  INT;
BEGIN
    SELECT COUNT(*) INTO v_leg
    FROM legislacao
    WHERE nome IN ('Portaria GM/MS 888/2021', 'Portaria SES/SC 1468/2022');

    SELECT COUNT(*) INTO v_ori
    FROM origem_amostra
    WHERE nome IN ('Água Consumo Humano', 'Água Tratada',
                   'Água Superficial (Água doce)', 'Água Subterrânea');

    SELECT COUNT(*) INTO v_par
    FROM legislacao_origem lo
    JOIN legislacao     l ON l.id = lo.fk_legislacao
    JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
    WHERE (l.nome, o.nome) IN (
        ('Portaria GM/MS 888/2021',  'Água Consumo Humano'),
        ('Portaria GM/MS 888/2021',  'Água Tratada'),
        ('Portaria SES/SC 1468/2022', 'Água Consumo Humano'),
        ('Portaria SES/SC 1468/2022', 'Água Tratada'),
        ('Portaria SES/SC 1468/2022', 'Água Superficial (Água doce)'),
        ('Portaria SES/SC 1468/2022', 'Água Subterrânea')
    );

    IF v_leg <> 2 THEN
        RAISE EXCEPTION 'DEV-3: esperado 2 legislações, encontrado %', v_leg;
    END IF;
    IF v_ori <> 4 THEN
        RAISE EXCEPTION 'DEV-3: esperado 4 origens de amostra, encontrado %', v_ori;
    END IF;
    IF v_par <> 6 THEN
        RAISE EXCEPTION 'DEV-3: esperado 6 pares legislação/origem, encontrado %', v_par;
    END IF;
END $$;

COMMIT;

-- ------------------------------------------------------------
-- Conferência manual (critérios de aceite)
-- ------------------------------------------------------------
-- SELECT COUNT(*) FROM legislacao;        -- 2 (nesta sprint)
-- SELECT COUNT(*) FROM origem_amostra;    -- 4
-- SELECT COUNT(*) FROM legislacao_origem; -- 6
-- SELECT COUNT(*) FROM classe;            -- 0 (esta tarefa não insere classes)
--
-- SELECT l.nome AS legislacao, o.nome AS origem
-- FROM legislacao_origem lo
-- JOIN legislacao     l ON l.id = lo.fk_legislacao
-- JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
-- ORDER BY l.nome, o.nome;
