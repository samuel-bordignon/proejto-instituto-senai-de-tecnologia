-- ============================================================
-- LaudoTech — IST Ambiental
-- Estrutura Lógica do Banco de Dados (DDL)
-- Versão: 1.0
-- Gerado em: 2026-10-02
-- ============================================================

-- ------------------------------------------------------------
-- BLOCO 1: Cadastros Base / Dados Mestres
-- ------------------------------------------------------------

CREATE TABLE cliente (
    id            UUID         PRIMARY KEY,
    razao_social  VARCHAR(150) NOT NULL,
    cnpj          VARCHAR(14),
    cidade        VARCHAR(100),
    uf            CHAR(2),
    contato       VARCHAR(20)
);

CREATE TABLE laboratorio (
    id   UUID        PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

CREATE TABLE usuario (
    id            UUID        PRIMARY KEY,
    nome_usuario  VARCHAR(50) NOT NULL,
    senha_hash    CHAR(32)    NOT NULL
);

CREATE TABLE unidade_medida (
    id        UUID        PRIMARY KEY,
    descricao VARCHAR(50) NOT NULL
);

-- ------------------------------------------------------------
-- BLOCO 2: Base Legal (Legislações, Classes, Ensaios, VMPs)
-- ------------------------------------------------------------

CREATE TABLE legislacao (
    id   UUID        PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

CREATE TABLE classe (
    id            UUID        PRIMARY KEY,
    nome          VARCHAR(50) NOT NULL,
    fk_legislacao UUID        NOT NULL,
    fk_parametros UUID        -- ver FK após criação de parametros
);

CREATE TABLE ensaios (
    id             UUID    PRIMARY KEY,
    descricao      TEXT    NOT NULL,
    id_num         INT     UNIQUE NOT NULL, -- código canônico do UltraLIMS (ex: 48, 877)
    tipo_avaliacao VARCHAR(20) -- ENUM: 'AUTOMATICA' | 'MANUAL_TECNICA'
);

CREATE TABLE parametros (
    id              UUID         PRIMARY KEY,
    valor_max       FLOAT,
    valor_min       FLOAT,
    operador        VARCHAR(20),  -- ENUM: 'MENOR_IGUAL' | 'MAIOR_IGUAL' | 'FAIXA' | 'AUSENCIA'
    valor_esperado  VARCHAR(50),  -- usado quando operador = 'AUSENCIA'
    fk_legislacao   UUID         NOT NULL,
    fk_ensaios      UUID         NOT NULL,
    fk_unidade_medida UUID
);

-- ------------------------------------------------------------
-- BLOCO 3: Proposta Comercial e Locais
-- ------------------------------------------------------------

CREATE TABLE proposta_comercial (
    id          UUID    PRIMARY KEY,
    data_inicio DATE,
    data_fim    DATE,
    status      BOOLEAN DEFAULT TRUE,
    fk_cliente  UUID    NOT NULL
);

CREATE TABLE local_coleta (
    id                  UUID        PRIMARY KEY,
    nome_identificacao  VARCHAR(50) NOT NULL,
    tipo_matriz_padrao  VARCHAR(50)
);

-- Tabela associativa: local pertence a uma ou mais propostas
CREATE TABLE local_proposta (
    fk_local_coleta       UUID NOT NULL,
    fk_proposta_comercial UUID NOT NULL,
    PRIMARY KEY (fk_local_coleta, fk_proposta_comercial)
);

-- Tabela associativa: legislações vinculadas a uma proposta
CREATE TABLE proposta_legislacao (
    fk_legislacao         UUID NOT NULL,
    fk_proposta_comercial UUID NOT NULL,
    PRIMARY KEY (fk_legislacao, fk_proposta_comercial)
);

-- ------------------------------------------------------------
-- BLOCO 4: Execução (Amostras e Resultados LIMS)
-- ------------------------------------------------------------

CREATE TABLE amostra (
    id                    UUID        PRIMARY KEY,
    codigo_amostra        VARCHAR(20),  -- código interno do LIMS (ex: 4799/2026)
    codigo_amostra_externo VARCHAR(20), -- código externo / do cliente
    data_coleta           DATE,
    data_conclusao        DATE,
    status                BOOLEAN,
    descricao             TEXT
    fk_local_coleta       UUID NOT NULL,
    fk_usuario            UUID,
    fk_laboratorio        UUID
);

CREATE TABLE resultado_amostra (
    id             UUID         PRIMARY KEY,
    valor_bruto    VARCHAR(100) NOT NULL,  -- texto exato do CSV (ex: '<0,060', 'Ausente', '4.61')
    valor_numerico FLOAT,                  -- número extraído para cálculos (NULL se qualitativo)
    qualificador   VARCHAR(5),             -- '<' | '>' | NULL
    data_analise   TIMESTAMP,
    fk_amostra     UUID NOT NULL,
    fk_ensaios     UUID NOT NULL
);

-- ------------------------------------------------------------
-- BLOCO 5: Análise de Conformidade
-- ------------------------------------------------------------

CREATE TABLE analise_conformidade (
    -- Chave composta natural: um resultado vs. um parâmetro
    fk_resultado_amostra UUID    NOT NULL,
    fk_parametros        UUID    NOT NULL,
    conformidade         BOOLEAN,          -- TRUE | FALSE | NULL (pendente)
    observacao           VARCHAR(255),
    PRIMARY KEY (fk_resultado_amostra, fk_parametros)
);

-- ============================================================
-- FOREIGN KEYS
-- ============================================================

-- proposta_comercial → cliente
ALTER TABLE proposta_comercial
    ADD CONSTRAINT FK_proposta_comercial_cliente
    FOREIGN KEY (fk_cliente)
    REFERENCES cliente (id)
    ON DELETE RESTRICT;

-- local_proposta → local_coleta
ALTER TABLE local_proposta
    ADD CONSTRAINT FK_local_proposta_local
    FOREIGN KEY (fk_local_coleta)
    REFERENCES local_coleta (id);

-- local_proposta → proposta_comercial
ALTER TABLE local_proposta
    ADD CONSTRAINT FK_local_proposta_proposta
    FOREIGN KEY (fk_proposta_comercial)
    REFERENCES proposta_comercial (id);

-- proposta_legislacao → legislacao
ALTER TABLE proposta_legislacao
    ADD CONSTRAINT FK_proposta_legislacao_legislacao
    FOREIGN KEY (fk_legislacao)
    REFERENCES legislacao (id);

-- proposta_legislacao → proposta_comercial
ALTER TABLE proposta_legislacao
    ADD CONSTRAINT FK_proposta_legislacao_proposta
    FOREIGN KEY (fk_proposta_comercial)
    REFERENCES proposta_comercial (id);

-- amostra → local_coleta
ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_local
    FOREIGN KEY (fk_local_coleta)
    REFERENCES local_coleta (id)
    ON DELETE RESTRICT;

-- amostra → usuario
ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_usuario
    FOREIGN KEY (fk_usuario)
    REFERENCES usuario (id)
    ON DELETE RESTRICT;

-- amostra → laboratorio
ALTER TABLE amostra
    ADD CONSTRAINT FK_amostra_laboratorio
    FOREIGN KEY (fk_laboratorio)
    REFERENCES laboratorio (id)
    ON DELETE RESTRICT;

-- resultado_amostra → amostra
ALTER TABLE resultado_amostra
    ADD CONSTRAINT FK_resultado_amostra
    FOREIGN KEY (fk_amostra)
    REFERENCES amostra (id)
    ON DELETE RESTRICT;

-- resultado_amostra → ensaios
ALTER TABLE resultado_amostra
    ADD CONSTRAINT FK_resultado_ensaio
    FOREIGN KEY (fk_ensaios)
    REFERENCES ensaios (id)
    ON DELETE RESTRICT;

-- parametros → legislacao
ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_legislacao
    FOREIGN KEY (fk_legislacao)
    REFERENCES legislacao (id)
    ON DELETE RESTRICT;

-- parametros → ensaios
ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_ensaios
    FOREIGN KEY (fk_ensaios)
    REFERENCES ensaios (id)
    ON DELETE RESTRICT;

-- parametros → unidade_medida
ALTER TABLE parametros
    ADD CONSTRAINT FK_parametros_unidade
    FOREIGN KEY (fk_unidade_medida)
    REFERENCES unidade_medida (id)
    ON DELETE RESTRICT;

-- analise_conformidade → resultado_amostra
ALTER TABLE analise_conformidade
    ADD CONSTRAINT FK_analise_resultado
    FOREIGN KEY (fk_resultado_amostra)
    REFERENCES resultado_amostra (id);

-- analise_conformidade → parametros
ALTER TABLE analise_conformidade
    ADD CONSTRAINT FK_analise_parametros
    FOREIGN KEY (fk_parametros)
    REFERENCES parametros (id);

-- classe → legislacao
ALTER TABLE classe
    ADD CONSTRAINT FK_classe_legislacao
    FOREIGN KEY (fk_legislacao)
    REFERENCES legislacao (id)
    ON DELETE CASCADE;

-- classe → parametros
ALTER TABLE classe
    ADD CONSTRAINT FK_classe_parametros
    FOREIGN KEY (fk_parametros)
    REFERENCES parametros (id)
    ON DELETE CASCADE;
