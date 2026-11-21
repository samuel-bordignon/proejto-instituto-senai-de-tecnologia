"""Fixtures de demonstração de pré-leitura UltraLIMS (lote mockado da POC)."""

from __future__ import annotations

from datetime import date

from app.core.models import (
    OcorrenciaPreLeitura,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
)


def gerar_lote_demonstracao(
    nome_arquivo: str = "Tela_GerenciaAmostra_ResultadoColuna.xlsx",
) -> ResultadoPreLeituraLote:
    """
    Gera um lote realista com 3 amostras do UltraLIMS, com TODOS os ensaios captados
    discriminados individualmente em cada um dos 4 KPIs para conferência via tabela dinâmica.
    """
    # --- Amostra 1: 68410/2026 (14 mapeados, 4 sem VMP, 2 ignorados, 2 avisos) ---
    a1_mapeados = [
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="800 · Temperatura - Água", valor_bruto="40,0 °C", acao_motor="Captado e vinculado ao catálogo UltraLIMS (40.0 °C)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto="71,00 mg/L", acao_motor="Captado e normalizado (71.00 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="268 · Mercúrio", valor_bruto="<0,200 µg/L", acao_motor="Captado com qualificador <LQ (0.200 µg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="794 · pH", valor_bruto="7,91", acao_motor="Captado como numérico adimensional (7.91)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="119 · Sólidos Sedimentáveis", valor_bruto="<0,3 mL/L", acao_motor="Captado com qualificador <LQ (0.3 mL/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="784 · Materiais Flutuantes", valor_bruto="Ausente", acao_motor="Captado como qualitativo ('Ausente')"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="19 · DBO (5 dias)", valor_bruto="28,4 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (28.4 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="259 · Chumbo Total", valor_bruto="0,04 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (0.04 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="48 · Turbidez", valor_bruto="12,6 NTU", acao_motor="Captado e vinculado ao catálogo UltraLIMS (12.6 NTU)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="59 · Coliformes Termotolerantes", valor_bruto="180 UFC/100mL", acao_motor="Captado e vinculado ao catálogo UltraLIMS (180 UFC/100mL)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="157 · Cobre Dissolvido", valor_bruto="<0,005 mg/L", acao_motor="Captado com qualificador <LQ (0.005 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="110 · Óleos e Graxas Minerais", valor_bruto="14,2 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (14.2 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="312 · Zinco Total", valor_bruto="0,42 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (0.42 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="405 · Cromo Hexavalente", valor_bruto="<0,01 mg/L", acao_motor="Captado com qualificador <LQ (0.01 mg/L)"),
    ]
    a1_sem_vmp = [
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="93 · DQO", valor_bruto="148,0 mg/L", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="28 · Fósforo Total", valor_bruto="1,85 mg/L", acao_motor="Regra condicional fora do escopo automático → gravado apenas para histórico"),
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="112 · Condutividade Elétrica", valor_bruto="612 µS/cm", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="115 · Alcalinidade Total", valor_bruto="94,0 mg/L", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
    ]
    a1_ignorados = [
        OcorrenciaPreLeitura(classificacao="IGNORADO RN-02", tipo_pill="gray", ensaio_coluna="812 · Aspecto", valor_bruto="________", acao_motor="Traço de campo não analisado no UltraLIMS → ignorado na conferência"),
        OcorrenciaPreLeitura(classificacao="IGNORADO RN-02", tipo_pill="gray", ensaio_coluna="904 · Cor / SVOC", valor_bruto="Resultado na carta controle de SVOC", acao_motor="Registro interno de controle de qualidade (RN-02) → ignorado na conferência"),
    ]
    a1_avisos = [
        OcorrenciaPreLeitura(classificacao="AVISO", tipo_pill="amber", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto="  71,00", acao_motor="Normalização numérica (trim + vírgula decimal → 71.00)"),
        OcorrenciaPreLeitura(classificacao="UNID. DIVERG.", tipo_pill="amber", ensaio_coluna="268 · Mercúrio", valor_bruto="<0,200 µg/L", acao_motor="Unidade da planilha (µg/L) difere do VMP (mg/L) → marcado PENDENTE (RN-05)"),
    ]

    a1 = ResultadoPreLeitura(
        nome_arquivo=nome_arquivo,
        amostras_detectadas=3,
        codigo_amostra_principal="68410/2026",
        data_coleta=date(2026, 7, 24),
        data_conclusao=date(2026, 7, 28),
        total_mapeados=len(a1_mapeados),
        total_sem_vmp=len(a1_sem_vmp),
        total_ignorados=len(a1_ignorados),
        total_avisos=len(a1_avisos),
        ocorrencias=a1_avisos + a1_ignorados + a1_sem_vmp,
        itens_por_kpi={
            "mapeados": a1_mapeados,
            "sem_vmp": a1_sem_vmp,
            "ignorados": a1_ignorados,
            "avisos": a1_avisos,
        },
        valores_brutos={800: "40,0", 106: "71,00", 268: "<0,200", 794: "7,91", 119: "<0,3", 784: "Ausente"},
    )

    # --- Amostra 2: 68411/2026 (7 mapeados, 2 sem VMP, 1 ignorado, 2 avisos) ---
    a2_mapeados = [
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="800 · Temperatura - Água", valor_bruto="34,2 °C", acao_motor="Captado e vinculado ao catálogo UltraLIMS (34.2 °C)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto="18,40 mg/L", acao_motor="Captado e normalizado (18.40 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="19 · DBO (5 dias)", valor_bruto="<5,00 mg/L", acao_motor="Captado com qualificador <LQ (5.00 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="794 · pH", valor_bruto="7,35", acao_motor="Captado como numérico adimensional (7.35)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="119 · Sólidos Sedimentáveis", valor_bruto="<0,3 mL/L", acao_motor="Captado com qualificador <LQ (0.3 mL/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="784 · Materiais Flutuantes", valor_bruto="Ausente", acao_motor="Captado como qualitativo ('Ausente')"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="259 · Chumbo Total", valor_bruto="0,02 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (0.02 mg/L)"),
    ]
    a2_sem_vmp = [
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="93 · DQO", valor_bruto="82,0 mg/L", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="112 · Condutividade Elétrica", valor_bruto="488 µS/cm", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
    ]
    a2_ignorados = [
        OcorrenciaPreLeitura(classificacao="IGNORADO RN-02", tipo_pill="gray", ensaio_coluna="812 · Aspecto", valor_bruto="________", acao_motor="Traço de campo não analisado no UltraLIMS → ignorado na conferência"),
    ]
    a2_avisos = [
        OcorrenciaPreLeitura(classificacao="AVISO", tipo_pill="amber", ensaio_coluna="Amostra 68411/2026", valor_bruto="Data Conclusão vazia", acao_motor="Amostra sem Data Conclusão registrada (RN-01) — confirmar finalização de 100% dos ensaios"),
        OcorrenciaPreLeitura(classificacao="AVISO", tipo_pill="amber", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto=" 18,40", acao_motor="Normalização numérica (trim + vírgula decimal → 18.40)"),
    ]

    a2 = ResultadoPreLeitura(
        nome_arquivo=nome_arquivo,
        amostras_detectadas=3,
        codigo_amostra_principal="68411/2026",
        data_coleta=date(2026, 7, 25),
        data_conclusao=None,
        total_mapeados=len(a2_mapeados),
        total_sem_vmp=len(a2_sem_vmp),
        total_ignorados=len(a2_ignorados),
        total_avisos=len(a2_avisos),
        ocorrencias=a2_avisos + a2_ignorados + a2_sem_vmp,
        itens_por_kpi={
            "mapeados": a2_mapeados,
            "sem_vmp": a2_sem_vmp,
            "ignorados": a2_ignorados,
            "avisos": a2_avisos,
        },
        valores_brutos={800: "34,2", 106: "18,40", 19: "<5,00", 794: "7,35", 119: "<0,3", 784: "Ausente", 259: "0,02"},
    )

    # --- Amostra 3: 68412/2026 (6 mapeados, 1 sem VMP, 1 ignorado, 0 avisos) ---
    a3_mapeados = [
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="800 · Temperatura - Água", valor_bruto="29,8 °C", acao_motor="Captado e vinculado ao catálogo UltraLIMS (29.8 °C)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto="11,20 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (11.20 mg/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="794 · pH", valor_bruto="7,18", acao_motor="Captado como numérico adimensional (7.18)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="119 · Sólidos Sedimentáveis", valor_bruto="<0,3 mL/L", acao_motor="Captado com qualificador <LQ (0.3 mL/L)"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="784 · Materiais Flutuantes", valor_bruto="Ausente", acao_motor="Captado como qualitativo ('Ausente')"),
        OcorrenciaPreLeitura(classificacao="MAPEADO", tipo_pill="green", ensaio_coluna="259 · Chumbo Total", valor_bruto="0,01 mg/L", acao_motor="Captado e vinculado ao catálogo UltraLIMS (0.01 mg/L)"),
    ]
    a3_sem_vmp = [
        OcorrenciaPreLeitura(classificacao="SEM VMP", tipo_pill="gray", ensaio_coluna="93 · DQO", valor_bruto="64,0 mg/L", acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico"),
    ]
    a3_ignorados = [
        OcorrenciaPreLeitura(classificacao="IGNORADO RN-02", tipo_pill="gray", ensaio_coluna="904 · Cor", valor_bruto="________", acao_motor="Traço de campo não analisado no UltraLIMS → ignorado na conferência"),
    ]

    a3 = ResultadoPreLeitura(
        nome_arquivo=nome_arquivo,
        amostras_detectadas=3,
        codigo_amostra_principal="68412/2026",
        data_coleta=date(2026, 7, 26),
        data_conclusao=date(2026, 7, 29),
        total_mapeados=len(a3_mapeados),
        total_sem_vmp=len(a3_sem_vmp),
        total_ignorados=len(a3_ignorados),
        total_avisos=0,
        ocorrencias=a3_ignorados + a3_sem_vmp,
        itens_por_kpi={
            "mapeados": a3_mapeados,
            "sem_vmp": a3_sem_vmp,
            "ignorados": a3_ignorados,
            "avisos": [],
        },
        valores_brutos={800: "29,8", 106: "11,20", 794: "7,18", 119: "<0,3", 784: "Ausente", 259: "0,01"},
    )

    return ResultadoPreLeituraLote(nome_arquivo=nome_arquivo, amostras=[a1, a2, a3])
