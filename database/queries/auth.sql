-- ============================================================
-- Domínio: Autenticação de Usuários Conferentes (RF-01 / RN-10)
-- ============================================================

-- name: ping_conexao
SELECT current_database() AS db, current_user AS usuario;

-- name: buscar_usuario_por_login
SELECT
    id::text AS id,
    nome_usuario,
    senha_hash
FROM usuario
WHERE LOWER(TRIM(nome_usuario)) = LOWER(TRIM(%s))
LIMIT 1;

-- name: buscar_usuario_por_id_ou_login
SELECT
    id::text AS id,
    nome_usuario,
    senha_hash
FROM usuario
WHERE id::text = TRIM(%s)
   OR LOWER(TRIM(nome_usuario)) = LOWER(TRIM(%s))
LIMIT 1;

-- name: buscar_usuario_padrao
SELECT
    id::text AS id,
    nome_usuario,
    senha_hash
FROM usuario
ORDER BY nome_usuario ASC
LIMIT 1;
