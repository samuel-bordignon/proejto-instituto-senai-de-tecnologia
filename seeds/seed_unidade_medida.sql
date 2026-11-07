-- ============================================================
-- LaudoTech — DEV-4: Carga de unidade_medida (unidades normalizadas)
-- ============================================================
-- Regras aplicadas sobre as planilhas de staging:
--   1. 'ug/L' e 'ppb'          -> unificados em 'µg/L' (1 ppb = 1 µg/L)
--   2. 'NMP/100 mL'            -> padronizado sem espaço em 'NMP/100mL'
--   3. Ensaio 7138 ('SUB - Gosto e Odor', sem unidade no PDF) -> vinculado a 'Intensidade' na DEV-6
--   4. '' (grandezas adimensionais: pH [793, 1190] e Razão de Nitrito e Nitrato [7865]) -> fk_unidade_medida = NULL na DEV-6
--   5. 'Aus/Pres em 100mL'     -> descartado na DEV-2 (não cadastrado)

INSERT INTO unidade_medida (descricao) VALUES
    ('µg/L'),
    ('mg/L'),
    ('Bq/L'),
    ('UFC/100mL'),
    ('NMP/100mL'),
    ('NTU'),
    ('Pt/Co'),
    ('Intensidade'),
    ('células/mL')
ON CONFLICT (descricao) DO NOTHING;
