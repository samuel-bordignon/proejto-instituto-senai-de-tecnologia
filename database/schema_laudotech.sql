-- ============================================================
-- LaudoTech — IST Ambiental
-- Estrutura Lógica do Banco de Dados (DDL)
-- Versão: 2.2 (com fk_unidade_medida em ensaios, múltiplas classes e log_alteracao)
-- Atualizado em: 2026-11-21
-- ============================================================

-- ------------------------------------------------------------
-- BLOCO 1: Cadastros Base / Dados Mestres
-- ------------------------------------------------------------

CREATE TABLE cliente (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social  VARCHAR(150) NOT NULL,
    cnpj          VARCHAR(14),
    cidade        VARCHAR(100),
    uf            CHAR(2),
    contato       VARCHAR(20)
);

CREATE TABLE laboratorio (
    id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(50) NOT NULL
);

CREATE TABLE usuario (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_usuario  VARCHAR(50)  NOT NULL,
    senha_hash    VARCHAR(100) NOT NULL,
    CONSTRAINT uq_usuario_nome UNIQUE (nome_usuario)
);

CREATE TABLE unidade_medida (
    id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    descricao VARCHAR(50) NOT NULL UNIQUE
);

-- ------------------------------------------------------------
-- BLOCO 2: Base Legal (Legislações, Origens, Classes, Ensaios, VMPs)
-- ------------------------------------------------------------

CREATE TABLE legislacao (
    id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE origem_amostra (
    id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE legislacao_origem (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_legislacao     UUID NOT NULL,
    fk_origem_amostra UUID NOT NULL,
    CONSTRAINT uq_legislacao_origem UNIQUE (fk_legislacao, fk_origem_amostra)
);

CREATE TABLE classe (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                 VARCHAR(50) NOT NULL,
    fk_legislacao_origem UUID        NOT NULL,
    CONSTRAINT uq_classe_leg_origem_nome UNIQUE (fk_legislacao_origem, nome)
);

CREATE TABLE ensaios (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    descricao         TEXT        NOT NULL,
    id_num            INT         NOT NULL UNIQUE, -- código canônico do UltraLIMS (ex: 48, 877)
    tipo_avaliacao    VARCHAR(20),                 -- 'AUTOMATICA' | 'MANUAL_TECNICA'
    fk_unidade_medida UUID                         -- unidade acreditada de trabalho (NULL se adimensional)
);

CREATE TABLE parametros (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    valor_max            DOUBLE PRECISION,
    valor_min            DOUBLE PRECISION,
    operador             VARCHAR(20),     -- 'MENOR_IGUAL' | 'MENOR_ESTRITO' | 'MAIOR_IGUAL' | 'FAIXA' | 'AUSENCIA'
    valor_esperado       VARCHAR(50),     -- usado quando operador = 'AUSENCIA'
    fk_legislacao_origem UUID             NOT NULL,
    fk_classe            UUID,            -- NULL para Portarias e regras Sem Classe (ex: CONAMA 430 Art. 16)
    fk_ensaios           UUID             NOT NULL,
    fk_unidade_medida    UUID,
    CONSTRAINT uq_parametros_regra UNIQUE NULLS NOT DISTINCT (fk_legislacao_origem, fk_classe, fk_ensaios)
);

-- ------------------------------------------------------------
-- BLOCO 3: Proposta Comercial e Locais
-- ------------------------------------------------------------

CREATE TABLE proposta_comercial (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    data_inicio DATE,
    data_fim    DATE,
    status      BOOLEAN DEFAULT TRUE,
    fk_cliente  UUID    NOT NULL
);

CREATE TABLE local_coleta (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_identificacao VARCHAR(120) NOT NULL
);

CREATE TABLE local_proposta (
    fk_local_coleta       UUID NOT NULL,
    fk_proposta_comercial UUID NOT NULL,
    PRIMARY KEY (fk_local_coleta, fk_proposta_comercial)
);

CREATE TABLE proposta_legislacao (
    fk_legislacao         UUID NOT NULL,
    fk_proposta_comercial UUID NOT NULL,
    PRIMARY KEY (fk_legislacao, fk_proposta_comercial)
);

-- ------------------------------------------------------------
-- BLOCO 4: Execução (Amostras e Resultados LIMS)
-- ------------------------------------------------------------

CREATE TABLE amostra (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_amostra         VARCHAR(20),  -- código interno do LIMS (ex: 63450/2026)
    codigo_amostra_externo VARCHAR(20),  -- código externo / do cliente
    data_coleta            DATE,
    data_conclusao         DATE,
    status                 BOOLEAN,      -- TRUE = Favorável | FALSE = Não favorável | NULL = Pendente
    descricao              TEXT,         -- texto da minuta / parecer técnico
    fk_local_coleta        UUID        NOT NULL,
    fk_origem_amostra      UUID        NOT NULL,
    fk_usuario             UUID,
    fk_laboratorio         UUID,
    CONSTRAINT uq_amostra_codigo UNIQUE (codigo_amostra)
);

CREATE TABLE resultado_amostra (
    id             UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    valor_bruto    VARCHAR(100)     NOT NULL, -- texto exato da planilha (ex: '<0,060', 'Ausente', '4.61')
    valor_numerico DOUBLE PRECISION,          -- número extraído para cálculos (NULL se qualitativo)
    qualificador   VARCHAR(5),                -- '<' | '>' | NULL
    data_analise   TIMESTAMP,
    fk_amostra     UUID             NOT NULL,
    fk_ensaios     UUID             NOT NULL,
    CONSTRAINT uq_resultado_amostra_ensaio UNIQUE (fk_amostra, fk_ensaios)
);

-- ------------------------------------------------------------
-- BLOCO 5: Análise de Conformidade e Auditoria (RN-10)
-- ------------------------------------------------------------

CREATE TABLE analise_conformidade (
    fk_resultado_amostra UUID         NOT NULL,
    fk_parametros        UUID         NOT NULL,
    conformidade         BOOLEAN,     -- TRUE | FALSE | NULL (pendente)
    observacao           VARCHAR(255),
    PRIMARY KEY (fk_resultado_amostra, fk_parametros)
);

CREATE TABLE log_alteracao (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_amostra           UUID        NOT NULL,
    fk_resultado_amostra UUID,       -- preenchido em edição de ensaio; NULL em parecer_geral / minuta
    fk_usuario           UUID        NOT NULL,
    campo_alterado       VARCHAR(50) NOT NULL, -- 'conformidade' | 'parecer_geral' | 'minuta'
    valor_anterior       TEXT,
    valor_novo           TEXT        NOT NULL,
    observacao           TEXT,
    data_alteracao       TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- FOREIGN KEYS
-- ============================================================

ALTER TABLE legislacao_origem
    ADD CONSTRAINT fk_legislacao_origem_legislacao
    FOREIGN KEY (fk_legislacao) REFERENCES legislacao (id) ON DELETE RESTRICT;

ALTER TABLE legislacao_origem
    ADD CONSTRAINT fk_legislacao_origem_origem
    FOREIGN KEY (fk_origem_amostra) REFERENCES origem_amostra (id) ON DELETE RESTRICT;

ALTER TABLE classe
    ADD CONSTRAINT fk_classe_legislacao_origem
    FOREIGN KEY (fk_legislacao_origem) REFERENCES legislacao_origem (id) ON DELETE CASCADE;

ALTER TABLE ensaios
    ADD CONSTRAINT fk_ensaios_unidade
    FOREIGN KEY (fk_unidade_medida) REFERENCES unidade_medida (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT fk_parametros_legislacao_origem
    FOREIGN KEY (fk_legislacao_origem) REFERENCES legislacao_origem (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT fk_parametros_classe
    FOREIGN KEY (fk_classe) REFERENCES classe (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT fk_parametros_ensaios
    FOREIGN KEY (fk_ensaios) REFERENCES ensaios (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT fk_parametros_unidade
    FOREIGN KEY (fk_unidade_medida) REFERENCES unidade_medida (id) ON DELETE RESTRICT;

ALTER TABLE proposta_comercial
    ADD CONSTRAINT fk_proposta_comercial_cliente
    FOREIGN KEY (fk_cliente) REFERENCES cliente (id) ON DELETE RESTRICT;

ALTER TABLE local_proposta
    ADD CONSTRAINT fk_local_proposta_local
    FOREIGN KEY (fk_local_coleta) REFERENCES local_coleta (id);

ALTER TABLE local_proposta
    ADD CONSTRAINT fk_local_proposta_proposta
    FOREIGN KEY (fk_proposta_comercial) REFERENCES proposta_comercial (id);

ALTER TABLE proposta_legislacao
    ADD CONSTRAINT fk_proposta_legislacao_legislacao
    FOREIGN KEY (fk_legislacao) REFERENCES legislacao (id);

ALTER TABLE proposta_legislacao
    ADD CONSTRAINT fk_proposta_legislacao_proposta
    FOREIGN KEY (fk_proposta_comercial) REFERENCES proposta_comercial (id);

ALTER TABLE amostra
    ADD CONSTRAINT fk_amostra_local
    FOREIGN KEY (fk_local_coleta) REFERENCES local_coleta (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT fk_amostra_origem
    FOREIGN KEY (fk_origem_amostra) REFERENCES origem_amostra (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT fk_amostra_usuario
    FOREIGN KEY (fk_usuario) REFERENCES usuario (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT fk_amostra_laboratorio
    FOREIGN KEY (fk_laboratorio) REFERENCES laboratorio (id) ON DELETE RESTRICT;

ALTER TABLE resultado_amostra
    ADD CONSTRAINT fk_resultado_amostra
    FOREIGN KEY (fk_amostra) REFERENCES amostra (id) ON DELETE RESTRICT;

ALTER TABLE resultado_amostra
    ADD CONSTRAINT fk_resultado_ensaio
    FOREIGN KEY (fk_ensaios) REFERENCES ensaios (id) ON DELETE RESTRICT;

ALTER TABLE analise_conformidade
    ADD CONSTRAINT fk_analise_resultado
    FOREIGN KEY (fk_resultado_amostra) REFERENCES resultado_amostra (id);

ALTER TABLE analise_conformidade
    ADD CONSTRAINT fk_analise_parametros
    FOREIGN KEY (fk_parametros) REFERENCES parametros (id);

ALTER TABLE log_alteracao
    ADD CONSTRAINT fk_log_alteracao_amostra
    FOREIGN KEY (fk_amostra) REFERENCES amostra (id) ON DELETE CASCADE;

ALTER TABLE log_alteracao
    ADD CONSTRAINT fk_log_alteracao_resultado
    FOREIGN KEY (fk_resultado_amostra) REFERENCES resultado_amostra (id) ON DELETE CASCADE;

ALTER TABLE log_alteracao
    ADD CONSTRAINT fk_log_alteracao_usuario
    FOREIGN KEY (fk_usuario) REFERENCES usuario (id) ON DELETE RESTRICT;

-- ============================================================
-- ÍNDICES
-- ============================================================

CREATE INDEX idx_amostra_local_data
    ON amostra (fk_local_coleta, data_coleta DESC);

CREATE INDEX idx_resultado_amostra_ensaio
    ON resultado_amostra (fk_ensaios, fk_amostra);

CREATE INDEX idx_log_alteracao_amostra
    ON log_alteracao (fk_amostra, data_alteracao DESC);
