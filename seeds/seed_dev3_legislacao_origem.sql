-- ============================================================
-- LaudoTech — DEV-3: Carga de legislacao, origem_amostra e legislacao_origem
-- ============================================================

-- 1. Legislações (2 registros)
INSERT INTO legislacao (nome) VALUES
    ('Portaria GM/MS 888/2021'),
    ('Portaria SES/SC 1468/2022')
ON CONFLICT (nome) DO NOTHING;

-- 2. Origens de Amostra (4 registros com grafia padronizada)
INSERT INTO origem_amostra (nome) VALUES
    ('Água Consumo Humano'),
    ('Água Tratada'),
    ('Água Superficial (Água doce)'),
    ('Água Subterrânea')
ON CONFLICT (nome) DO NOTHING;

-- 3. Associação Legislação × Origem de Amostra (6 registros — 1 para cada PDF)
INSERT INTO legislacao_origem (fk_legislacao, fk_origem_amostra)
SELECT l.id, o.id
FROM (VALUES
    ('Portaria GM/MS 888/2021',   'Água Consumo Humano'),
    ('Portaria GM/MS 888/2021',   'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Consumo Humano'),
    ('Portaria SES/SC 1468/2022', 'Água Tratada'),
    ('Portaria SES/SC 1468/2022', 'Água Superficial (Água doce)'),
    ('Portaria SES/SC 1468/2022', 'Água Subterrânea')
) AS v(leg_nome, ori_nome)
JOIN legislacao l     ON l.nome = v.leg_nome
JOIN origem_amostra o ON o.nome = v.ori_nome
ON CONFLICT (fk_legislacao, fk_origem_amostra) DO NOTHING;
