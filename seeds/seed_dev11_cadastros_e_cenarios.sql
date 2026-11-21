-- ============================================================
-- LaudoTech — DEV-11: Cadastros Base Operacionais e Seed de Cenários (CT-01 a CT-16)
-- ============================================================
-- Pré-requisitos:
--   - database/migrations/001_migracao_v2_1.sql (DEV-9)
--   - seeds/seed_dev10_conama_430_357.sql       (DEV-10)
-- Características:
--   - 100% idempotente (UUIDs determinísticos + ON CONFLICT DO NOTHING)
--   - Preserva os cadastros válidos existentes (Cervejaria Vale do Itajaí e Águas de Blumenau)
--   - Remove apenas o cliente residual 'teste' (c3066687-ec21-4768-9347-d0e79f01de79)
--   - Usa resultados 100% reais da planilha UltraLIMS + séries históricas controladas (CT-01..CT-16)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Limpeza segura do cliente residual de teste
-- ------------------------------------------------------------
DELETE FROM cliente
WHERE id = 'c3066687-ec21-4768-9347-d0e79f01de79'
  AND razao_social = 'teste';

-- ------------------------------------------------------------
-- 2. Usuários conferentes (RF-01 — senha simples MVP: 123456)
-- ------------------------------------------------------------
INSERT INTO usuario (id, nome_usuario, senha_hash) VALUES
    ('aaaa0001-0000-4000-8000-000000000001', 'samuel.wiegand',  '123456'),
    ('aaaa0002-0000-4000-8000-000000000002', 'maria.cardoso',   '123456'),
    ('aaaa0003-0000-4000-8000-000000000003', 'bruno.dombroski', '123456'),
    ('aaaa0004-0000-4000-8000-000000000004', 'conferente',      '123456')
ON CONFLICT (nome_usuario) DO NOTHING;

-- ------------------------------------------------------------
-- 3. Laboratório
-- ------------------------------------------------------------
INSERT INTO laboratorio (id, nome) VALUES
    ('bbbb0001-0000-4000-8000-000000000001', 'IST Ambiental — SENAI Blumenau')
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------
-- 4. Clientes (preserva 1111...01 e 1111...02; adiciona SAMAE e Têxtil Garcia)
-- ------------------------------------------------------------
INSERT INTO cliente (id, razao_social, cnpj, cidade, uf, contato) VALUES
    ('11111111-1111-4111-8111-111111111101', 'Cervejaria Vale do Itajaí Ltda', '12345678000190', 'Blumenau', 'SC', '(47) 3321-1000'),
    ('11111111-1111-4111-8111-111111111102', 'Águas de Blumenau S/A',          '23456789000180', 'Blumenau', 'SC', '(47) 3321-2000'),
    ('11111111-1111-4111-8111-111111111103', 'SAMAE Blumenau',                 '83779462000186', 'Blumenau', 'SC', '(47) 3331-8400'),
    ('11111111-1111-4111-8111-111111111104', 'Têxtil Garcia S/A',              '82640558000104', 'Blumenau', 'SC', '(47) 3326-5000')
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------
-- 5. Propostas Comerciais (preserva 2222...01 e 2222...02; adiciona ETE, SAMAE, Têxtil)
-- ------------------------------------------------------------
INSERT INTO proposta_comercial (id, data_inicio, data_fim, status, fk_cliente) VALUES
    ('22222222-2222-4222-8222-222222222201', '2026-01-01', '2026-12-31', TRUE, '11111111-1111-4111-8111-111111111101'), -- Cervejaria Potabilidade
    ('22222222-2222-4222-8222-222222222202', '2026-01-01', '2026-12-31', TRUE, '11111111-1111-4111-8111-111111111102'), -- Águas de Blumenau
    ('22222222-2222-4222-8222-222222222203', '2026-01-01', '2026-12-31', TRUE, '11111111-1111-4111-8111-111111111101'), -- Cervejaria ETE
    ('22222222-2222-4222-8222-222222222204', '2026-01-01', '2026-12-31', TRUE, '11111111-1111-4111-8111-111111111103'), -- SAMAE Águas Superficiais
    ('22222222-2222-4222-8222-222222222205', '2026-01-01', '2026-12-31', TRUE, '11111111-1111-4111-8111-111111111104')  -- Têxtil Garcia Efluente
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------
-- 6. Locais de Coleta e Vínculos (local_proposta / proposta_legislacao)
-- ------------------------------------------------------------
INSERT INTO local_coleta (id, nome_identificacao) VALUES
    ('33333333-3333-4333-8333-333333333301', 'Ponto 01 — Reservatório principal'),
    ('33333333-3333-4333-8333-333333333302', 'Ponto 02 — Saída do tratamento'),
    ('33333333-3333-4333-8333-333333333303', 'ETA Central — Filtro 03'),
    ('33333333-3333-4333-8333-333333333304', 'Rede de distribuição — Bairro Velha'),
    ('33333333-3333-4333-8333-333333333305', 'Saída — Efluente Sanitário (ETE 01)'),
    ('33333333-3333-4333-8333-333333333306', 'ETE — Linha B (Lagoa)'),
    ('33333333-3333-4333-8333-333333333307', 'Captação — Rio Itajaí-Açu'),
    ('33333333-3333-4333-8333-333333333308', 'Montante ETA Central'),
    ('33333333-3333-4333-8333-333333333309', 'Saída Efluente Industrial 02')
ON CONFLICT (id) DO NOTHING;

INSERT INTO local_proposta (fk_local_coleta, fk_proposta_comercial) VALUES
    ('33333333-3333-4333-8333-333333333301', '22222222-2222-4222-8222-222222222201'),
    ('33333333-3333-4333-8333-333333333302', '22222222-2222-4222-8222-222222222201'),
    ('33333333-3333-4333-8333-333333333303', '22222222-2222-4222-8222-222222222202'),
    ('33333333-3333-4333-8333-333333333304', '22222222-2222-4222-8222-222222222202'),
    ('33333333-3333-4333-8333-333333333305', '22222222-2222-4222-8222-222222222203'),
    ('33333333-3333-4333-8333-333333333306', '22222222-2222-4222-8222-222222222203'),
    ('33333333-3333-4333-8333-333333333307', '22222222-2222-4222-8222-222222222204'),
    ('33333333-3333-4333-8333-333333333308', '22222222-2222-4222-8222-222222222204'),
    ('33333333-3333-4333-8333-333333333309', '22222222-2222-4222-8222-222222222205')
ON CONFLICT (fk_local_coleta, fk_proposta_comercial) DO NOTHING;

INSERT INTO proposta_legislacao (fk_legislacao, fk_proposta_comercial)
SELECT l.id, v.prop_id::uuid
FROM (VALUES
    ('Portaria GM/MS 888/2021',   '22222222-2222-4222-8222-222222222201'),
    ('Portaria SES/SC 1468/2022', '22222222-2222-4222-8222-222222222201'),
    ('Portaria GM/MS 888/2021',   '22222222-2222-4222-8222-222222222202'),
    ('Portaria SES/SC 1468/2022', '22222222-2222-4222-8222-222222222202'),
    ('Resolução CONAMA 430/2011', '22222222-2222-4222-8222-222222222203'),
    ('Resolução CONAMA 357/2005', '22222222-2222-4222-8222-222222222204'),
    ('Portaria SES/SC 1468/2022', '22222222-2222-4222-8222-222222222204'),
    ('Resolução CONAMA 430/2011', '22222222-2222-4222-8222-222222222205')
) AS v(leg_nome, prop_id)
JOIN legislacao l ON l.nome = v.leg_nome
ON CONFLICT (fk_legislacao, fk_proposta_comercial) DO NOTHING;

-- ------------------------------------------------------------
-- 7. Amostras Reais (UltraLIMS) + Séries Históricas (CT-01 a CT-16)
-- ------------------------------------------------------------
INSERT INTO amostra (
    codigo_amostra, codigo_amostra_externo, data_coleta, data_conclusao,
    fk_local_coleta, fk_origem_amostra, fk_usuario, fk_laboratorio
)
SELECT
    v.cod, v.ext, v.dt_col::date, v.dt_conc::date,
    v.loc_id::uuid, o.id,
    'aaaa0001-0000-4000-8000-000000000001'::uuid,
    'bbbb0001-0000-4000-8000-000000000001'::uuid
FROM (VALUES
    -- [ETE 01] Série histórica (5 anteriores) + Amostra Real 63450/2026 (Slide 10/12 — CT-03, CT-11, CT-13, CT-16)
    ('58110/2026', NULL,             '2026-02-15', '2026-02-24', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),
    ('59201/2026', NULL,             '2026-03-16', '2026-03-25', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),
    ('60144/2026', NULL,             '2026-04-14', '2026-04-23', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),
    ('61210/2026', NULL,             '2026-05-15', '2026-05-24', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),
    ('62308/2026', NULL,             '2026-06-16', '2026-06-25', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),
    ('63450/2026', '14984.BNU.2026', '2026-07-15', '2026-07-27', '33333333-3333-4333-8333-333333333305', 'Efluente Tratado'),

    -- [ETE Linha B] Amostra Real 63413/2026 (CT-08) + Fronteiras controladas 68001/68002 (CT-05, CT-08 RN-03)
    ('63413/2026', NULL,             '2026-07-21', '2026-07-28', '33333333-3333-4333-8333-333333333306', 'Efluente Tratado'),
    ('68001/2026', NULL,             '2026-07-22', '2026-07-29', '33333333-3333-4333-8333-333333333306', 'Efluente Tratado'),
    ('68002/2026', NULL,             '2026-07-23', '2026-07-30', '33333333-3333-4333-8333-333333333306', 'Efluente Tratado'),

    -- [Têxtil Garcia Industrial 02] 1 anterior (n < 3 -> CT-12) + Amostra Real 67019/2026 (RN-05 268 Hg -> CT-09)
    ('66120/2026', NULL,             '2026-06-18', '2026-06-27', '33333333-3333-4333-8333-333333333309', 'Efluente Tratado'),
    ('67019/2026', NULL,             '2026-07-21', '2026-07-30', '33333333-3333-4333-8333-333333333309', 'Efluente Tratado'),

    -- [SAMAE Captação Rio Itajaí-Açu] 5 anteriores com <LQ (CT-14) + Amostra Real 65462/2026 (CT-06)
    ('60110/2026', NULL,             '2026-02-18', '2026-02-26', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),
    ('61190/2026', NULL,             '2026-03-19', '2026-03-27', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),
    ('62100/2026', NULL,             '2026-04-18', '2026-04-26', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),
    ('63105/2026', NULL,             '2026-05-18', '2026-05-26', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),
    ('64112/2026', NULL,             '2026-06-19', '2026-06-27', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),
    ('65462/2026', NULL,             '2026-07-16', '2026-07-28', '33333333-3333-4333-8333-333333333307', 'Água Superficial (Água doce)'),

    -- [SAMAE Montante ETA Central] Amostras Reais 64283/2026 (CT-04: Cl. 1 vs 2 vs 3) e 65335/2026 (CT-06 metais)
    ('64283/2026', NULL,             '2026-07-13', '2026-07-30', '33333333-3333-4333-8333-333333333308', 'Água Superficial (Água doce)'),
    ('65335/2026', NULL,             '2026-07-10', '2026-07-24', '33333333-3333-4333-8333-333333333308', 'Água Superficial (Água doce)'),

    -- [Cervejaria Potabilidade] CT-01 (100% Conforme) e CT-02 (Conflito 877 GM888 vs SES1468)
    ('4765/2026',  NULL,             '2026-07-14', '2026-07-22', '33333333-3333-4333-8333-333333333301', 'Água Tratada'),
    ('4766/2026',  NULL,             '2026-07-15', '2026-07-23', '33333333-3333-4333-8333-333333333302', 'Água Tratada'),

    -- [Águas de Blumenau — ETA Central Filtro 03] 10 coletas ao longo de 10 meses (CT-15 + CT-07 >LS)
    ('50101/2025', NULL,             '2025-10-15', '2025-10-22', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- > 6 meses (fora janela)
    ('51102/2025', NULL,             '2025-12-10', '2025-12-18', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- > 6 meses (fora janela)
    ('52103/2026', NULL,             '2026-02-05', '2026-02-12', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#7 -> fora teto 6)
    ('53104/2026', NULL,             '2026-03-01', '2026-03-08', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#6)
    ('54105/2026', NULL,             '2026-03-25', '2026-04-02', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#5)
    ('55106/2026', NULL,             '2026-04-20', '2026-04-28', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#4)
    ('56107/2026', NULL,             '2026-05-15', '2026-05-23', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#3)
    ('57108/2026', NULL,             '2026-06-10', '2026-06-18', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#2)
    ('58109/2026', NULL,             '2026-07-01', '2026-07-08', '33333333-3333-4333-8333-333333333303', 'Água Tratada'), -- dentro 6m (#1)
    ('68010/2026', NULL,             '2026-07-20', '2026-07-28', '33333333-3333-4333-8333-333333333303', 'Água Tratada')  -- Atual (CT-07 >LS)
) AS v(cod, ext, dt_col, dt_conc, loc_id, orig_nome)
JOIN origem_amostra o ON o.nome = v.orig_nome
ON CONFLICT (codigo_amostra) DO NOTHING;

-- ------------------------------------------------------------
-- 8. Resultados das Amostras (resultado_amostra)
-- ------------------------------------------------------------
INSERT INTO resultado_amostra (fk_amostra, fk_ensaios, valor_bruto, valor_numerico, qualificador, data_analise)
SELECT a.id, e.id, v.bruto, v.num, v.qual, a.data_conclusao::timestamp
FROM (VALUES
    -- === ETE 01: 5 coletas anteriores (para histórico 6m + CT-13 OGT desvio dentro do VMP) ===
    ('58110/2026', 794, '7,85',  7.85,  NULL), ('58110/2026', 92,  '18,0',  18.0,  NULL), ('58110/2026', 111, '6,0',   6.0,   NULL), ('58110/2026', 119, '<0,3',  0.3,   '<'), ('58110/2026', 106, '<0,20', 0.20,  '<'), ('58110/2026', 259, '0,02',  0.02,  NULL),
    ('59201/2026', 794, '7,94',  7.94,  NULL), ('59201/2026', 92,  '20,0',  20.0,  NULL), ('59201/2026', 111, '7,0',   7.0,   NULL), ('59201/2026', 119, '0,4',   0.4,   NULL), ('59201/2026', 106, '28,4',  28.4,  NULL), ('59201/2026', 259, '0,03',  0.03,  NULL),
    ('60144/2026', 794, '7,88',  7.88,  NULL), ('60144/2026', 92,  '19,0',  19.0,  NULL), ('60144/2026', 111, '6,5',   6.5,   NULL), ('60144/2026', 119, '<0,3',  0.3,   '<'), ('60144/2026', 106, '34,1',  34.1,  NULL), ('60144/2026', 259, '0,02',  0.02,  NULL),
    ('61210/2026', 794, '7,96',  7.96,  NULL), ('61210/2026', 92,  '21,0',  21.0,  NULL), ('61210/2026', 111, '7,2',   7.2,   NULL), ('61210/2026', 119, '0,5',   0.5,   NULL), ('61210/2026', 106, '41,8',  41.8,  NULL), ('61210/2026', 259, '0,03',  0.03,  NULL),
    ('62308/2026', 794, '7,89',  7.89,  NULL), ('62308/2026', 92,  '20,0',  20.0,  NULL), ('62308/2026', 111, '6,8',   6.8,   NULL), ('62308/2026', 119, '<0,3',  0.3,   '<'), ('62308/2026', 106, '46,5',  46.5,  NULL), ('62308/2026', 259, '0,04',  0.04,  NULL),

    -- === ETE 01: Amostra REAL 63450/2026 (14 ensaios idênticos à linha 99 do XLSX / Slide 10) ===
    ('63450/2026', 259, '0,04',  0.04,  NULL),
    ('63450/2026', 794, '7,91',  7.91,  NULL),
    ('63450/2026', 92,  '<5,00', 5.0,   '<'),
    ('63450/2026', 93,  '<25',   25.0,  '<'),
    ('63450/2026', 106, '71',    71.0,  NULL),
    ('63450/2026', 119, '<0,3',  0.3,   '<'),
    ('63450/2026', 101, '1,72',  1.72,  NULL),
    ('63450/2026', 132, '<10',   10.0,  '<'),
    ('63450/2026', 111, '14',    14.0,  NULL), -- Conforme (<=100), mas > mu+0.20*sigma (CT-13!)
    ('63450/2026', 104, '<3,00', 3.0,   '<'),
    ('63450/2026', 105, '<3,00', 3.0,   '<'),
    ('63450/2026', 144, '1',     1.0,   NULL),
    ('63450/2026', 145, '2',     2.0,   NULL),
    ('63450/2026', 135, '<10',   10.0,  '<'),

    -- === ETE Linha B: Amostra REAL 63413/2026 (CT-08 Presente) + Fronteiras 68001 / 68002 (CT-05, CT-08) ===
    ('63413/2026', 794, '9,3',      9.3,    NULL),
    ('63413/2026', 106, '297,41',   297.41, NULL),
    ('63413/2026', 784, 'Presente', NULL,   NULL),
    ('63413/2026', 800, '20',       20.0,   NULL),

    ('68001/2026', 110, '20,0',     20.0,   NULL), -- fronteira <= 20,0 -> Conforme
    ('68001/2026', 800, '40,0',     40.0,   NULL), -- fronteira < 40,0 (MENOR_ESTRITO) -> Nao conforme!
    ('68001/2026', 794, '7,20',     7.20,   NULL),
    ('68001/2026', 784, 'Ausente',  NULL,   NULL),

    ('68002/2026', 110, '20,0',     20.0,   NULL), -- fronteira <= 20,0 -> Conforme
    ('68002/2026', 800, '39,9',     39.9,   NULL), -- fronteira < 40,0 -> Conforme
    ('68002/2026', 794, '7,10',     7.10,   NULL),
    ('68002/2026', 119, 'Ausente',  NULL,   NULL), -- RN-03: Ausente em numerico -> 0.0 -> Conforme!
    ('68002/2026', 784, 'Ausente',  NULL,   NULL),

    -- === Têxtil Garcia Industrial 02: 1 anterior (CT-12) + Amostra REAL 67019/2026 (CT-09 268 Hg) ===
    ('66120/2026', 794, '7,80',     7.80,   NULL), ('66120/2026', 110, '12,0',  12.0,  NULL), ('66120/2026', 800, '31,0',  31.0,  NULL), ('66120/2026', 268, '<0,200', 0.20, '<'),
    ('67019/2026', 259, '0,01',     0.01,   NULL),
    ('67019/2026', 794, '9,72',     9.72,   NULL),
    ('67019/2026', 92,  '397,11',   397.11, NULL),
    ('67019/2026', 93,  '778',      778.0,  NULL),
    ('67019/2026', 119, '0,7',      0.7,    NULL),
    ('67019/2026', 111, '111',      111.0,  NULL),
    ('67019/2026', 800, '36',       36.0,   NULL),
    ('67019/2026', 144, '16',       16.0,   NULL),
    ('67019/2026', 145, '>128',     128.0,  '>'),
    ('67019/2026', 257, '<0,001',   0.001,  '<'),
    ('67019/2026', 268, '<0,200',   0.200,  '<'), -- RN-05: ug/L vs mg/L -> PENDENTE
    ('67019/2026', 270, '<0,01',    0.01,   '<'),
    ('67019/2026', 282, '0,16',     0.16,   NULL),
    ('67019/2026', 110, '27',       27.0,   NULL),
    ('67019/2026', 196, '<0,010',   0.010,  '<'),

    -- === SAMAE Captação Rio Itajaí-Açu: 5 anteriores com <LQ (CT-14) + Amostra REAL 65462/2026 (CT-06) ===
    ('60110/2026', 19, '<2,00', 2.0, '<'), ('60110/2026', 791, '7,40', 7.40, NULL), ('60110/2026', 793, '7,10', 7.10, NULL), ('60110/2026', 780, '<0,01', 0.01, '<'),
    ('61190/2026', 19, '1,80',  1.8, NULL),('61190/2026', 791, '7,20', 7.20, NULL), ('61190/2026', 793, '7,05', 7.05, NULL), ('61190/2026', 780, '<0,01', 0.01, '<'),
    ('62100/2026', 19, '<2,00', 2.0, '<'), ('62100/2026', 791, '6,90', 6.90, NULL), ('62100/2026', 793, '6,95', 6.95, NULL), ('62100/2026', 780, '<0,01', 0.01, '<'),
    ('63105/2026', 19, '2,40',  2.4, NULL),('63105/2026', 791, '6,60', 6.60, NULL), ('63105/2026', 793, '6,88', 6.88, NULL), ('63105/2026', 780, '<0,01', 0.01, '<'),
    ('64112/2026', 19, '2,90',  2.9, NULL),('64112/2026', 791, '6,10', 6.10, NULL), ('64112/2026', 793, '6,82', 6.82, NULL), ('64112/2026', 780, '<0,01', 0.01, '<'),

    ('65462/2026', 19,  '<5,00', 5.0,  '<'),  -- Cl.1 (<=3) PENDENTE | Cl.2 (<=5) CONFORME
    ('65462/2026', 33,  '3',     3.0,  NULL), -- sem VMP na 357 (salvo para historico)
    ('65462/2026', 62,  '17,5',  17.5, NULL),
    ('65462/2026', 791, '2,02',  2.02, NULL), -- Cl.1 (>=6) e Cl.2 (>=5) -> NAO CONFORME
    ('65462/2026', 793, '6,73',  6.73, NULL),
    ('65462/2026', 780, '<0,10', 0.10, '<'),  -- Cl.1/2 (<=0,01) -> PENDENTE

    -- === SAMAE Montante ETA Central: Reais 64283/2026 (CT-04) e 65335/2026 (CT-06 metais) ===
    ('64283/2026', 33,    '<0,20', 0.20, '<'),
    ('64283/2026', 28,    '0,05',  0.05, NULL),
    ('64283/2026', 59,    '270',   270.0, NULL), -- Cl.1 (<=200) NC | Cl.2 (<=1000) C | Cl.3 (<=4000) C
    ('64283/2026', 48,    '2,01',  2.01, NULL),
    ('64283/2026', 791,   '9,31',  9.31, NULL),
    ('64283/2026', 793,   '6,38',  6.38, NULL),
    ('64283/2026', 31,    '0,4',   0.4,  NULL),
    ('64283/2026', 32,    '<0,10', 0.10, '<'),
    ('64283/2026', 52,    '<10',   10.0, '<'),
    ('64283/2026', 15915, '<2,00', 2.0,  '<'),

    ('65335/2026', 157, '<0,01',  0.01,  '<'), -- Cl.1/2 (<=0,009) PENDENTE | Cl.3 (<=0,013) CONFORME
    ('65335/2026', 163, '<0,01',  0.01,  '<'),
    ('65335/2026', 249, '<0,01',  0.01,  '<'),
    ('65335/2026', 224, '<0,001', 0.001, '<'),
    ('65335/2026', 226, '<0,01',  0.01,  '<'),
    ('65335/2026', 229, '<0,01',  0.01,  '<'),

    -- === Cervejaria Potabilidade: CT-01 (100% Conforme) e CT-02 (Conflito 877 GM888 vs SES1468) ===
    ('4765/2026', 48,  '0,45',    0.45,   NULL),
    ('4765/2026', 793, '7,30',    7.30,   NULL),
    ('4765/2026', 877, '<5,0',    5.0,    '<'),
    ('4765/2026', 235, '<0,0002', 0.0002, '<'),

    ('4766/2026', 48,  '1,20',    1.20,   NULL),
    ('4766/2026', 793, '7,45',    7.45,   NULL),
    ('4766/2026', 877, '42,0',    42.0,   NULL), -- GM888 (<=500) C | SES1468 (<=30) NC!
    ('4766/2026', 235, '<0,0002', 0.0002, '<'),

    -- === Águas de Blumenau — Filtro 03: 10 coletas (CT-15 janela 6m/teto 6 + CT-07 >LS) ===
    ('50101/2025', 48, '4,80', 4.80, NULL), ('50101/2025', 793, '7,10', 7.10, NULL), -- >6m (valor alto proposital p/ provar exclusao!)
    ('51102/2025', 48, '4,50', 4.50, NULL), ('51102/2025', 793, '7,15', 7.15, NULL), -- >6m
    ('52103/2026', 48, '3,90', 3.90, NULL), ('52103/2026', 793, '7,20', 7.20, NULL), -- #7 dentro 6m (fora teto 6)
    ('53104/2026', 48, '1,10', 1.10, NULL), ('53104/2026', 793, '7,22', 7.22, NULL),
    ('54105/2026', 48, '1,25', 1.25, NULL), ('54105/2026', 793, '7,24', 7.24, NULL),
    ('55106/2026', 48, '1,15', 1.15, NULL), ('55106/2026', 793, '7,21', 7.21, NULL),
    ('56107/2026', 48, '1,30', 1.30, NULL), ('56107/2026', 793, '7,26', 7.26, NULL),
    ('57108/2026', 48, '1,20', 1.20, NULL), ('57108/2026', 793, '7,25', 7.25, NULL),
    ('58109/2026', 48, '1,28', 1.28, NULL), ('58109/2026', 793, '7,23', 7.23, NULL),
    ('68010/2026', 48, '>5,0', 5.00, '>'),  ('68010/2026', 793, '7,24', 7.24, NULL)  -- CT-07: >5,0 vs <=5 -> NAO CONFORME
) AS v(cod_amostra, id_num, bruto, num, qual)
JOIN amostra a ON a.codigo_amostra = v.cod_amostra
JOIN ensaios e ON e.id_num = v.id_num
ON CONFLICT (fk_amostra, fk_ensaios) DO NOTHING;

-- ------------------------------------------------------------
-- 9. Avaliações de Conformidade (analise_conformidade) — Calculadas pela Regra Oficial (RN-03..RN-06)
-- ------------------------------------------------------------
WITH amostra_normas_seed(cod_amostra, leg_nome, classe_nome) AS (
    VALUES
        -- ETE 01: CONAMA 430 (Sanitário + Sem Classe)
        ('58110/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('58110/2026', 'Resolução CONAMA 430/2011', NULL),
        ('59201/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('59201/2026', 'Resolução CONAMA 430/2011', NULL),
        ('60144/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('60144/2026', 'Resolução CONAMA 430/2011', NULL),
        ('61210/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('61210/2026', 'Resolução CONAMA 430/2011', NULL),
        ('62308/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('62308/2026', 'Resolução CONAMA 430/2011', NULL),
        ('63450/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('63450/2026', 'Resolução CONAMA 430/2011', NULL),

        -- ETE Linha B: CONAMA 430 (Sanitário + Sem Classe)
        ('63413/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('63413/2026', 'Resolução CONAMA 430/2011', NULL),
        ('68001/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('68001/2026', 'Resolução CONAMA 430/2011', NULL),
        ('68002/2026', 'Resolução CONAMA 430/2011', 'Sanitário'), ('68002/2026', 'Resolução CONAMA 430/2011', NULL),

        -- Têxtil Garcia Industrial 02: CONAMA 430 Sem Classe (Art. 16)
        ('66120/2026', 'Resolução CONAMA 430/2011', NULL),
        ('67019/2026', 'Resolução CONAMA 430/2011', NULL),

        -- SAMAE Captação Rio Itajaí-Açu: CONAMA 357 Classe 1 + Classe 2
        ('60110/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('60110/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('61190/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('61190/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('62100/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('62100/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('63105/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('63105/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('64112/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('64112/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('65462/2026', 'Resolução CONAMA 357/2005', 'Classe 1'), ('65462/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),

        -- SAMAE Montante ETA Central: CONAMA 357 Classes 1, 2 e 3 (3 normas simultâneas!)
        ('64283/2026', 'Resolução CONAMA 357/2005', 'Classe 1'),
        ('64283/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('64283/2026', 'Resolução CONAMA 357/2005', 'Classe 3'),
        ('65335/2026', 'Resolução CONAMA 357/2005', 'Classe 1'),
        ('65335/2026', 'Resolução CONAMA 357/2005', 'Classe 2'),
        ('65335/2026', 'Resolução CONAMA 357/2005', 'Classe 3'),

        -- Potabilidade: GM/MS 888 + SES/SC 1468
        ('4765/2026',  'Portaria GM/MS 888/2021', NULL), ('4765/2026',  'Portaria SES/SC 1468/2022', NULL),
        ('4766/2026',  'Portaria GM/MS 888/2021', NULL), ('4766/2026',  'Portaria SES/SC 1468/2022', NULL),
        ('50101/2025', 'Portaria GM/MS 888/2021', NULL), ('50101/2025', 'Portaria SES/SC 1468/2022', NULL),
        ('51102/2025', 'Portaria GM/MS 888/2021', NULL), ('51102/2025', 'Portaria SES/SC 1468/2022', NULL),
        ('52103/2026', 'Portaria GM/MS 888/2021', NULL), ('52103/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('53104/2026', 'Portaria GM/MS 888/2021', NULL), ('53104/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('54105/2026', 'Portaria GM/MS 888/2021', NULL), ('54105/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('55106/2026', 'Portaria GM/MS 888/2021', NULL), ('55106/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('56107/2026', 'Portaria GM/MS 888/2021', NULL), ('56107/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('57108/2026', 'Portaria GM/MS 888/2021', NULL), ('57108/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('58109/2026', 'Portaria GM/MS 888/2021', NULL), ('58109/2026', 'Portaria SES/SC 1468/2022', NULL),
        ('68010/2026', 'Portaria GM/MS 888/2021', NULL), ('68010/2026', 'Portaria SES/SC 1468/2022', NULL)
),
base_eval AS (
    SELECT
        ra.id AS fk_resultado_amostra,
        p.id  AS fk_parametros,
        e.tipo_avaliacao,
        e.fk_unidade_medida AS unid_ensaio,
        p.fk_unidade_medida AS unid_param,
        p.operador,
        p.valor_min,
        p.valor_max,
        p.valor_esperado,
        ra.valor_bruto,
        ra.qualificador,
        COALESCE(
            ra.valor_numerico,
            CASE WHEN LOWER(TRIM(ra.valor_bruto)) = 'ausente' THEN 0.0 ELSE NULL END
        ) AS v_efetivo,
        a.codigo_amostra,
        e.id_num
    FROM amostra_normas_seed ans
    JOIN amostra a            ON a.codigo_amostra = ans.cod_amostra
    JOIN legislacao l         ON l.nome = ans.leg_nome
    JOIN legislacao_origem lo ON lo.fk_legislacao = l.id AND lo.fk_origem_amostra = a.fk_origem_amostra
    LEFT JOIN classe c        ON c.fk_legislacao_origem = lo.id AND c.nome = ans.classe_nome
    JOIN resultado_amostra ra ON ra.fk_amostra = a.id
    JOIN ensaios e            ON e.id = ra.fk_ensaios
    JOIN parametros p         ON p.fk_legislacao_origem = lo.id
                             AND p.fk_classe IS NOT DISTINCT FROM c.id
                             AND p.fk_ensaios = e.id
    WHERE ans.classe_nome IS NULL OR c.id IS NOT NULL
)
INSERT INTO analise_conformidade (fk_resultado_amostra, fk_parametros, conformidade, observacao)
SELECT
    fk_resultado_amostra,
    fk_parametros,
    CASE
        WHEN tipo_avaliacao = 'MANUAL_TECNICA' THEN NULL
        WHEN operador <> 'AUSENCIA' AND unid_ensaio IS DISTINCT FROM unid_param THEN NULL
        WHEN operador = 'AUSENCIA' THEN
            LOWER(TRIM(valor_bruto)) = LOWER(TRIM(COALESCE(valor_esperado, 'Ausente')))
        WHEN v_efetivo IS NULL THEN NULL
        WHEN operador = 'MENOR_IGUAL' THEN
            CASE
                WHEN qualificador = '<' THEN (CASE WHEN v_efetivo <= valor_max THEN TRUE  ELSE NULL END)
                WHEN qualificador = '>' THEN (CASE WHEN v_efetivo >= valor_max THEN FALSE ELSE NULL END)
                ELSE (v_efetivo <= valor_max)
            END
        WHEN operador = 'MENOR_ESTRITO' THEN
            CASE
                WHEN qualificador = '<' THEN (CASE WHEN v_efetivo <= valor_max THEN TRUE  ELSE NULL END)
                WHEN qualificador = '>' THEN (CASE WHEN v_efetivo >= valor_max THEN FALSE ELSE NULL END)
                ELSE (v_efetivo < valor_max)
            END
        WHEN operador = 'MAIOR_IGUAL' THEN
            CASE
                WHEN qualificador = '>' THEN (CASE WHEN v_efetivo >= valor_min THEN TRUE  ELSE NULL END)
                WHEN qualificador = '<' THEN (CASE WHEN v_efetivo <= valor_min THEN FALSE ELSE NULL END)
                ELSE (v_efetivo >= valor_min)
            END
        WHEN operador = 'FAIXA' THEN
            CASE
                WHEN qualificador = '<' THEN (CASE WHEN v_efetivo <= valor_min THEN FALSE ELSE NULL END)
                WHEN qualificador = '>' THEN (CASE WHEN v_efetivo >= valor_max THEN FALSE ELSE NULL END)
                ELSE (v_efetivo >= valor_min AND v_efetivo <= valor_max)
            END
        ELSE NULL
    END AS conformidade,
    CASE
        WHEN codigo_amostra = '63450/2026' AND id_num = 106 THEN 'Em análise — acima do histórico e do Art. 16'
        WHEN codigo_amostra = '67019/2026' AND id_num = 268 THEN 'Revisar unidade (µg/L vs mg/L)'
        ELSE NULL
    END AS observacao
FROM base_eval
ON CONFLICT (fk_resultado_amostra, fk_parametros) DO NOTHING;

-- ------------------------------------------------------------
-- 10. Derivação Automática de amostra.status (100% derivado — RN-07) e amostra.descricao
-- ------------------------------------------------------------
UPDATE amostra a
SET
    status = agg.status_derivado,
    descricao = CASE
        WHEN agg.status_derivado IS TRUE THEN
            'Os resultados de ensaio atendem às especificações aplicadas neste documento.'
        WHEN agg.status_derivado IS FALSE THEN
            'Os ensaios atendem às especificações aplicadas neste documento, exceto ' || agg.texto_excecoes || '.'
        ELSE
            'Análise em conferência técnica. Os resultados avaliados atendem às especificações aplicadas, restando pendência de verificação em: ' || agg.texto_pendentes || '.'
    END
FROM (
    SELECT
        ra.fk_amostra,
        CASE
            WHEN BOOL_OR(ac.conformidade IS FALSE) THEN FALSE
            WHEN BOOL_OR(ac.conformidade IS NULL)  THEN NULL
            ELSE TRUE
        END AS status_derivado,
        STRING_AGG(
            DISTINCT ('o ensaio de ' || e.descricao || ' para a ' || l.nome || COALESCE(' (' || c.nome || ')', '')),
            ', '
        ) FILTER (WHERE ac.conformidade IS FALSE) AS texto_excecoes,
        STRING_AGG(DISTINCT e.descricao, ', ') FILTER (WHERE ac.conformidade IS NULL) AS texto_pendentes
    FROM resultado_amostra ra
    JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
    JOIN ensaios e               ON e.id = ra.fk_ensaios
    JOIN parametros p            ON p.id = ac.fk_parametros
    JOIN legislacao_origem lo    ON lo.id = p.fk_legislacao_origem
    JOIN legislacao l            ON l.id = lo.fk_legislacao
    LEFT JOIN classe c           ON c.id = p.fk_classe
    GROUP BY ra.fk_amostra
) agg
WHERE a.id = agg.fk_amostra
  AND a.descricao IS NULL;

-- ------------------------------------------------------------
-- 11. Registros iniciais de auditoria em log_alteracao (RN-10 / CT-16)
-- ------------------------------------------------------------
INSERT INTO log_alteracao (
    id, fk_amostra, fk_resultado_amostra, fk_usuario,
    campo_alterado, valor_anterior, valor_novo, observacao, data_alteracao
)
SELECT
    'cccc0001-0000-4000-8000-000000000001'::uuid,
    a.id,
    ra.id,
    'aaaa0001-0000-4000-8000-000000000001'::uuid,
    'conformidade',
    'Não conforme',
    'Não conforme',
    'Registrada observação técnica sobre elevação de Nitrogênio Amoniacal (71 mg/L) frente ao histórico do ponto.',
    TIMESTAMP '2026-07-28 14:35:00'
FROM amostra a
JOIN resultado_amostra ra ON ra.fk_amostra = a.id
JOIN ensaios e            ON e.id = ra.fk_ensaios
WHERE a.codigo_amostra = '63450/2026' AND e.id_num = 106
ON CONFLICT (id) DO NOTHING;

INSERT INTO log_alteracao (
    id, fk_amostra, fk_resultado_amostra, fk_usuario,
    campo_alterado, valor_anterior, valor_novo, observacao, data_alteracao
)
SELECT
    'cccc0002-0000-4000-8000-000000000002'::uuid,
    a.id,
    NULL,
    'aaaa0001-0000-4000-8000-000000000001'::uuid,
    'minuta',
    'Minuta inicial automática',
    a.descricao,
    'Conferência técnica revisada para liberação no PRL.',
    TIMESTAMP '2026-07-28 14:40:00'
FROM amostra a
WHERE a.codigo_amostra = '63450/2026'
ON CONFLICT (id) DO NOTHING;

COMMIT;
