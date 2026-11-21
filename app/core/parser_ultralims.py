"""Parser multi-amostra de planilhas UltraLIMS (.xlsx / .csv) com detalhamento por KPI (RN-01, RN-02, RN-03, RN-05)."""

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
                classificacao="AVISO",
                tipo_pill="amber",
                ensaio_coluna=f"Amostra {codigo_amostra}",
                valor_bruto="Data Conclusão vazia",
                acao_motor="Amostra sem data de conclusão registrada (RN-01) — confirmar finalização de 100% dos ensaios",
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
                    valor_bruto=bruto_strip,
                    acao_motor="Ensaio fora do catálogo de VMPs da proposta → armazenado apenas para histórico",
                )
            )
            continue

        meta = catalogo_ensaios[id_num]
        unid = meta.get("unidade", "")
        valores_brutos[id_num] = bruto_strip
        val_display = (
            f"{bruto_strip} {unid}".strip()
            if unid and bruto_strip.lower() not in ("ausente", "presente")
            else bruto_strip
        )

        obs_acao = (
            f"Captado e convertido ({q or ''}{v:g} {unid})".strip()
            if v is not None
            else f"Captado como qualitativo ('{bruto_strip}')"
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

        # Normalização numérica BR (espaços ou vírgula decimal)
        if (bruto != bruto_strip or "," in bruto) and v is not None:
            itens_avisos.append(
                OcorrenciaPreLeitura(
                    classificacao="AVISO",
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
                    valor_bruto=f"{bruto_strip} {u_trab}",
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
    limite_amostras: int = 25,
) -> ResultadoPreLeituraLote:
    """
    Lê todas as amostras de uma planilha real (.xlsx / .csv) no formato UltraLIMS.
    Lança ValueError explícito quando o arquivo está vazio ou não contém colunas UltraLIMS.
    """
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
        raise ValueError("A planilha enviada está vazia.")

    colunas = [str(c) for c in df.columns]
    df_proc = df.head(limite_amostras)
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
        raise ValueError(
            "Nenhuma coluna no padrão UltraLIMS ('<código> - <ensaio>') com valores preenchidos foi encontrada."
        )

    return ResultadoPreLeituraLote(nome_arquivo=nome_arquivo, amostras=amostras)
