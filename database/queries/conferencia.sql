-- ============================================================
-- Domínio: Conferência Técnica e Trilha de Auditoria RN-10 (RF-05 / CT-16)
-- ============================================================

-- name: inserir_analise_conformidade
INSERT INTO analise_conformidade (
    fk_resultado_amostra,
    fk_parametros,
    conformidade,
    observacao
)
VALUES (%s::uuid, %s::uuid, %s, %s)
ON CONFLICT (fk_resultado_amostra, fk_parametros)
DO UPDATE SET
    conformidade = EXCLUDED.conformidade,
    observacao   = EXCLUDED.observacao;

-- name: atualizar_observacao_ensaio
UPDATE analise_conformidade ac
SET observacao = %s
FROM resultado_amostra ra
JOIN ensaios e ON e.id = ra.fk_ensaios
WHERE ac.fk_resultado_amostra = ra.id
  AND ra.fk_amostra = %s::uuid
  AND e.id_num = %s;

-- name: atualizar_conformidade_e_observacao_ensaio
UPDATE analise_conformidade ac
SET
    conformidade = %s,
    observacao   = %s
FROM resultado_amostra ra
JOIN ensaios e ON e.id = ra.fk_ensaios
WHERE ac.fk_resultado_amostra = ra.id
  AND ra.fk_amostra = %s::uuid
  AND e.id_num = %s;

-- name: buscar_resultado_amostra_por_ensaio
SELECT
    ra.id::text AS resultado_id
FROM resultado_amostra ra
JOIN ensaios e ON e.id = ra.fk_ensaios
WHERE ra.fk_amostra = %s::uuid
  AND e.id_num = %s
LIMIT 1;

-- name: atualizar_conclusao_amostra
UPDATE amostra
SET
    status    = %s,
    descricao = %s
WHERE id = %s::uuid;

-- name: inserir_log_alteracao
INSERT INTO log_alteracao (
    fk_amostra,
    fk_resultado_amostra,
    fk_usuario,
    campo_alterado,
    valor_anterior,
    valor_novo,
    observacao,
    data_alteracao
)
VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s)
RETURNING id::text AS id;

-- name: listar_logs_por_amostra
SELECT
    la.id::text AS id,
    la.data_alteracao,
    u.nome_usuario AS usuario,
    la.campo_alterado,
    e.id_num AS ensaio_codigo,
    e.descricao AS ensaio_nome,
    COALESCE(la.valor_anterior, '') AS valor_anterior,
    la.valor_novo,
    la.observacao
FROM log_alteracao la
JOIN usuario u ON u.id = la.fk_usuario
LEFT JOIN resultado_amostra ra ON ra.id = la.fk_resultado_amostra
LEFT JOIN ensaios e ON e.id = ra.fk_ensaios
WHERE la.fk_amostra = %s::uuid
ORDER BY la.data_alteracao DESC, la.id DESC;
