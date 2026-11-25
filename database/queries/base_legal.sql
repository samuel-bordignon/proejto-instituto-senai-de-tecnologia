-- ============================================================
-- Domínio: Base Legal — Origens, Legislações, Classes, Ensaios e VMPs (RNF-01 / RN-05 / RN-06)
-- ============================================================

-- name: listar_origens
SELECT
    id::text AS id,
    nome
FROM origem_amostra
ORDER BY nome ASC;

-- name: listar_legislacoes_origens_classes
SELECT
    lo.id::text AS legislacao_origem_id,
    l.id::text AS legislacao_id,
    l.nome AS legislacao_nome,
    o.id::text AS origem_id,
    o.nome AS origem_nome,
    c.id::text AS classe_id,
    c.nome AS classe_nome,
    EXISTS (
        SELECT 1 FROM classe c2 WHERE c2.fk_legislacao_origem = lo.id
    ) AS possui_classes,
    EXISTS (
        SELECT 1 FROM parametros p WHERE p.fk_legislacao_origem = lo.id AND p.fk_classe IS NULL
    ) AS possui_sem_classe
FROM legislacao_origem lo
JOIN legislacao l ON l.id = lo.fk_legislacao
JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
LEFT JOIN classe c ON c.fk_legislacao_origem = lo.id
ORDER BY l.nome ASC, o.nome ASC, c.nome ASC NULLS LAST;

-- name: listar_ensaios
SELECT
    e.id::text AS id,
    e.id_num,
    e.descricao,
    COALESCE(e.tipo_avaliacao, 'AUTOMATICA') AS tipo_avaliacao,
    COALESCE(u.descricao, '') AS unidade
FROM ensaios e
LEFT JOIN unidade_medida u ON u.id = e.fk_unidade_medida
ORDER BY e.id_num ASC;

-- name: listar_parametros_vmp
SELECT
    p.id::text AS parametro_id,
    lo.id::text AS legislacao_origem_id,
    l.id::text AS legislacao_id,
    l.nome AS legislacao_nome,
    o.id::text AS origem_id,
    o.nome AS origem_nome,
    c.id::text AS classe_id,
    c.nome AS classe_nome,
    e.id::text AS ensaio_id,
    e.id_num,
    p.operador,
    p.valor_min,
    p.valor_max,
    p.valor_esperado,
    COALESCE(u.descricao, '') AS unidade
FROM parametros p
JOIN legislacao_origem lo ON lo.id = p.fk_legislacao_origem
JOIN legislacao l ON l.id = lo.fk_legislacao
JOIN origem_amostra o ON o.id = lo.fk_origem_amostra
LEFT JOIN classe c ON c.id = p.fk_classe
JOIN ensaios e ON e.id = p.fk_ensaios
LEFT JOIN unidade_medida u ON u.id = p.fk_unidade_medida
ORDER BY l.nome ASC, o.nome ASC, c.nome ASC NULLS LAST, e.id_num ASC;
