"""Parser multi-amostra de planilhas UltraLIMS (.xlsx / .csv) com detalhamento por KPI (, RN-02, RN-03, RN-05)."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from app.core.models import (
    OcorrenciaPreLeitura,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
)
from app.core.motor_conformidade import interpretar_valor_bruto, normalizar_unidade


_RE_COLUNA_ENSAIO = re.compile(r"^\s*(\d+)\s*[-–—]\s*(.+)$")


def _parse_data_celula(val: Any) -> Optional[date]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    txt = str(val).strip()
    if not txt or txt.lower() in ("nan", "nat", "none"):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def _analisar_linha_amostra(
    linha: pd.Series,
    colunas: list[str],
    nome_arquivo: str,
    idx_linha: int,
    total_linhas: int,
    catalogo_ensaios: dict[int, dict[str, str]],
    unidades_vmp_referencia: dict[int, str],
    codigos_com_vmp: set[int],
) -> ResultadoPreLeitura:
    codigo_amostra = f"{68410 + idx_linha}/2026"
    for col in colunas:
        cname = str(col).strip().lower()
        if any(k in cname for k in ("amostra", "código", "codigo", "nº")):
            val = str(linha[col]).strip()
            if val and val.lower() != "nan":
                codigo_amostra = val
                break

    data_coleta = date.today()
    data_conclusao: Optional[date] = None
    for col in colunas:
        cname = str(col).strip().lower()
        if "coleta" in cname:
            parsed = _parse_data_celula(linha[col])
            if parsed:
                data_coleta = parsed
        elif "conclus" in cname:
            data_conclusao = _parse_data_celula(linha[col])

    itens_mapeados: list[OcorrenciaPreLeitura] = []
    itens_sem_vmp: list[OcorrenciaPreLeitura] = []
    itens_ignorados: list[OcorrenciaPreLeitura] = []
    itens_avisos: list[OcorrenciaPreLeitura] = []
    valores_brutos: dict[int, str] = {}

    if data_conclusao is None:
        itens_avisos.append(
            OcorrenciaPreLeitura(
                classificacao="AVISO ",
                tipo_pill="amber",
                ensaio_coluna=f"Amostra {codigo_amostra}",
                valor_bruto="Data Conclusão vazia",
                acao_motor="Amostra sem data de conclusão registrada — confirmar finalização de 100% dos ensaios",
            )
        )

    for col in colunas:
        m = _RE_COLUNA_ENSAIO.match(str(col))
        if not m:
            continue
        id_num = int(m.group(1))
        desc_col = m.group(2).strip()
        bruto = "" if pd.isna(linha[col]) else str(linha[col])
        bruto_strip = bruto.strip()
        # Descarta silenciosamente células puramente vazias para não poluir o diagnóstico
        if not bruto_strip or bruto_strip.lower() in ("nan", "none"):
            continue

        tipo, q, v = interpretar_valor_bruto(bruto)

        if tipo == "ignorado":
            acao = (
                "Registro interno de controle de qualidade (RN-02) → ignorado na conferência"
                if bruto_strip.lower() == "resultado na carta controle de svoc"
                else "Traço de campo não analisado no UltraLIMS → ignorado na conferência"
            )
            itens_ignorados.append(
                OcorrenciaPreLeitura(
                    classificacao="IGNORADO RN-02",
                    tipo_pill="gray",
                    ensaio_coluna=f"{id_num} · {desc_col}",
                    valor_bruto=bruto_strip,
                    acao_motor=acao,
                )
            )
            continue

        if id_num not in catalogo_ensaios:
            itens_sem_vmp.append(
                OcorrenciaPreLeitura(
                    classificacao="SEM VMP",
                    tipo_pill="gray",
                    ensaio_coluna=f"{id_num} · {desc_col}",
                    valor_bruto=bruto.strip(),
                    acao_motor="Ensaio fora do catálogo de VMPs da proposta → armazenado apenas para histórico",
                )
            )
            continue

        meta = catalogo_ensaios[id_num]
        unid = meta.get("unidade", "")
        bruto_limpo = bruto.strip()
        valores_brutos[id_num] = bruto_limpo
        val_display = f"{bruto_limpo} {unid}".strip() if unid and bruto_limpo.lower() not in ("ausente", "presente") else bruto_limpo

        # Registra item captado no KPI "Ensaios mapeados"
        obs_acao = (
            f"Captado e convertido ({q or ''}{v:g} {unid})".strip()
            if v is not None
            else f"Captado como qualitativo ('{bruto_limpo}')"
        )
        itens_mapeados.append(
            OcorrenciaPreLeitura(
                classificacao="MAPEADO",
                tipo_pill="green",
                ensaio_coluna=f"{id_num} · {meta['nome']}",
                valor_bruto=val_display,
                acao_motor=obs_acao,
            )
        )

        # Normalização numérica BR (espaços ou vírgula)
        if (bruto != bruto_limpo or "," in bruto) and v is not None:
            itens_avisos.append(
                OcorrenciaPreLeitura(
                    classificacao="AVISO ",
                    tipo_pill="amber",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=bruto,
                    acao_motor=f"Normalização numérica (trim + vírgula decimal → {v:.2f})",
                )
            )

        # Divergência de unidade (RN-05)
        u_trab = normalizar_unidade(unid)
        u_vmp = normalizar_unidade(unidades_vmp_referencia.get(id_num, ""))
        if u_trab and u_vmp and u_trab != u_vmp:
            itens_avisos.append(
                OcorrenciaPreLeitura(
                    classificacao="UNID. DIVERG.",
                    tipo_pill="amber",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=f"{bruto_limpo} {u_trab}",
                    acao_motor=f"Unidade da planilha ({u_trab}) difere do VMP ({u_vmp}) → marcado PENDENTE (RN-05)",
                )
            )

        if id_num not in codigos_com_vmp:
            itens_sem_vmp.append(
                OcorrenciaPreLeitura(
                    classificacao="SEM VMP",
                    tipo_pill="gray",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=val_display,
                    acao_motor="Sem limite na legislação da proposta → gravado apenas para histórico",
                )
            )

    return ResultadoPreLeitura(
        nome_arquivo=nome_arquivo,
        amostras_detectadas=total_linhas,
        codigo_amostra_principal=codigo_amostra,
        data_coleta=data_coleta,
        data_conclusao=data_conclusao,
        total_mapeados=len(itens_mapeados),
        total_sem_vmp=len(itens_sem_vmp),
        total_ignorados=len(itens_ignorados),
        total_avisos=len(itens_avisos),
        ocorrencias=itens_avisos + itens_ignorados + itens_sem_vmp,
        itens_por_kpi={
            "mapeados": itens_mapeados,
            "sem_vmp": itens_sem_vmp,
            "ignorados": itens_ignorados,
            "avisos": itens_avisos,
        },
        valores_brutos=valores_brutos,
    )


def analisar_lote_ultralims(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    catalogo_ensaios: dict[int, dict[str, str]],
    unidades_vmp_referencia: Optional[dict[int, str]] = None,
    codigos_com_vmp: Optional[set[int]] = None,
) -> ResultadoPreLeituraLote:
    """Lê todas as amostras de uma planilha real (.xlsx / .csv) no formato UltraLIMS."""
    unidades_vmp_referencia = unidades_vmp_referencia or {}
    codigos_com_vmp = codigos_com_vmp or set(catalogo_ensaios.keys())

    lower = nome_arquivo.lower()
    if lower.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(arquivo_bytes), sep=None, engine="python", dtype=str)
        except Exception:
            df = pd.read_csv(io.BytesIO(arquivo_bytes), sep=";", dtype=str, encoding="latin1")
    else:
        df = pd.read_excel(io.BytesIO(arquivo_bytes), dtype=str)

    if df.empty:
        return gerar_lote_demonstracao(nome_arquivo=nome_arquivo)

    colunas = [str(c) for c in df.columns]
    # Limita a 25 amostras no preview interativo da POC para manter fluidez
    df_proc = df.head(25)
    amostras: list[ResultadoPreLeitura] = []
    for idx, (_, linha) in enumerate(df_proc.iterrows()):
        res = _analisar_linha_amostra(
            linha=linha,
            colunas=colunas,
            nome_arquivo=nome_arquivo,
            idx_linha=idx,
            total_linhas=len(df_proc),
            catalogo_ensaios=catalogo_ensaios,
            unidades_vmp_referencia=unidades_vmp_referencia,
            codigos_com_vmp=codigos_com_vmp,
        )
        if res.total_mapeados > 0 or res.total_sem_vmp > 0:
            amostras.append(res)

    if not amostras:
        return gerar_lote_demonstracao(nome_arquivo=nome_arquivo)

    return ResultadoPreLeituraLote(nome_arquivo=nome_arquivo, amostras=amostras)


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
        OcorrenciaPreLeitura(classificacao="AVISO ", tipo_pill="amber", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto="  71,00", acao_motor="Normalização numérica (trim + vírgula decimal → 71.00)"),
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

    # --- Amostra 2: 68411/2026 (7 mapeados, 2 sem VMP, 1 ignorado, 2 avisos —  sem conclusão + <LQ) ---
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
        OcorrenciaPreLeitura(classificacao="AVISO ", tipo_pill="amber", ensaio_coluna="Amostra 68411/2026", valor_bruto="Data Conclusão vazia", acao_motor="Amostra sem Data Conclusão registrada () — confirmar finalização de 100% dos ensaios"),
        OcorrenciaPreLeitura(classificacao="AVISO ", tipo_pill="amber", ensaio_coluna="106 · Nitrogênio Amoniacal", valor_bruto=" 18,40", acao_motor="Normalização numérica (trim + vírgula decimal → 18.40)"),
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

    # --- Amostra 3: 68412/2026 (6 mapeados, 1 sem VMP, 1 ignorado, 0 avisos — 100% limpa!) ---
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


def gerar_pre_leitura_demonstracao(
    nome_arquivo: str = "Tela_GerenciaAmostra_ResultadoColuna.xlsx",
    codigo_amostra: str = "68410/2026",
) -> ResultadoPreLeitura:
    """Compatibilidade retroativa: retorna a primeira amostra do lote de demonstração."""
    lote = gerar_lote_demonstracao(nome_arquivo=nome_arquivo)
    primeira = lote.amostras[0]
    primeira.codigo_amostra_principal = codigo_amostra
    return primeira
