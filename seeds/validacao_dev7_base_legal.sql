-- ============================================================
-- LaudoTech — DEV-7: Validação de Integridade da Carga Base Legal
-- ============================================================

-- 1. Zero ensaios sem parâmetro vinculado (Resultado obrigatório: 0)
SELECT COUNT(*) AS ensaios_orfaos
FROM ensaios e
LEFT JOIN parametros p ON p.fk_ensaios = e.id
WHERE p.id IS NULL;

-- 2. Zero ensaios fora do modo automático (Resultado obrigatório: 0)
SELECT COUNT(*) AS ensaios_nao_automaticos
FROM ensaios
WHERE tipo_avaliacao <> 'AUTOMATICA' OR tipo_avaliacao IS NULL;

-- 3. Zero parâmetros sem limites (NULL/NULL) ou com operador fora dos numéricos (Resultado obrigatório: 0)
SELECT COUNT(*) AS parametros_invalidos
FROM parametros
WHERE (valor_min IS NULL AND valor_max IS NULL)
   OR operador NOT IN ('MENOR_IGUAL', 'MAIOR_IGUAL', 'FAIXA');

-- 4. Zero duplicatas de (fk_legislacao_origem, fk_ensaios) em parametros (Resultado obrigatório: 0 linhas)
SELECT fk_legislacao_origem, fk_ensaios, COUNT(*) AS qtd
FROM parametros
GROUP BY fk_legislacao_origem, fk_ensaios
HAVING COUNT(*) > 1;

-- 5. Resumo final de contagens da Base Legal
SELECT
    (SELECT COUNT(*) FROM legislacao)        AS total_legislacoes,
    (SELECT COUNT(*) FROM origem_amostra)    AS total_origens_amostra,
    (SELECT COUNT(*) FROM legislacao_origem) AS total_legislacao_origem,
    (SELECT COUNT(*) FROM classe)            AS total_classes,
    (SELECT COUNT(*) FROM unidade_medida)    AS total_unidades_medida,
    (SELECT COUNT(*) FROM ensaios)           AS total_ensaios,
    (SELECT COUNT(*) FROM parametros)        AS total_parametros;
