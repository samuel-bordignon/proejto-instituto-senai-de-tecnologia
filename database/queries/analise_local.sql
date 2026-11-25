-- ============================================================
-- Domínio: Análise Histórica por Local de Coleta — Tela B5 (/analise) (RF-06)
-- ============================================================

-- name: listar_normas_avaliadas_no_local
SELECT DISTINCT
    l.nome AS legislacao_nome,
    c.nome AS classe_nome,
    EXISTS (
        SELECT 1 FROM classe c2 WHERE c2.fk_legislacao_origem = lo.id
    ) AS possui_classes
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
JOIN resultado_amostra ra ON ra.fk_amostra = a.id
JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
JOIN parametros p ON p.id = ac.fk_parametros
JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
JOIN legislacao l ON l.id = lo.fk_legislacao
LEFT JOIN classe c ON c.id = p.fk_classe
WHERE lc.nome_identificacao = %s
ORDER BY l.nome ASC, c.nome ASC NULLS LAST;

-- name: buscar_data_referencia_local
SELECT COALESCE(MAX(a.data_coleta), CURRENT_DATE) AS data_ref
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
WHERE lc.nome_identificacao = %s;

-- name: listar_evolucao_amostras_local
SELECT
    a.id::text AS amostra_id,
    a.codigo_amostra,
    a.data_coleta,
    CASE
        WHEN COUNT(ac.fk_parametros) = 0 THEN a.status
        WHEN BOOL_OR(ac.conformidade IS FALSE) THEN FALSE
        WHEN BOOL_OR(ac.conformidade IS NULL)  THEN NULL
        ELSE TRUE
    END AS status_na_norma
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
LEFT JOIN resultado_amostra ra ON ra.fk_amostra = a.id
LEFT JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
LEFT JOIN parametros p ON p.id = ac.fk_parametros
LEFT JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
LEFT JOIN legislacao l ON l.id = lo.fk_legislacao
LEFT JOIN classe c ON c.id = p.fk_classe
WHERE lc.nome_identificacao = %s
  AND a.data_coleta >= (%s::date - make_interval(months => %s))::date
  AND (
      ac.fk_parametros IS NULL
      OR (l.nome = %s AND c.nome IS NOT DISTINCT FROM %s)
  )
GROUP BY a.id, a.codigo_amostra, a.data_coleta, a.status
HAVING COUNT(ac.fk_parametros) FILTER (WHERE l.nome = %s AND c.nome IS NOT DISTINCT FROM %s) > 0
ORDER BY a.data_coleta ASC, a.codigo_amostra ASC;

-- name: listar_resultados_local_por_norma
SELECT
    e.id_num,
    e.descricao AS ensaio_nome,
    COALESCE(e.tipo_avaliacao, 'AUTOMATICA') AS tipo_avaliacao,
    COALESCE(ue.descricao, '') AS unidade_ensaio,
    a.codigo_amostra,
    a.data_coleta,
    ra.valor_bruto,
    ra.valor_numerico,
    ra.qualificador,
    p.operador,
    p.valor_min,
    p.valor_max,
    p.valor_esperado,
    COALESCE(up.descricao, '') AS unidade_parametro,
    ac.conformidade
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
JOIN resultado_amostra ra ON ra.fk_amostra = a.id
JOIN ensaios e ON e.id = ra.fk_ensaios
LEFT JOIN unidade_medida ue ON ue.id = e.fk_unidade_medida
JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
JOIN parametros p ON p.id = ac.fk_parametros
LEFT JOIN unidade_medida up ON up.id = p.fk_unidade_medida
JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
JOIN legislacao l ON l.id = lo.fk_legislacao
LEFT JOIN classe c ON c.id = p.fk_classe
WHERE lc.nome_identificacao = %s
  AND a.data_coleta >= (%s::date - make_interval(months => %s))::date
  AND l.nome = %s
  AND c.nome IS NOT DISTINCT FROM %s
ORDER BY e.id_num ASC, a.data_coleta DESC, a.codigo_amostra DESC;
