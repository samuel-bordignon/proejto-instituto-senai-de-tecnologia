"""Gerador de planilha de conferência técnica e auditoria em XLSX (RF-07 / RNF-02 / RN-10)."""

from __future__ import annotations

import io
from datetime import date
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    STATUS_CONFORME,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.models import Amostra
from app.core.motor_conformidade import formatar_numero_br, resumir_diagnostico_amostra


# Paleta institucional LaudoTech / SENAI
_AZUL_CORP = "004B8D"
_AZUL_SUAVE = "EBF3FA"
_CINZA_CAB = "3F3F46"
_CINZA_CARD = "F8FAFC"
_BORDA_COR = "CBD5E1"
_TEXTO = "111827"
_MUTED = "52525B"

_VERDE_BG = "DCFCE7"
_VERDE_TXT = "15803D"
_VERMELHO_BG = "FEE2E2"
_VERMELHO_LINHA = "FEF2F2"
_VERMELHO_TXT = "DC2626"
_AMBAR_BG = "FEF3C7"
_AMBAR_LINHA = "FFFBEB"
_AMBAR_TXT = "B45309"


def _borda_fina() -> Border:
    lado = Side(style="thin", color=_BORDA_COR)
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def _auto_ajustar_larguras(ws, largura_min: int = 10, largura_max: int = 52) -> None:
    """Ajusta largura das colunas conforme o maior conteúdo de texto, respeitando limites seguros."""
    for col_cells in ws.columns:
        max_len = 0
        col_idx = col_cells[0].column
        for cell in col_cells:
            val = cell.value
            if val is None:
                continue
            linhas = str(val).splitlines() or [""]
            maior_linha = max(len(l) for l in linhas)
            if maior_linha > max_len:
                max_len = maior_linha
        ws.column_dimensions[get_column_letter(col_idx)].width = max(
            largura_min, min(largura_max, max_len + 4)
        )


def _rotulo_veredito(conformidade: Optional[bool]) -> str:
    if conformidade is True:
        return STATUS_CONFORME
    if conformidade is False:
        return STATUS_NAO_CONFORME
    return STATUS_PENDENTE


def _estilo_status(status: str) -> tuple[PatternFill, Font]:
    if status in (STATUS_NAO_CONFORME, GERAL_NAO_FAVORAVEL):
        return (
            PatternFill("solid", fgColor=_VERMELHO_BG),
            Font(name="Calibri", size=10, bold=True, color=_VERMELHO_TXT),
        )
    if status in (STATUS_CONFORME, GERAL_FAVORAVEL):
        return (
            PatternFill("solid", fgColor=_VERDE_BG),
            Font(name="Calibri", size=10, bold=True, color=_VERDE_TXT),
        )
    return (
        PatternFill("solid", fgColor=_AMBAR_BG),
        Font(name="Calibri", size=10, bold=True, color=_AMBAR_TXT),
    )


def _montar_aba_resumo(wb: Workbook, amostra: Amostra) -> None:
    ws = wb.active
    ws.title = "Resumo e Parecer"
    ws.views.sheetView[0].showGridLines = True

    borda = _borda_fina()
    fill_azul = PatternFill("solid", fgColor=_AZUL_CORP)
    fill_label = PatternFill("solid", fgColor=_AZUL_SUAVE)
    fill_card = PatternFill("solid", fgColor=_CINZA_CARD)

    font_titulo = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    font_sub = Font(name="Calibri", size=10, italic=True, color="E2E8F0")
    font_secao = Font(name="Calibri", size=11, bold=True, color=_AZUL_CORP)
    font_label = Font(name="Calibri", size=10, bold=True, color=_TEXTO)
    font_valor = Font(name="Calibri", size=10, color=_TEXTO)

    # Banner institucional
    ws.merge_cells("A1:D1")
    ws["A1"] = "LAUDOTECH · IST AMBIENTAL"
    ws["A1"].font = font_titulo
    ws["A1"].fill = fill_azul
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:D2")
    ws["A2"] = "Instituto SENAI de Tecnologia Ambiental — Blumenau/SC · Planilha de Conferência Técnica e Parecer"
    ws["A2"].font = font_sub
    ws["A2"].fill = fill_azul
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20

    # Bloco 1: Identificação da Amostra
    ws["A4"] = "1. Identificação da Amostra"
    ws["A4"].font = font_secao
    ws.row_dimensions[4].height = 22

    concl_txt = amostra.data_conclusao.strftime("%d/%m/%Y") if amostra.data_conclusao else "Não informada"
    metadados = [
        ("Código da Amostra", amostra.codigo, "Data da Coleta", amostra.data_coleta.strftime("%d/%m/%Y")),
        ("Cliente", amostra.cliente, "Data de Conclusão", concl_txt),
        ("Proposta Comercial", amostra.proposta, "Origem da Amostra", amostra.origem),
        ("Local de Coleta", amostra.local_coleta, "Emissão da Planilha", date.today().strftime("%d/%m/%Y")),
        ("Normas Aplicadas", amostra.normas_resumo or "—", "Total de Ensaios", len(amostra.ensaios)),
    ]

    for offset, (k1, v1, k2, v2) in enumerate(metadados, start=5):
        ws.row_dimensions[offset].height = 20
        for col, (val, is_label) in enumerate([(k1, True), (v1, False), (k2, True), (v2, False)], start=1):
            cell = ws.cell(row=offset, column=col, value=val)
            cell.font = font_label if is_label else font_valor
            cell.fill = fill_label if is_label else fill_card
            cell.border = borda
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # Bloco 2: Diagnóstico Consolidado
    resumo = resumir_diagnostico_amostra(amostra)
    qtd_conf = sum(1 for e in amostra.ensaios if e.status == STATUS_CONFORME)
    qtd_desv = sum(1 for e in amostra.ensaios if e.estatistica and e.estatistica.alerta_desvio)
    qtd_unid = sum(
        1 for e in amostra.ensaios if any(av.motivo == "UNIDADE_DIVERGENTE" for av in e.avaliacoes.values())
    )

    ws["A11"] = "2. Diagnóstico Consolidado"
    ws["A11"].font = font_secao
    ws.row_dimensions[11].height = 22

    indicadores = [
        ("Ensaios Conformes", qtd_conf, "Ensaios Não Conformes", resumo.qtd_nao_conformes),
        ("Ensaios Pendentes", resumo.qtd_pendentes, "Alertas de Desvio Histórico", qtd_desv),
        ("Divergências de Unidade (RN-05)", qtd_unid, "Registros de Auditoria (RN-10)", len(amostra.logs)),
    ]
    for offset, (k1, v1, k2, v2) in enumerate(indicadores, start=12):
        ws.row_dimensions[offset].height = 20
        for col, (val, is_label) in enumerate([(k1, True), (v1, False), (k2, True), (v2, False)], start=1):
            cell = ws.cell(row=offset, column=col, value=val)
            cell.font = font_label if is_label else Font(name="Calibri", size=10, bold=True, color=_TEXTO)
            cell.fill = fill_label if is_label else fill_card
            cell.border = borda
            cell.alignment = Alignment(
                horizontal="left" if is_label else "center",
                vertical="center",
            )

    # Bloco 3: Conclusão e Minuta do Parecer
    ws["A16"] = "3. Conclusão da Amostra (Parecer Técnico)"
    ws["A16"].font = font_secao
    ws.row_dimensions[16].height = 22

    ws.merge_cells("A17:D17")
    fill_st, font_st = _estilo_status(amostra.status_geral)
    ws["A17"] = f"PARECER GERAL: {amostra.status_geral.upper()}"
    ws["A17"].fill = fill_st
    ws["A17"].font = font_st
    ws["A17"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for c in range(1, 5):
        ws.cell(row=17, column=c).border = borda
    ws.row_dimensions[17].height = 24

    ws.merge_cells("A18:D20")
    ws["A18"] = amostra.parecer or "Sem parecer registrado."
    ws["A18"].font = Font(name="Calibri", size=10.5, color=_TEXTO)
    ws["A18"].fill = fill_card
    ws["A18"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    for r in range(18, 21):
        ws.row_dimensions[r].height = 22
        for c in range(1, 5):
            ws.cell(row=r, column=c).border = borda

    # Larguras fixas elegantes para a aba Resumo
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 44
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 30


def _montar_aba_resultados(wb: Workbook, amostra: Amostra) -> None:
    ws = wb.create_sheet(title="Resultados e Conformidade")
    borda = _borda_fina()

    fill_hdr = PatternFill("solid", fgColor=_AZUL_CORP)
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_base = Font(name="Calibri", size=10, color=_TEXTO)
    font_red_bold = Font(name="Calibri", size=10, bold=True, color=_VERMELHO_TXT)
    fill_nc = PatternFill("solid", fgColor=_VERMELHO_LINHA)
    fill_pend = PatternFill("solid", fgColor=_AMBAR_LINHA)

    colunas = ["Cód.", "Ensaio", "Resultado Bruto", "Unid. Acreditada"]
    for norma in amostra.normas:
        colunas.append(f"VMP ({norma.titulo_coluna})")
        colunas.append(f"Veredito ({norma.titulo_coluna})")
    colunas.extend(["Status Consolidado", "Sinalização", "Média Hist. (μ)", "Desvio (σ)", "Observação"])

    ws.row_dimensions[1].height = 26
    for idx, titulo in enumerate(colunas, start=1):
        cell = ws.cell(row=1, column=idx, value=titulo)
        cell.font = font_hdr
        cell.fill = fill_hdr
        cell.border = borda
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, ensaio in enumerate(amostra.ensaios, start=2):
        ws.row_dimensions[row_idx].height = 21
        media_txt = (
            formatar_numero_br(ensaio.estatistica.media, 3)
            if ensaio.estatistica and ensaio.estatistica.media is not None
            else "—"
        )
        sigma_txt = (
            formatar_numero_br(ensaio.estatistica.desvio_padrao, 3)
            if ensaio.estatistica and ensaio.estatistica.desvio_padrao is not None
            else "—"
        )

        # Preserva valor_bruto original e unidade acreditada sem conversão implícita (RNF-02)
        valores: list[object] = [
            ensaio.codigo,
            ensaio.nome,
            ensaio.valor_bruto,
            ensaio.unidade_trabalho or "—",
        ]
        for norma in amostra.normas:
            av = ensaio.avaliacoes.get(norma.id)
            if av:
                valores.append(av.vmp_texto)
                valores.append(_rotulo_veredito(av.conformidade))
            else:
                valores.append("—")
                valores.append("—")

        valores.extend(
            [
                ensaio.status,
                ensaio.sinalizacao or "—",
                media_txt,
                sigma_txt,
                ensaio.observacao or "—",
            ]
        )

        row_fill = fill_nc if ensaio.status == STATUS_NAO_CONFORME else (
            fill_pend if ensaio.status == STATUS_PENDENTE else None
        )
        col_status_idx = 4 + 2 * len(amostra.normas) + 1

        for col_idx, val in enumerate(valores, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = borda
            cell.font = font_base
            if row_fill is not None:
                cell.fill = row_fill

            if col_idx == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 3:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if ensaio.status == STATUS_NAO_CONFORME:
                    cell.font = font_red_bold
            elif col_idx == col_status_idx:
                st_fill, st_font = _estilo_status(ensaio.status)
                cell.fill = st_fill
                cell.font = st_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in (4, col_status_idx + 1, col_status_idx + 2, col_status_idx + 3):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif 4 < col_idx < col_status_idx:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if val in (STATUS_CONFORME, STATUS_NAO_CONFORME, STATUS_PENDENTE):
                    v_fill, v_font = _estilo_status(str(val))
                    cell.fill = v_fill
                    cell.font = v_font
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(colunas))}{max(1, len(amostra.ensaios) + 1)}"
    _auto_ajustar_larguras(ws, largura_min=11, largura_max=42)


def _montar_aba_historico(wb: Workbook, amostra: Amostra) -> None:
    ws = wb.create_sheet(title="Historico_RN10")
    borda = _borda_fina()

    fill_hdr = PatternFill("solid", fgColor=_CINZA_CAB)
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_base = Font(name="Calibri", size=10, color=_TEXTO)
    font_muted = Font(name="Calibri", size=10, italic=True, color=_MUTED)

    colunas = [
        "Data / Hora",
        "Usuário",
        "Campo Alterado",
        "Escopo / Ensaio",
        "Valor Anterior",
        "Valor Novo",
        "Observação",
    ]
    ws.row_dimensions[1].height = 24
    for idx, titulo in enumerate(colunas, start=1):
        cell = ws.cell(row=1, column=idx, value=titulo)
        cell.font = font_hdr
        cell.fill = fill_hdr
        cell.border = borda
        cell.alignment = Alignment(horizontal="center", vertical="center")

    if not amostra.logs:
        ws.merge_cells("A2:G2")
        ws["A2"] = "Nenhuma alteração manual registrada para esta amostra."
        ws["A2"].font = font_muted
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
        for c in range(1, 8):
            ws.cell(row=2, column=c).border = borda
        ws.row_dimensions[2].height = 20
    else:
        for row_idx, lg in enumerate(amostra.logs, start=2):
            ws.row_dimensions[row_idx].height = 22
            escopo = (
                f"Ensaio {lg.ensaio_codigo} — {lg.ensaio_nome}"
                if lg.ensaio_codigo is not None
                else ("Parecer Geral" if lg.campo_alterado == "parecer_geral" else "Minuta do Parecer")
            )
            vals = [
                lg.data_alteracao.strftime("%d/%m/%Y %H:%M"),
                lg.usuario,
                lg.campo_alterado,
                escopo,
                lg.valor_anterior,
                lg.valor_novo,
                lg.observacao or "—",
            ]
            for col_idx, val in enumerate(vals, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = font_base
                cell.border = borda
                cell.alignment = Alignment(
                    horizontal="center" if col_idx in (1, 2, 3) else "left",
                    vertical="center",
                    wrap_text=True,
                )

    ws.freeze_panes = "A2"
    _auto_ajustar_larguras(ws, largura_min=14, largura_max=48)


def gerar_xlsx_amostra(amostra: Amostra) -> bytes:
    """
    Gera planilha XLSX oficial de conferência da amostra (RF-07 / RNF-02) contendo:
      - Aba 1: 'Resumo e Parecer'
      - Aba 2: 'Resultados e Conformidade'
      - Aba 3: 'Historico_RN10'
    """
    wb = Workbook()
    _montar_aba_resumo(wb, amostra)
    _montar_aba_resultados(wb, amostra)
    _montar_aba_historico(wb, amostra)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
