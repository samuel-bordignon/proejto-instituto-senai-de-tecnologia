-- ============================================================
-- Domínio: Cadastros Base — Clientes, Propostas, Locais e Laboratório (RF-02 / RNF-06)
-- Zero redundância: rótulos de proposta derivados via JOIN com proposta_legislacao
-- ============================================================

-- name: listar_clientes
SELECT
    id::text AS id,
    razao_social,
    cnpj,
    cidade,
    uf,
    contato
FROM cliente
ORDER BY razao_social ASC;

-- name: listar_propostas_com_cliente
SELECT
    pc.id::text AS proposta_id,
    pc.fk_cliente::text AS cliente_id,
    c.razao_social AS cliente_nome,
    pc.data_inicio,
    pc.data_fim,
    COALESCE(pc.status, TRUE) AS status,
    COALESCE(
        STRING_AGG(l.nome, ' + ' ORDER BY l.nome),
        'Sem legislação vinculada'
    ) AS legislacoes_vinculadas
FROM proposta_comercial pc
JOIN cliente c ON c.id = pc.fk_cliente
LEFT JOIN proposta_legislacao pl ON pl.fk_proposta_comercial = pc.id
LEFT JOIN legislacao l ON l.id = pl.fk_legislacao
GROUP BY pc.id, pc.fk_cliente, c.razao_social, pc.data_inicio, pc.data_fim, pc.status
ORDER BY c.razao_social ASC, pc.status DESC, pc.data_inicio DESC, pc.id ASC;

-- name: listar_locais_propostas
SELECT
    lc.id::text AS local_id,
    lc.nome_identificacao AS local_nome,
    pc.id::text AS proposta_id,
    c.id::text AS cliente_id,
    c.razao_social AS cliente_nome
FROM local_proposta lp
JOIN local_coleta lc ON lc.id = lp.fk_local_coleta
JOIN proposta_comercial pc ON pc.id = lp.fk_proposta_comercial
JOIN cliente c ON c.id = pc.fk_cliente
ORDER BY c.razao_social ASC, lc.nome_identificacao ASC;

-- name: listar_proposta_legislacoes
SELECT
    pl.fk_proposta_comercial::text AS proposta_id,
    l.id::text AS legislacao_id,
    l.nome AS legislacao_nome
FROM proposta_legislacao pl
JOIN legislacao l ON l.id = pl.fk_legislacao
ORDER BY pl.fk_proposta_comercial, l.nome ASC;

-- name: buscar_laboratorio_padrao
SELECT
    id::text AS id,
    nome
FROM laboratorio
ORDER BY nome ASC
LIMIT 1;
