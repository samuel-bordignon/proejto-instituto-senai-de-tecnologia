-- ============================================================
-- LaudoTech — IST Ambiental
-- Estrutura Lógica do Banco de Dados (DDL)
-- Versão: 2.0 (com origem_amostra e legislacao_origem)
-- Atualizado em: 2026-10-23
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
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_usuario  VARCHAR(50) NOT NULL,
    senha_hash    CHAR(32)    NOT NULL
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
    CONSTRAINT UQ_legislacao_origem UNIQUE (fk_legislacao, fk_origem_amostra)
);

CREATE TABLE classe (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                 VARCHAR(50) NOT NULL,
    fk_legislacao_origem UUID        NOT NULL
);

CREATE TABLE ensaios (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    descricao      TEXT        NOT NULL,
    id_num         INT         NOT NULL UNIQUE, -- código canônico do UltraLIMS (ex: 48, 877)
    tipo_avaliacao VARCHAR(20) -- ENUM: 'AUTOMATICA' | 'MANUAL_TECNICA'
);

CREATE TABLE parametros (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    valor_max            DOUBLE PRECISION,
    valor_min            DOUBLE PRECISION,
    operador             VARCHAR(20),     -- ENUM: 'MENOR_IGUAL' | 'MAIOR_IGUAL' | 'FAIXA' | 'AUSENCIA'
    valor_esperado       VARCHAR(50),     -- usado quando operador = 'AUSENCIA'
    fk_legislacao_origem UUID             NOT NULL,
    fk_classe            UUID,            -- NULL para Portarias; preenchido para Resoluções
    fk_ensaios           UUID             NOT NULL,
    fk_unidade_medida    UUID,
    CONSTRAINT UQ_parametros_leg_origem_ensaio UNIQUE (fk_legislacao_origem, fk_ensaios)
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
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    nome_identificacao VARCHAR(50) NOT NULL
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
    codigo_amostra         VARCHAR(20),  -- código interno do LIMS (ex: 4799/2026)
    codigo_amostra_externo VARCHAR(20),  -- código externo / do cliente
    data_coleta            DATE,
    data_conclusao         DATE,
    status                 BOOLEAN,
    descricao              TEXT,
    fk_local_coleta        UUID        NOT NULL,
    fk_origem_amostra      UUID        NOT NULL,
    fk_usuario             UUID,
    fk_laboratorio         UUID
);

CREATE TABLE resultado_amostra (
    id             UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    valor_bruto    VARCHAR(100)     NOT NULL,  -- texto exato do CSV (ex: '<0,060', 'Ausente', '4.61')
    valor_numerico DOUBLE PRECISION,           -- número extraído para cálculos (NULL se qualitativo)
    qualificador   VARCHAR(5),                 -- '<' | '>' | NULL
    data_analise   TIMESTAMP,
    fk_amostra     UUID             NOT NULL,
    fk_ensaios     UUID             NOT NULL
);

-- ------------------------------------------------------------
-- BLOCO 5: Análise de Conformidade
-- ------------------------------------------------------------

CREATE TABLE analise_conformidade (
    fk_resultado_amostra UUID         NOT NULL,
    fk_parametros        UUID         NOT NULL,
    conformidade         BOOLEAN,     -- TRUE | FALSE | NULL (pendente)
    observacao           VARCHAR(255),
    PRIMARY KEY (fk_resultado_amostra, fk_parametros)
);

-- ============================================================
-- FOREIGN KEYS
-- ============================================================

ALTER TABLE legislacao_origem
    ADD CONSTRAINT FK_legislacao_origem_legislacao
    FOREIGN KEY (fk_legislacao) REFERENCES legislacao (id) ON DELETE RESTRICT;

ALTER TABLE legislacao_origem
    ADD CONSTRAINT FK_legislacao_origem_origem
    FOREIGN KEY (fk_origem_amostra) REFERENCES origem_amostra (id) ON DELETE RESTRICT;

ALTER TABLE classe
    ADD CONSTRAINT FK_classe_legislacao_origem
    FOREIGN KEY (fk_legislacao_origem) REFERENCES legislacao_origem (id) ON DELETE CASCADE;

ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_legislacao_origem
    FOREIGN KEY (fk_legislacao_origem) REFERENCES legislacao_origem (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_classe
    FOREIGN KEY (fk_classe) REFERENCES classe (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_ensaios
    FOREIGN KEY (fk_ensaios) REFERENCES ensaios (id) ON DELETE RESTRICT;

ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_unidade
    FOREIGN KEY (fk_unidade_medida) REFERENCES unidade_medida (id) ON DELETE RESTRICT;

ALTER TABLE proposta_comercial
    ADD CONSTRAINT FK_proposta_comercial_cliente
    FOREIGN KEY (fk_cliente) REFERENCES cliente (id) ON DELETE RESTRICT;

ALTER TABLE local_proposta
    ADD CONSTRAINT FK_local_proposta_local
    FOREIGN KEY (fk_local_coleta) REFERENCES local_coleta (id);

ALTER TABLE local_proposta
    ADD CONSTRAINT FK_local_proposta_proposta
    FOREIGN KEY (fk_proposta_comercial) REFERENCES proposta_comercial (id);

ALTER TABLE proposta_legislacao
    ADD CONSTRAINT FK_proposta_legislacao_legislacao
    FOREIGN KEY (fk_legislacao) REFERENCES legislacao (id);

ALTER TABLE proposta_legislacao
    ADD CONSTRAINT FK_proposta_legislacao_proposta
    FOREIGN KEY (fk_proposta_comercial) REFERENCES proposta_comercial (id);

ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_local
    FOREIGN KEY (fk_local_coleta) REFERENCES local_coleta (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_origem
    FOREIGN KEY (fk_origem_amostra) REFERENCES origem_amostra (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_usuario
    FOREIGN KEY (fk_usuario) REFERENCES usuario (id) ON DELETE RESTRICT;

ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_laboratorio
    FOREIGN KEY (fk_laboratorio) REFERENCES laboratorio (id) ON DELETE RESTRICT;

ALTER TABLE resultado_amostra
    ADD CONSTRAINT FK_resultado_amostra
    FOREIGN KEY (fk_amostra) REFERENCES amostra (id) ON DELETE RESTRICT;

ALTER TABLE resultado_amostra
    ADD CONSTRAINT FK_resultado_ensaio
    FOREIGN KEY (fk_ensaios) REFERENCES ensaios (id) ON DELETE RESTRICT;

ALTER TABLE analise_conformidade
    ADD CONSTRAINT FK_analise_resultado
    FOREIGN KEY (fk_resultado_amostra) REFERENCES resultado_amostra (id);

ALTER TABLE analise_conformidade
    ADD CONSTRAINT FK_analise_parametros
    FOREIGN KEY (fk_parametros) REFERENCES parametros (id);
