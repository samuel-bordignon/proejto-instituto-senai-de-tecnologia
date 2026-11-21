-- ============================================================
-- LaudoTech — DEV-10: Carga Oficial CONAMA 430/2011 e CONAMA 357/2005
-- Recorte: Camada 1 — Núcleo Estrito (100% id_num reais da planilha UltraLIMS + Slide 10)
-- ============================================================
-- Pré-requisito: database/migrations/001_migracao_v2_1.sql aplicada (DEV-9)
-- Características:
--   - 100% idempotente (ON CONFLICT DO NOTHING)
--   - 28 (Fósforo Total) e 33 (Nitrogênio Amoniacal Total) são cadastrados em ensaios
--     como MANUAL_TECNICA e propositalmente omitidos de parametros (regras condicionais externas).
--   - 268 (Mercúrio) tem unidade acreditada µg/L em ensaios vs 0,01 mg/L na CONAMA 430 (RN-05).
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Novas legislações (Resoluções)
-- ------------------------------------------------------------
INSERT INTO legislacao (nome) VALUES
    ('Resolução CONAMA 430/2011'),
    ('Resolução CONAMA 357/2005')
ON CONFLICT (nome) DO NOTHING;

-- ------------------------------------------------------------
-- 2. Nova origem de amostra (Água Superficial já existe na DEV-3)
-- ------------------------------------------------------------
INSERT INTO origem_amostra (nome) VALUES
    ('Efluente Tratado')
ON CONFLICT (nome) DO NOTHING;

-- ------------------------------------------------------------
-- 3. Vínculos legislação × origem
-- ------------------------------------------------------------
INSERT INTO legislacao_origem (fk_legislacao, fk_origem_amostra)
SELECT l.id, o.id
FROM (VALUES
    ('Resolução CONAMA 430/2011', 'Efluente Tratado'),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)')
) AS v(leg_nome, ori_nome)
JOIN legislacao l     ON l.nome = v.leg_nome
JOIN origem_amostra o ON o.nome = v.ori_nome
ON CONFLICT (fk_legislacao, fk_origem_amostra) DO NOTHING;

-- ------------------------------------------------------------
-- 4. Classes das Resoluções (CONAMA 430 Art. 16 usa fk_classe IS NULL = Sem Classe)
-- ------------------------------------------------------------
INSERT INTO classe (fk_legislacao_origem, nome)
SELECT lo.id, v.classe_nome
FROM (VALUES
    ('Resolução CONAMA 430/2011', 'Efluente Tratado',             'Sanitário'),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1'),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2'),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3')
) AS v(leg_nome, ori_nome, classe_nome)
JOIN legislacao l         ON l.nome = v.leg_nome
JOIN origem_amostra o     ON o.nome = v.ori_nome
JOIN legislacao_origem lo ON lo.fk_legislacao = l.id AND lo.fk_origem_amostra = o.id
ON CONFLICT (fk_legislacao_origem, nome) DO NOTHING;

-- ------------------------------------------------------------
-- 5. Novas unidades de medida (+mL/L, +°C, +FT)
-- ------------------------------------------------------------
INSERT INTO unidade_medida (descricao) VALUES
    ('mL/L'),
    ('°C'),
    ('FT')
ON CONFLICT (descricao) DO NOTHING;

-- ------------------------------------------------------------
-- 6. 42 novos ensaios reais (planilha UltraLIMS + Slide 10) já com fk_unidade_medida
-- ------------------------------------------------------------
INSERT INTO ensaios (id_num, descricao, tipo_avaliacao, fk_unidade_medida)
SELECT v.id_num, v.descricao, v.tipo_avaliacao, u.id
FROM (VALUES
    -- Efluente (14 códigos confirmados 1:1 no Slide 10)
    (92,    'DBO (5 dias)',                              'AUTOMATICA',     'mg/L'::varchar),
    (93,    'DQO',                                       'AUTOMATICA',     'mg/L'::varchar),
    (101,   'Fósforo',                                   'AUTOMATICA',     'mg/L'::varchar),
    (104,   'Nitrato (NO3-N)',                           'AUTOMATICA',     'mg/L'::varchar),
    (105,   'Nitrito (NO2-N)',                           'AUTOMATICA',     'mg/L'::varchar),
    (106,   'Nitrogênio Amoniacal',                      'AUTOMATICA',     'mg/L'::varchar),
    (111,   'Óleos e Graxas Totais',                     'AUTOMATICA',     'mg/L'::varchar),
    (119,   'Sólidos Sedimentáveis',                     'AUTOMATICA',     'mL/L'::varchar),
    (132,   'Coliformes Termotolerantes (UFC)',          'AUTOMATICA',     'UFC/100mL'::varchar),
    (135,   'Escherichia coli (UFC)',                    'AUTOMATICA',     'UFC/100mL'::varchar),
    (144,   'Toxicidade aguda com Daphnia magna',        'MANUAL_TECNICA', 'FT'::varchar),
    (145,   'Toxicidade aguda com Vibrio fischeri',      'MANUAL_TECNICA', 'FT'::varchar),
    (259,   'Chumbo',                                    'AUTOMATICA',     'mg/L'::varchar),
    (794,   'pH',                                        'AUTOMATICA',     NULL::varchar),

    -- Demais 18 códigos reais de Efluente da planilha XLSX (CONAMA 430 Art. 16 / 21)
    (82,    'Cianeto Total',                             'AUTOMATICA',     'mg/L'::varchar),
    (97,    'Fenóis Totais',                             'AUTOMATICA',     'mg/L'::varchar),
    (110,   'Óleos e Graxas Minerais',                   'AUTOMATICA',     'mg/L'::varchar),
    (112,   'Óleos Vegetais e Gorduras Animais',         'AUTOMATICA',     'mg/L'::varchar),
    (117,   'Sulfeto',                                   'AUTOMATICA',     'mg/L'::varchar),
    (196,   'Cromo Hexavalente',                         'AUTOMATICA',     'mg/L'::varchar),
    (198,   'Ferro Dissolvido',                          'AUTOMATICA',     'mg/L'::varchar),
    (256,   'Boro',                                      'AUTOMATICA',     'mg/L'::varchar),
    (257,   'Cádmio',                                    'AUTOMATICA',     'mg/L'::varchar),
    (263,   'Estanho',                                   'AUTOMATICA',     'mg/L'::varchar),
    (268,   'Mercúrio',                                  'AUTOMATICA',     'µg/L'::varchar), -- RN-05: planilha µg/L vs lei mg/L
    (270,   'Níquel',                                    'AUTOMATICA',     'mg/L'::varchar),
    (274,   'Selênio',                                   'AUTOMATICA',     'mg/L'::varchar),
    (282,   'Zinco',                                     'AUTOMATICA',     'mg/L'::varchar),
    (784,   'Materiais Flutuantes',                      'AUTOMATICA',     NULL::varchar),
    (800,   'Temperatura - Água',                        'AUTOMATICA',     '°C'::varchar),
    (1189,  'pH',                                        'AUTOMATICA',     NULL::varchar),
    (6333,  'SUB - Cromo Hexavalente',                   'AUTOMATICA',     'mg/L'::varchar),

    -- 10 novos códigos reais de Água Superficial da planilha XLSX (CONAMA 357)
    (17,    'Cor Verdadeira',                            'AUTOMATICA',     'Pt/Co'::varchar),
    (19,    'DBO (5 dias) - Trak',                       'AUTOMATICA',     'mg/L'::varchar),
    (28,    'Fósforo Total',                             'MANUAL_TECNICA', 'mg/L'::varchar), -- condicional (fora de parametros)
    (33,    'Nitrogênio Amoniacal Total',                'MANUAL_TECNICA', 'mg/L'::varchar), -- condicional (fora de parametros)
    (59,    'Coliformes Termotolerantes (UFC)',          'AUTOMATICA',     'UFC/100mL'::varchar),
    (157,   'Cobre Dissolvido',                          'AUTOMATICA',     'mg/L'::varchar),
    (163,   'Ferro Dissolvido',                          'AUTOMATICA',     'mg/L'::varchar),
    (780,   'Cloro Residual Total',                      'AUTOMATICA',     'mg/L'::varchar),
    (791,   'Oxigênio Dissolvido',                       'AUTOMATICA',     'mg/L'::varchar),
    (15915, 'DBO (5 dias) - OD',                         'AUTOMATICA',     'mg/L'::varchar)
) AS v(id_num, descricao, tipo_avaliacao, unid_desc)
LEFT JOIN unidade_medida u ON u.descricao = v.unid_desc
WHERE v.unid_desc IS NULL OR u.id IS NOT NULL
ON CONFLICT (id_num) DO NOTHING;

-- ------------------------------------------------------------
-- 7A. Parâmetros — CONAMA 430/2011 (Efluente Tratado: Sanitário = 7 | Sem Classe = 22)
-- ------------------------------------------------------------
INSERT INTO parametros (
    fk_legislacao_origem, fk_classe, fk_ensaios, fk_unidade_medida,
    operador, valor_min, valor_max, valor_esperado
)
SELECT
    lo.id, c.id, e.id, u.id,
    v.operador, v.valor_min, v.valor_max, v.valor_esperado
FROM (VALUES
    -- Classe 'Sanitário' (Art. 21) — 7 registros
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 794,  'FAIXA',         5.0::double precision,  9.0::double precision,   NULL::varchar,      NULL::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 1189, 'FAIXA',         5.0::double precision,  9.0::double precision,   NULL::varchar,      NULL::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 800,  'MENOR_ESTRITO', NULL::double precision, 40.0::double precision,  NULL::varchar,      '°C'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 119,  'MENOR_IGUAL',   NULL::double precision, 1.0::double precision,   NULL::varchar,      'mL/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 92,   'MENOR_IGUAL',   NULL::double precision, 120.0::double precision, NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 111,  'MENOR_IGUAL',   NULL::double precision, 100.0::double precision, NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', 'Sanitário', 784,  'AUSENCIA',      NULL::double precision, NULL::double precision,  'Ausente'::varchar, NULL::varchar),

    -- Sem Classe (fk_classe IS NULL — Art. 16 + Tabela I) — 22 registros
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        794,  'FAIXA',         5.0::double precision,  9.0::double precision,   NULL::varchar,      NULL::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        1189, 'FAIXA',         5.0::double precision,  9.0::double precision,   NULL::varchar,      NULL::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        800,  'MENOR_ESTRITO', NULL::double precision, 40.0::double precision,  NULL::varchar,      '°C'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        119,  'MENOR_IGUAL',   NULL::double precision, 1.0::double precision,   NULL::varchar,      'mL/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        110,  'MENOR_IGUAL',   NULL::double precision, 20.0::double precision,  NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        112,  'MENOR_IGUAL',   NULL::double precision, 50.0::double precision,  NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        784,  'AUSENCIA',      NULL::double precision, NULL::double precision,  'Ausente'::varchar, NULL::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        256,  'MENOR_IGUAL',   NULL::double precision, 5.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        257,  'MENOR_IGUAL',   NULL::double precision, 0.2::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        259,  'MENOR_IGUAL',   NULL::double precision, 0.5::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        82,   'MENOR_IGUAL',   NULL::double precision, 1.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        196,  'MENOR_IGUAL',   NULL::double precision, 0.1::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        6333, 'MENOR_IGUAL',   NULL::double precision, 0.1::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        263,  'MENOR_IGUAL',   NULL::double precision, 4.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        198,  'MENOR_IGUAL',   NULL::double precision, 15.0::double precision,  NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        268,  'MENOR_IGUAL',   NULL::double precision, 0.01::double precision,  NULL::varchar,      'mg/L'::varchar), -- RN-05 vs µg/L
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        270,  'MENOR_IGUAL',   NULL::double precision, 2.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        106,  'MENOR_IGUAL',   NULL::double precision, 20.0::double precision,  NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        274,  'MENOR_IGUAL',   NULL::double precision, 0.30::double precision,  NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        117,  'MENOR_IGUAL',   NULL::double precision, 1.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        282,  'MENOR_IGUAL',   NULL::double precision, 5.0::double precision,   NULL::varchar,      'mg/L'::varchar),
    ('Resolução CONAMA 430/2011', 'Efluente Tratado', NULL,        97,   'MENOR_IGUAL',   NULL::double precision, 0.5::double precision,   NULL::varchar,      'mg/L'::varchar)
) AS v(leg_nome, ori_nome, classe_nome, id_num, operador, valor_min, valor_max, valor_esperado, unid_desc)
JOIN legislacao l          ON l.nome = v.leg_nome
JOIN origem_amostra o      ON o.nome = v.ori_nome
JOIN legislacao_origem lo  ON lo.fk_legislacao = l.id AND lo.fk_origem_amostra = o.id
LEFT JOIN classe c         ON c.fk_legislacao_origem = lo.id AND c.nome = v.classe_nome
JOIN ensaios e             ON e.id_num = v.id_num
LEFT JOIN unidade_medida u ON u.descricao = v.unid_desc
WHERE (v.classe_nome IS NULL OR c.id IS NOT NULL)
  AND (v.unid_desc IS NULL OR u.id IS NOT NULL)
ON CONFLICT (fk_legislacao_origem, fk_classe, fk_ensaios) DO NOTHING;

-- ------------------------------------------------------------
-- 7B. Parâmetros — CONAMA 357/2005 (Água Superficial: Cl. 1 = 27 | Cl. 2 = 28 | Cl. 3 = 23)
-- ------------------------------------------------------------
INSERT INTO parametros (
    fk_legislacao_origem, fk_classe, fk_ensaios, fk_unidade_medida,
    operador, valor_min, valor_max, valor_esperado
)
SELECT
    lo.id, c.id, e.id, u.id,
    v.operador, v.valor_min, v.valor_max, NULL
FROM (VALUES
    -- CLASSE 1 (Art. 14 + Tab. I) — 27 registros (Cor Verdadeira Cl. 1 é nível natural)
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 793,   'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 1190,  'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 791,   'MAIOR_IGUAL', 6.0::double precision,  NULL::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 19,    'MENOR_IGUAL', NULL::double precision, 3.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 15915, 'MENOR_IGUAL', NULL::double precision, 3.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 48,    'MENOR_IGUAL', NULL::double precision, 40.0::double precision,     'NTU'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 52,    'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 60,    'MENOR_IGUAL', NULL::double precision, 20000.0::double precision,  'células/mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 59,    'MENOR_IGUAL', NULL::double precision, 200.0::double precision,    'UFC/100mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 25,    'MENOR_IGUAL', NULL::double precision, 1.4::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 31,    'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 32,    'MENOR_IGUAL', NULL::double precision, 1.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 780,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 157,   'MENOR_IGUAL', NULL::double precision, 0.009::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 163,   'MENOR_IGUAL', NULL::double precision, 0.3::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 219,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 224,   'MENOR_IGUAL', NULL::double precision, 0.001::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 226,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 229,   'MENOR_IGUAL', NULL::double precision, 0.05::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 233,   'MENOR_IGUAL', NULL::double precision, 0.1::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 249,   'MENOR_IGUAL', NULL::double precision, 0.18::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 924,   'MENOR_IGUAL', NULL::double precision, 0.5::double precision,      'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 676,   'MENOR_IGUAL', NULL::double precision, 2.0::double precision,      'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 682,   'MENOR_IGUAL', NULL::double precision, 90.0::double precision,     'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 386,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 672,   'MENOR_IGUAL', NULL::double precision, 0.005::double precision,    'mg/L'::varchar), -- RN-05 vs µg/L
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 1', 382,   'MENOR_IGUAL', NULL::double precision, 0.3::double precision,      'µg/L'::varchar), -- RN-05 vs mg/L

    -- CLASSE 2 (Art. 15 — herda Tab. I + exceções) — 28 registros
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 793,   'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 1190,  'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 791,   'MAIOR_IGUAL', 5.0::double precision,  NULL::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 19,    'MENOR_IGUAL', NULL::double precision, 5.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 15915, 'MENOR_IGUAL', NULL::double precision, 5.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 48,    'MENOR_IGUAL', NULL::double precision, 100.0::double precision,    'NTU'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 17,    'MENOR_IGUAL', NULL::double precision, 75.0::double precision,     'Pt/Co'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 52,    'MENOR_IGUAL', NULL::double precision, 30.0::double precision,     'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 60,    'MENOR_IGUAL', NULL::double precision, 50000.0::double precision,  'células/mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 59,    'MENOR_IGUAL', NULL::double precision, 1000.0::double precision,   'UFC/100mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 25,    'MENOR_IGUAL', NULL::double precision, 1.4::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 31,    'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 32,    'MENOR_IGUAL', NULL::double precision, 1.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 780,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 157,   'MENOR_IGUAL', NULL::double precision, 0.009::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 163,   'MENOR_IGUAL', NULL::double precision, 0.3::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 219,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 224,   'MENOR_IGUAL', NULL::double precision, 0.001::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 226,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 229,   'MENOR_IGUAL', NULL::double precision, 0.05::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 233,   'MENOR_IGUAL', NULL::double precision, 0.1::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 249,   'MENOR_IGUAL', NULL::double precision, 0.18::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 924,   'MENOR_IGUAL', NULL::double precision, 0.5::double precision,      'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 676,   'MENOR_IGUAL', NULL::double precision, 2.0::double precision,      'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 682,   'MENOR_IGUAL', NULL::double precision, 90.0::double precision,     'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 386,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 672,   'MENOR_IGUAL', NULL::double precision, 0.005::double precision,    'mg/L'::varchar), -- RN-05 vs µg/L
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 2', 382,   'MENOR_IGUAL', NULL::double precision, 0.3::double precision,      'µg/L'::varchar), -- RN-05 vs mg/L

    -- CLASSE 3 (Art. 16 + Tab. III) — 23 registros (sem 780, 924, 676, 682, 382)
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 793,   'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 1190,  'FAIXA',       6.0::double precision,  9.0::double precision,      NULL::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 791,   'MAIOR_IGUAL', 4.0::double precision,  NULL::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 19,    'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 15915, 'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 48,    'MENOR_IGUAL', NULL::double precision, 100.0::double precision,    'NTU'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 17,    'MENOR_IGUAL', NULL::double precision, 75.0::double precision,     'Pt/Co'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 52,    'MENOR_IGUAL', NULL::double precision, 60.0::double precision,     'µg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 60,    'MENOR_IGUAL', NULL::double precision, 100000.0::double precision, 'células/mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 59,    'MENOR_IGUAL', NULL::double precision, 4000.0::double precision,   'UFC/100mL'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 25,    'MENOR_IGUAL', NULL::double precision, 1.4::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 31,    'MENOR_IGUAL', NULL::double precision, 10.0::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 32,    'MENOR_IGUAL', NULL::double precision, 1.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 157,   'MENOR_IGUAL', NULL::double precision, 0.013::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 163,   'MENOR_IGUAL', NULL::double precision, 5.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 219,   'MENOR_IGUAL', NULL::double precision, 0.033::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 224,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 226,   'MENOR_IGUAL', NULL::double precision, 0.033::double precision,    'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 229,   'MENOR_IGUAL', NULL::double precision, 0.05::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 233,   'MENOR_IGUAL', NULL::double precision, 0.5::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 249,   'MENOR_IGUAL', NULL::double precision, 5.0::double precision,      'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 386,   'MENOR_IGUAL', NULL::double precision, 0.01::double precision,     'mg/L'::varchar),
    ('Resolução CONAMA 357/2005', 'Água Superficial (Água doce)', 'Classe 3', 672,   'MENOR_IGUAL', NULL::double precision, 0.005::double precision,    'mg/L'::varchar)  -- RN-05 vs µg/L
) AS v(leg_nome, ori_nome, classe_nome, id_num, operador, valor_min, valor_max, unid_desc)
JOIN legislacao l          ON l.nome = v.leg_nome
JOIN origem_amostra o      ON o.nome = v.ori_nome
JOIN legislacao_origem lo  ON lo.fk_legislacao = l.id AND lo.fk_origem_amostra = o.id
JOIN classe c              ON c.fk_legislacao_origem = lo.id AND c.nome = v.classe_nome
JOIN ensaios e             ON e.id_num = v.id_num
LEFT JOIN unidade_medida u ON u.descricao = v.unid_desc
WHERE v.unid_desc IS NULL OR u.id IS NOT NULL
ON CONFLICT (fk_legislacao_origem, fk_classe, fk_ensaios) DO NOTHING;

COMMIT;
