-- ============================================================
-- LaudoTech — DEV-7 / DEV-10: Validação de Integridade da Base Legal (v2.2)
-- Cobre Portarias (GM/MS 888, SES/SC 1468) + Resoluções (CONAMA 430, CONAMA 357)
-- ============================================================

-- 1. Ensaios sem parâmetro vinculado: permitidos APENAS os 8 informativos do Slide 10
--    (93, 101, 104, 105, 132, 135, 144, 145) e os 2 condicionais CONAMA 357 (28, 33).
--    Resultado obrigatório: 0 ensaios órfãos inesperados.
SELECT COUNT(*) AS ensaios_orfaos_inesperados
FROM ensaios e
LEFT JOIN parametros p ON p.fk_ensaios = e.id
WHERE p.id IS NULL
  AND e.id_num NOT IN (28, 33, 93, 101, 104, 105, 132, 135, 144, 145);

-- 2. Tipo de avaliação válido em 100% dos ensaios (Resultado obrigatório: 0)
SELECT COUNT(*) AS ensaios_tipo_invalido
FROM ensaios
WHERE tipo_avaliacao NOT IN ('AUTOMATICA', 'MANUAL_TECNICA')
   OR tipo_avaliacao IS NULL;

-- 3. Integridade de operadores e limites em parametros (Resultado obrigatório: 0)
SELECT COUNT(*) AS parametros_invalidos
FROM parametros
WHERE operador NOT IN ('MENOR_IGUAL', 'MENOR_ESTRITO', 'MAIOR_IGUAL', 'FAIXA', 'AUSENCIA')
   OR (operador IN ('MENOR_IGUAL', 'MENOR_ESTRITO') AND (valor_max IS NULL OR valor_min IS NOT NULL))
   OR (operador = 'MAIOR_IGUAL' AND (valor_min IS NULL OR valor_max IS NOT NULL))
   OR (operador = 'FAIXA' AND (valor_min IS NULL OR valor_max IS NULL OR valor_min >= valor_max))
   OR (operador = 'AUSENCIA' AND (valor_esperado IS NULL OR TRIM(valor_esperado) = ''));

-- 4. Zero duplicatas de (fk_legislacao_origem, fk_classe, fk_ensaios) considerando NULL igual a NULL
--    Resultado obrigatório: 0 linhas retornadas.
SELECT fk_legislacao_origem, fk_classe, fk_ensaios, COUNT(*) AS qtd
FROM parametros
GROUP BY fk_legislacao_origem, fk_classe, fk_ensaios
HAVING COUNT(*) > 1;

-- 5. Zero ensaios físicos sem fk_unidade_medida preenchida
--    (Apenas os 6 adimensionais/qualitativos 793, 1190, 7865, 794, 1189, 784 podem ter NULL)
--    Resultado obrigatório: 0.
SELECT COUNT(*) AS ensaios_fisicos_sem_unidade
FROM ensaios
WHERE fk_unidade_medida IS NULL
  AND id_num NOT IN (793, 1190, 7865, 794, 1189, 784);

-- 6. Conferência dos casos educativos de divergência de unidade (RN-05)
--    (268, 672, 382 e 690/691 em GM888 ACH)
SELECT
    e.id_num,
    e.descricao AS ensaio,
    l.nome AS legislacao,
    COALESCE(c.nome, 'Sem Classe') AS classe,
    COALESCE(ue.descricao, 'NULL') AS unid_ensaio,
    COALESCE(up.descricao, 'NULL') AS unid_parametro
FROM parametros p
JOIN ensaios e             ON e.id = p.fk_ensaios
JOIN legislacao_origem lo  ON lo.id = p.fk_legislacao_origem
JOIN legislacao l          ON l.id = lo.fk_legislacao
LEFT JOIN classe c         ON c.id = p.fk_classe
LEFT JOIN unidade_medida ue ON ue.id = e.fk_unidade_medida
LEFT JOIN unidade_medida up ON up.id = p.fk_unidade_medida
WHERE e.fk_unidade_medida IS DISTINCT FROM p.fk_unidade_medida
ORDER BY e.id_num, l.nome, classe;

-- 7. Resumo final de contagens da Base Legal
--    Esperado: 4 legislações, 5 origens, 8 legislacao_origem, 4 classes,
--              12 unidades, 340 ensaios, 820 parâmetros.
SELECT
    (SELECT COUNT(*) FROM legislacao)        AS total_legislacoes,
    (SELECT COUNT(*) FROM origem_amostra)    AS total_origens_amostra,
    (SELECT COUNT(*) FROM legislacao_origem) AS total_legislacao_origem,
    (SELECT COUNT(*) FROM classe)            AS total_classes,
    (SELECT COUNT(*) FROM unidade_medida)    AS total_unidades_medida,
    (SELECT COUNT(*) FROM ensaios)           AS total_ensaios,
    (SELECT COUNT(*) FROM parametros)        AS total_parametros;
