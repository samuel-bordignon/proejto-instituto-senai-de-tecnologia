-- ============================================================
-- Domínio: Amostras e Resultados LIMS — Leitura Normalizada e Persistência (RF-03 / RF-04 / RNF-06)
-- Cliente e Proposta resolvidos por JOIN lateral priorizando vigência em data_coleta
-- ============================================================

-- name: listar_codigos_amostras
SELECT codigo_amostra
FROM amostra
WHERE codigo_amostra IS NOT NULL;

-- name: listar_amostras_base
SELECT
    a.id::text AS amostra_id,
    a.codigo_amostra,
    a.codigo_amostra_externo,
    a.data_coleta,
    a.data_conclusao,
    a.status,
    COALESCE(a.descricao, '') AS descricao,
    lc.id::text AS local_id,
    lc.nome_identificacao AS local_nome,
    o.id::text AS origem_id,
    o.nome AS origem_nome,
    ctx.proposta_id,
    COALESCE(ctx.cliente_nome, 'Cliente não vinculado') AS cliente_nome
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
JOIN origem_amostra o ON o.id = a.fk_origem_amostra
LEFT JOIN LATERAL (
    SELECT
        pc.id::text AS proposta_id,
        c.razao_social AS cliente_nome
    FROM local_proposta lp
    JOIN proposta_comercial pc ON pc.id = lp.fk_proposta_comercial
    JOIN cliente c ON c.id = pc.fk_cliente
    WHERE lp.fk_local_coleta = a.fk_local_coleta
    ORDER BY
        (
            a.data_coleta IS NOT NULL
            AND pc.data_inicio IS NOT NULL
            AND pc.data_fim IS NOT NULL
            AND a.data_coleta BETWEEN pc.data_inicio AND pc.data_fim
        ) DESC,
        COALESCE(pc.status, TRUE) DESC,
        pc.data_inicio DESC NULLS LAST,
        pc.id ASC
    LIMIT 1
) ctx ON TRUE
ORDER BY a.data_coleta DESC NULLS LAST, a.codigo_amostra DESC;

-- name: buscar_amostra_base_por_codigo
SELECT
    a.id::text AS amostra_id,
    a.codigo_amostra,
    a.codigo_amostra_externo,
    a.data_coleta,
    a.data_conclusao,
    a.status,
    COALESCE(a.descricao, '') AS descricao,
    lc.id::text AS local_id,
    lc.nome_identificacao AS local_nome,
    o.id::text AS origem_id,
    o.nome AS origem_nome,
    ctx.proposta_id,
    COALESCE(ctx.cliente_nome, 'Cliente não vinculado') AS cliente_nome
FROM amostra a
JOIN local_coleta lc ON lc.id = a.fk_local_coleta
JOIN origem_amostra o ON o.id = a.fk_origem_amostra
LEFT JOIN LATERAL (
    SELECT
        pc.id::text AS proposta_id,
        c.razao_social AS cliente_nome
    FROM local_proposta lp
    JOIN proposta_comercial pc ON pc.id = lp.fk_proposta_comercial
    JOIN cliente c ON c.id = pc.fk_cliente
    WHERE lp.fk_local_coleta = a.fk_local_coleta
    ORDER BY
        (
            a.data_coleta IS NOT NULL
            AND pc.data_inicio IS NOT NULL
            AND pc.data_fim IS NOT NULL
            AND a.data_coleta BETWEEN pc.data_inicio AND pc.data_fim
        ) DESC,
        COALESCE(pc.status, TRUE) DESC,
        pc.data_inicio DESC NULLS LAST,
        pc.id ASC
    LIMIT 1
) ctx ON TRUE
WHERE a.codigo_amostra = %s
LIMIT 1;

-- name: listar_resultados_e_avaliacoes_todas
SELECT
    ra.id::text AS resultado_id,
    ra.fk_amostra::text AS amostra_id,
    a.codigo_amostra,
    a.fk_local_coleta::text AS local_id,
    a.data_coleta,
    e.id::text AS ensaio_id,
    e.id_num,
    e.descricao AS ensaio_nome,
    COALESCE(e.tipo_avaliacao, 'AUTOMATICA') AS tipo_avaliacao,
    COALESCE(ue.descricao, '') AS unidade_ensaio,
    ra.valor_bruto,
    ra.valor_numerico,
    ra.qualificador,
    p.id::text AS parametro_id,
    l.nome AS legislacao_nome,
    o.nome AS origem_parametro,
    c.nome AS classe_nome,
    p.operador,
    p.valor_min,
    p.valor_max,
    p.valor_esperado,
    COALESCE(up.descricao, '') AS unidade_parametro,
    ac.conformidade,
    COALESCE(ac.observacao, '') AS observacao
FROM resultado_amostra ra
JOIN amostra a ON a.id = ra.fk_amostra
JOIN ensaios e ON e.id = ra.fk_ensaios
LEFT JOIN unidade_medida ue ON ue.id = e.fk_unidade_medida
LEFT JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
LEFT JOIN parametros p ON p.id = ac.fk_parametros
LEFT JOIN unidade_medida up ON up.id = p.fk_unidade_medida
LEFT JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
LEFT JOIN legislacao l ON l.id = lo.fk_legislacao
LEFT JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
LEFT JOIN classe c ON c.id = p.fk_classe
ORDER BY a.data_coleta ASC, a.codigo_amostra ASC, e.id_num ASC, l.nome ASC NULLS LAST, c.nome ASC NULLS LAST;

-- name: listar_resultados_e_avaliacoes_amostra
SELECT
    ra.id::text AS resultado_id,
    ra.fk_amostra::text AS amostra_id,
    a.codigo_amostra,
    a.fk_local_coleta::text AS local_id,
    a.data_coleta,
    e.id::text AS ensaio_id,
    e.id_num,
    e.descricao AS ensaio_nome,
    COALESCE(e.tipo_avaliacao, 'AUTOMATICA') AS tipo_avaliacao,
    COALESCE(ue.descricao, '') AS unidade_ensaio,
    ra.valor_bruto,
    ra.valor_numerico,
    ra.qualificador,
    p.id::text AS parametro_id,
    l.nome AS legislacao_nome,
    o.nome AS origem_parametro,
    c.nome AS classe_nome,
    p.operador,
    p.valor_min,
    p.valor_max,
    p.valor_esperado,
    COALESCE(up.descricao, '') AS unidade_parametro,
    ac.conformidade,
    COALESCE(ac.observacao, '') AS observacao
FROM resultado_amostra ra
JOIN amostra a ON a.id = ra.fk_amostra
JOIN ensaios e ON e.id = ra.fk_ensaios
LEFT JOIN unidade_medida ue ON ue.id = e.fk_unidade_medida
LEFT JOIN analise_conformidade ac ON ac.fk_resultado_amostra = ra.id
LEFT JOIN parametros p ON p.id = ac.fk_parametros
LEFT JOIN unidade_medida up ON up.id = p.fk_unidade_medida
LEFT JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
LEFT JOIN legislacao l ON l.id = lo.fk_legislacao
LEFT JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
LEFT JOIN classe c ON c.id = p.fk_classe
WHERE a.id = %s::uuid
ORDER BY e.id_num ASC, l.nome ASC NULLS LAST, c.nome ASC NULLS LAST;

-- name: listar_serie_historica_local
SELECT
    e.id_num,
    a.codigo_amostra,
    a.data_coleta,
    ra.valor_bruto,
    ra.valor_numerico,
    ra.qualificador
FROM resultado_amostra ra
JOIN amostra a ON a.id = ra.fk_amostra
JOIN ensaios e ON e.id = ra.fk_ensaios
WHERE a.fk_local_coleta = %s::uuid
  AND a.id <> %s::uuid
  AND a.data_coleta < %s::date
  AND a.data_coleta >= (%s::date - make_interval(months => %s))::date
ORDER BY e.id_num ASC, a.data_coleta ASC, a.codigo_amostra ASC;

-- name: inserir_amostra
INSERT INTO amostra (
    codigo_amostra,
    codigo_amostra_externo,
    data_coleta,
    data_conclusao,
    status,
    descricao,
    fk_local_coleta,
    fk_origem_amostra,
    fk_usuario,
    fk_laboratorio
)
VALUES (%s, %s, %s, %s, %s, %s, %s::uuid, %s::uuid, %s::uuid, %s::uuid)
RETURNING id::text AS id;

-- name: inserir_resultado_amostra
INSERT INTO resultado_amostra (
    fk_amostra,
    fk_ensaios,
    valor_bruto,
    valor_numerico,
    qualificador,
    data_analise
)
VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
RETURNING id::text AS id;

-- name: excluir_analises_por_codigo_amostra
DELETE FROM analise_conformidade ac
USING resultado_amostra ra, amostra a
WHERE ac.fk_resultado_amostra = ra.id
  AND ra.fk_amostra = a.id
  AND a.codigo_amostra = %s;

-- name: excluir_resultados_por_codigo_amostra
DELETE FROM resultado_amostra ra
USING amostra a
WHERE ra.fk_amostra = a.id
  AND a.codigo_amostra = %s;

-- name: excluir_amostra_por_codigo
DELETE FROM amostra
WHERE codigo_amostra = %s;
