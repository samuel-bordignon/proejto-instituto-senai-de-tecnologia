"""Parser multi-amostra de planilhas UltraLIMS (.xlsx / .csv) com detalhamento por KPI (RN-01, RN-02, RN-03, RN-05)."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any, Iterable, Optional, Union

import pandas as pd

from app.core.models import (
    OcorrenciaPreLeitura,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
)
from app.core.motor_conformidade import (
    interpretar_valor_bruto,
    normalizar_unidade,
    tem_sujeira_numerica,
)


_RE_COLUNA_ENSAIO = re.compile(r"^\s*(\d+)\s*[-–—]\s*(.+)$")

UnidadesVmpMap = dict[int, Union[str, set[str], list[str]]]


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


def _extrair_unidades_referencia(
    unidades_vmp: UnidadesVmpMap,
    id_num: int,
) -> list[str]:
    """Normaliza a entrada (str ou coleção de str) em lista deduplicada de unidades da legislação."""
    if id_num not in unidades_vmp:
        return []
    val = unidades_vmp[id_num]
    if isinstance(val, str):
        return [normalizar_unidade(val)]
    vistas: list[str] = []
    for u in val:
        norm = normalizar_unidade(u)
        if norm not in vistas:
            vistas.append(norm)
    return vistas


def _avaliar_divergencias_unidade_ensaio(
    id_num: int,
    nome_ensaio: str,
    bruto_strip: str,
    unidade_ensaio: str,
    unidades_vmp: UnidadesVmpMap,
    operadores_por_ensaio: Optional[dict[int, set[str]]] = None,
) -> list[OcorrenciaPreLeitura]:
    """Verifica RN-05 para o ensaio frente às unidades exigidas pelas normas selecionadas."""
    ops = (operadores_por_ensaio or {}).get(id_num)
    if ops and ops == {"AUSENCIA"}:
        return []

    unidades_normas = _extrair_unidades_referencia(unidades_vmp, id_num)
    if not unidades_normas:
        return []

    u_trab = normalizar_unidade(unidade_ensaio)
    divergentes = [u_vmp for u_vmp in unidades_normas if u_trab != u_vmp]
    if not divergentes:
        return []

    u_trab_txt = u_trab or "adimensional"
    u_vmp_txt = " / ".join(u or "adimensional" for u in divergentes)
    val_txt = f"{bruto_strip} {u_trab}".strip() if u_trab else bruto_strip
    return [
        OcorrenciaPreLeitura(
            classificacao="UNID. DIVERG.",
            tipo_pill="amber",
            ensaio_coluna=f"{id_num} · {nome_ensaio}",
            valor_bruto=val_txt,
            acao_motor=f"Unidade acreditada ({u_trab_txt}) difere do VMP ({u_vmp_txt}) → marcado PENDENTE (RN-05)",
        )
    ]


def _analisar_linha_amostra(
    linha: pd.Series,
    colunas: list[str],
    nome_arquivo: str,
    idx_linha: int,
    total_linhas: int,
    catalogo_ensaios: dict[int, dict[str, str]],
    unidades_vmp_referencia: UnidadesVmpMap,
    codigos_com_vmp: set[int],
    codigos_existentes: set[str],
    codigos_vistos_lote: set[str],
    operadores_vmp_referencia: Optional[dict[int, set[str]]] = None,
) -> ResultadoPreLeitura:
    codigo_amostra = f"{68410 + idx_linha}/2026"
    codigo_externo: Optional[str] = None

    for col in colunas:
        cname = str(col).strip().lower()
        val = "" if pd.isna(linha[col]) else str(linha[col]).strip()
        if not val or val.lower() == "nan":
            continue
        if "extern" in cname and any(k in cname for k in ("amostra", "código", "codigo", "cod")):
            if codigo_externo is None:
                codigo_externo = val
            continue
        if any(k in cname for k in ("amostra", "código", "codigo", "nº")):
            codigo_amostra = val
            break

    if codigo_externo is None:
        for col in colunas:
            cname = str(col).strip().lower()
            if "extern" in cname:
                val = "" if pd.isna(linha[col]) else str(linha[col]).strip()
                if val and val.lower() != "nan":
                    codigo_externo = val
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

    duplicada_banco = codigo_amostra in codigos_existentes
    duplicada_lote = codigo_amostra in codigos_vistos_lote
    duplicada = duplicada_banco or duplicada_lote

    if duplicada_banco:
        itens_avisos.append(
            OcorrenciaPreLeitura(
                classificacao="DUPLICADA",
                tipo_pill="red",
                ensaio_coluna=f"Amostra {codigo_amostra}",
                valor_bruto=codigo_amostra,
                acao_motor="Amostra já cadastrada no banco (RNF-03 / CT-11) — importação bloqueada para evitar duplicidade",
            )
        )
    elif duplicada_lote:
        itens_avisos.append(
            OcorrenciaPreLeitura(
                classificacao="DUPLICADA",
                tipo_pill="red",
                ensaio_coluna=f"Amostra {codigo_amostra}",
                valor_bruto=codigo_amostra,
                acao_motor="Código de amostra repetido no mesmo arquivo (RNF-03 / CT-11) — linha duplicada bloqueada",
            )
        )

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
                    acao_motor="Ensaio fora do catálogo de ensaios → não mapeado para avaliação legal",
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

        # RN-01 / CT-10: alerta somente sujeira numérica real (nunca vírgula decimal comum '7,91')
        suja, detalhe_sujeira = tem_sujeira_numerica(bruto)
        if suja and v is not None:
            itens_avisos.append(
                OcorrenciaPreLeitura(
                    classificacao="AVISO",
                    tipo_pill="amber",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=bruto,
                    acao_motor=f"Limpeza numérica RN-01 ({detalhe_sujeira} → {q or ''}{v:g})",
                )
            )

        if id_num in codigos_com_vmp:
            itens_avisos.extend(
                _avaliar_divergencias_unidade_ensaio(
                    id_num=id_num,
                    nome_ensaio=meta["nome"],
                    bruto_strip=bruto_strip,
                    unidade_ensaio=unid,
                    unidades_vmp=unidades_vmp_referencia,
                    operadores_por_ensaio=operadores_vmp_referencia,
                )
            )
        else:
            itens_sem_vmp.append(
                OcorrenciaPreLeitura(
                    classificacao="SEM VMP",
                    tipo_pill="gray",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=val_display,
                    acao_motor="Sem limite na legislação selecionada → gravado apenas para histórico",
                )
            )

    return ResultadoPreLeitura(
        nome_arquivo=nome_arquivo,
        amostras_detectadas=total_linhas,
        codigo_amostra_principal=codigo_amostra,
        codigo_externo=codigo_externo,
        data_coleta=data_coleta,
        data_conclusao=data_conclusao,
        duplicada=duplicada,
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


def recalcular_pre_leitura_por_normas(
    pre: ResultadoPreLeitura,
    catalogo_ensaios: dict[int, dict[str, str]],
    codigos_com_vmp: set[int],
    unidades_vmp_por_ensaio: UnidadesVmpMap,
    operadores_por_ensaio: Optional[dict[int, set[str]]] = None,
) -> ResultadoPreLeitura:
    """
    Recalcula dinamicamente os KPIs dependentes de legislação (SEM VMP e UNID. DIVERG.)
    quando o conferente altera as legislações/classes selecionadas na Etapa 2 de /importar (RF-03).
    Preserva intactos os itens mapeados, ignorados RN-02 e avisos estruturais (DUPLICADA, RN-01).
    """
    itens_mapeados = list(pre.itens_por_kpi.get("mapeados", []))
    itens_ignorados = list(pre.itens_por_kpi.get("ignorados", []))

    # Mantém avisos estruturais (DUPLICADA, Data Conclusão, limpeza RN-01) e descarta avisos de norma anteriores
    avisos_base = [
        item
        for item in pre.itens_por_kpi.get("avisos", [])
        if item.classificacao not in ("UNID. DIVERG.", "SEM MATCH NORMA")
    ]

    # Mantém ensaios fora do catálogo (não presentes em valores_brutos)
    sem_vmp_fora_catalogo = [
        item
        for item in pre.itens_por_kpi.get("sem_vmp", [])
        if _extrair_id_ocorrencia(item.ensaio_coluna) not in catalogo_ensaios
    ]

    novos_sem_vmp: list[OcorrenciaPreLeitura] = list(sem_vmp_fora_catalogo)
    novos_avisos: list[OcorrenciaPreLeitura] = list(avisos_base)
    qtd_com_vmp = 0

    for id_num, bruto_strip in pre.valores_brutos.items():
        meta = catalogo_ensaios.get(id_num)
        if not meta:
            continue
        unid = meta.get("unidade", "")
        val_display = (
            f"{bruto_strip} {unid}".strip()
            if unid and bruto_strip.lower() not in ("ausente", "presente")
            else bruto_strip
        )

        if id_num in codigos_com_vmp:
            qtd_com_vmp += 1
            novos_avisos.extend(
                _avaliar_divergencias_unidade_ensaio(
                    id_num=id_num,
                    nome_ensaio=meta["nome"],
                    bruto_strip=bruto_strip,
                    unidade_ensaio=unid,
                    unidades_vmp=unidades_vmp_por_ensaio,
                    operadores_por_ensaio=operadores_por_ensaio,
                )
            )
        else:
            novos_sem_vmp.append(
                OcorrenciaPreLeitura(
                    classificacao="SEM VMP",
                    tipo_pill="gray",
                    ensaio_coluna=f"{id_num} · {meta['nome']}",
                    valor_bruto=val_display,
                    acao_motor="Sem limite na legislação selecionada → gravado apenas para histórico",
                )
            )

    if pre.valores_brutos and qtd_com_vmp == 0:
        novos_avisos.append(
            OcorrenciaPreLeitura(
                classificacao="SEM MATCH NORMA",
                tipo_pill="amber",
                ensaio_coluna=f"Amostra {pre.codigo_amostra_principal}",
                valor_bruto="0 parâmetros avaliáveis",
                acao_motor="Nenhum ensaio desta amostra possui VMP nas legislações/classes selecionadas (verificar enquadramento)",
            )
        )

    return pre.model_copy(
        update={
            "total_mapeados": len(itens_mapeados),
            "total_sem_vmp": len(novos_sem_vmp),
            "total_ignorados": len(itens_ignorados),
            "total_avisos": len(novos_avisos),
            "ocorrencias": novos_avisos + itens_ignorados + novos_sem_vmp,
            "itens_por_kpi": {
                "mapeados": itens_mapeados,
                "sem_vmp": novos_sem_vmp,
                "ignorados": itens_ignorados,
                "avisos": novos_avisos,
            },
        }
    )


def recalcular_lote_por_normas(
    lote: ResultadoPreLeituraLote,
    catalogo_ensaios: dict[int, dict[str, str]],
    codigos_com_vmp: set[int],
    unidades_vmp_por_ensaio: UnidadesVmpMap,
    operadores_por_ensaio: Optional[dict[int, set[str]]] = None,
) -> ResultadoPreLeituraLote:
    """Recalcula os KPIs dependentes de normas para todas as amostras do lote."""
    return ResultadoPreLeituraLote(
        nome_arquivo=lote.nome_arquivo,
        amostras=[
            recalcular_pre_leitura_por_normas(
                pre=am,
                catalogo_ensaios=catalogo_ensaios,
                codigos_com_vmp=codigos_com_vmp,
                unidades_vmp_por_ensaio=unidades_vmp_por_ensaio,
                operadores_por_ensaio=operadores_por_ensaio,
            )
            for am in lote.amostras
        ],
    )


def _extrair_id_ocorrencia(ensaio_coluna: str) -> Optional[int]:
    m = re.match(r"^\s*(\d+)\s*[·\-–—]", ensaio_coluna or "")
    return int(m.group(1)) if m else None


def analisar_lote_ultralims(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    catalogo_ensaios: dict[int, dict[str, str]],
    unidades_vmp_referencia: Optional[UnidadesVmpMap] = None,
    codigos_com_vmp: Optional[set[int]] = None,
    codigos_existentes: Optional[Iterable[str]] = None,
    operadores_vmp_referencia: Optional[dict[int, set[str]]] = None,
    limite_amostras: int = 25,
) -> ResultadoPreLeituraLote:
    """
    Lê todas as amostras de uma planilha real (.xlsx / .csv) no formato UltraLIMS.
    Lança ValueError explícito quando o arquivo está vazio ou não contém colunas UltraLIMS.
    """
    unidades_vmp_referencia = unidades_vmp_referencia or {}
    codigos_com_vmp = set(catalogo_ensaios.keys()) if codigos_com_vmp is None else codigos_com_vmp
    existentes_norm = {str(c).strip() for c in (codigos_existentes or ()) if str(c).strip()}

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
    codigos_vistos_lote: set[str] = set()

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
            codigos_existentes=existentes_norm,
            codigos_vistos_lote=codigos_vistos_lote,
            operadores_vmp_referencia=operadores_vmp_referencia,
        )
        if res.total_mapeados > 0 or res.total_sem_vmp > 0:
            amostras.append(res)
            codigos_vistos_lote.add(res.codigo_amostra_principal)

    if not amostras:
        raise ValueError(
            "Nenhuma coluna no padrão UltraLIMS ('<código> - <ensaio>') com valores preenchidos foi encontrada."
        )

    return ResultadoPreLeituraLote(nome_arquivo=nome_arquivo, amostras=amostras)
