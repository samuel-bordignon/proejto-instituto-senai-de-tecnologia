"""Gerador de relatório e parecer técnico em PDF (A4) com resultados, VMPs (1–3 normas) e histórico RN-10."""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    STATUS_CONFORME,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.models import Amostra


def gerar_pdf_amostra(amostra: Amostra) -> bytes:
    """Gera o PDF oficial de conferência da amostra, incluindo histórico de alterações (RN-10)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )
    largura_util = A4[0] - 2.8 * cm

    styles = getSampleStyleSheet()
    azul = colors.HexColor("#004B8D")
    preto = colors.HexColor("#111827")
    cinza = colors.HexColor("#52525B")
    borda = colors.HexColor("#E4E4E7")

    titulo_style = ParagraphStyle(
        "LTTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=azul,
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "LTSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=cinza,
    )
    secao_style = ParagraphStyle(
        "LTSecao",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13.5,
        textColor=preto,
        spaceBefore=10,
        spaceAfter=5,
    )
    normal_style = ParagraphStyle(
        "LTNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=preto,
    )
    cell_style = ParagraphStyle(
        "LTCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=preto,
    )
    cell_bold_red = ParagraphStyle(
        "LTCellRed",
        parent=cell_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#DC2626"),
    )
    header_cell = ParagraphStyle(
        "LTHeaderCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
    )

    story = []

    # 1. Cabeçalho Institucional
    story.append(Paragraph("LAUDOTECH · IST AMBIENTAL", titulo_style))
    story.append(Paragraph("Instituto SENAI de Tecnologia Ambiental — SENAI Blumenau / SC", sub_style))
    story.append(Paragraph("Relatório de Conferência Técnica e Parecer Analítico", sub_style))
    story.append(Spacer(1, 0.25 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=azul, spaceAfter=8))

    # 2. Dados Cadastrais da Amostra
    dados_cad = [
        [
            Paragraph("<b>Amostra:</b>", normal_style),
            Paragraph(amostra.codigo, normal_style),
            Paragraph("<b>Data da Coleta:</b>", normal_style),
            Paragraph(amostra.data_coleta.strftime("%d/%m/%Y"), normal_style),
        ],
        [
            Paragraph("<b>Cliente:</b>", normal_style),
            Paragraph(amostra.cliente, normal_style),
            Paragraph("<b>Proposta:</b>", normal_style),
            Paragraph(amostra.proposta, normal_style),
        ],
        [
            Paragraph("<b>Local de Coleta:</b>", normal_style),
            Paragraph(amostra.local_coleta, normal_style),
            Paragraph("<b>Origem da Amostra:</b>", normal_style),
            Paragraph(amostra.origem, normal_style),
        ],
        [
            Paragraph("<b>Normas Aplicadas:</b>", normal_style),
            Paragraph(amostra.normas_resumo, normal_style),
            Paragraph("<b>Emissão do Relatório:</b>", normal_style),
            Paragraph(date.today().strftime("%d/%m/%Y"), normal_style),
        ],
    ]
    t_info = Table(
        dados_cad,
        colWidths=[3.1 * cm, 6.1 * cm, 3.3 * cm, largura_util - 12.5 * cm],
    )
    t_info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("BOX", (0, 0), (-1, -1), 0.6, borda),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, borda),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t_info)

    # 3. Tabela Dinâmica de Ensaios (suporta 1, 2 ou 3 normas sem overflow)
    story.append(Paragraph("Resultados Analíticos e Avaliação de Conformidade", secao_style))

    n_normas = max(1, len(amostra.normas))
    w_cod = 1.1 * cm
    w_res = 2.2 * cm
    w_status = 2.1 * cm
    w_obs = 2.8 * cm if n_normas == 3 else 3.4 * cm
    w_norma = 2.15 * cm if n_normas == 3 else (2.6 * cm if n_normas == 2 else 3.4 * cm)
    w_ensaio = largura_util - (w_cod + w_res + w_status + w_obs + w_norma * len(amostra.normas))
    col_widths = [w_cod, w_ensaio, w_res] + [w_norma] * len(amostra.normas) + [w_status, w_obs]

    cabecalho = [
        Paragraph("Cód.", header_cell),
        Paragraph("Ensaio", header_cell),
        Paragraph("Resultado", header_cell),
    ]
    for norma in amostra.normas:
        cabecalho.append(Paragraph(norma.titulo_coluna, header_cell))
    cabecalho.extend([Paragraph("Status", header_cell), Paragraph("Observação", header_cell)])

    linhas_tabela = [cabecalho]
    for e in amostra.ensaios:
        estilo_res = cell_bold_red if e.status == STATUS_NAO_CONFORME else cell_style
        row = [
            Paragraph(str(e.codigo), cell_style),
            Paragraph(e.nome, cell_style),
            Paragraph(e.resultado_formatado, estilo_res),
        ]
        for norma in amostra.normas:
            av = e.avaliacoes.get(norma.id)
            row.append(Paragraph(av.vmp_texto if av else "—", cell_style))
        row.append(Paragraph(e.status, cell_style))
        obs_txt = e.observacao or (e.sinalizacao or "—")
        row.append(Paragraph(obs_txt, cell_style))
        linhas_tabela.append(row)

    t_ensaios = Table(linhas_tabela, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), azul),
        ("GRID", (0, 0), (-1, -1), 0.45, borda),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
    ]
    for idx, e in enumerate(amostra.ensaios, start=1):
        if e.status == STATUS_NAO_CONFORME:
            ts.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FEF2F2")))
            ts.append(("TEXTCOLOR", (-2, idx), (-2, idx), colors.HexColor("#DC2626")))
        elif e.status == STATUS_PENDENTE:
            ts.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FFFBEB")))
            ts.append(("TEXTCOLOR", (-2, idx), (-2, idx), colors.HexColor("#B45309")))
        elif e.status == STATUS_CONFORME:
            ts.append(("TEXTCOLOR", (-2, idx), (-2, idx), colors.HexColor("#15803D")))

    t_ensaios.setStyle(TableStyle(ts))
    story.append(t_ensaios)

    # 4. Conclusão / Parecer Técnico
    story.append(Paragraph("Conclusão da Amostra (Parecer Técnico)", secao_style))
    cor_geral = (
        "#16A34A"
        if amostra.status_geral == GERAL_FAVORAVEL
        else ("#DC2626" if amostra.status_geral == GERAL_NAO_FAVORAVEL else "#D97706")
    )
    bloco_parecer = (
        f"<font color='{cor_geral}'><b>PARECER: {amostra.status_geral.upper()}</b></font><br/><br/>"
        f"{(amostra.parecer or 'Sem parecer registrado.').replace(chr(10), '<br/>')}"
    )
    t_par = Table([[Paragraph(bloco_parecer, normal_style)]], colWidths=[largura_util])
    t_par.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                ("BOX", (0, 0), (-1, -1), 0.7, borda),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(t_par)

    # 5. Histórico de Alterações (RN-10 — exigido pela Seção 5.5 e 8.5)
    story.append(Paragraph("Histórico de Alterações (Auditoria RN-10)", secao_style))
    if amostra.logs:
        log_rows = [
            [
                Paragraph("Data / Hora", header_cell),
                Paragraph("Escopo", header_cell),
                Paragraph("Registro da Alteração", header_cell),
            ]
        ]
        for lg in amostra.logs:
            escopo = (
                f"Ensaio {lg.ensaio_codigo} — {lg.ensaio_nome}"
                if lg.ensaio_codigo is not None
                else ("Parecer Geral" if lg.campo_alterado == "parecer_geral" else "Texto do Parecer")
            )
            desc = f"{lg.usuario} alterou de <b>{lg.valor_anterior}</b> para <b>{lg.valor_novo}</b>"
            if lg.observacao:
                desc += f"<br/><font color='#52525B'>Obs.: {lg.observacao}</font>"
            log_rows.append(
                [
                    Paragraph(lg.data_alteracao.strftime("%d/%m/%Y %H:%M"), cell_style),
                    Paragraph(escopo, cell_style),
                    Paragraph(desc, cell_style),
                ]
            )
        t_logs = Table(log_rows, colWidths=[2.9 * cm, 4.3 * cm, largura_util - 7.2 * cm], repeatRows=1)
        t_logs.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#52525B")),
                    ("GRID", (0, 0), (-1, -1), 0.4, borda),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t_logs)
    else:
        story.append(Paragraph("Nenhuma alteração manual registrada para esta amostra.", sub_style))

    # 6. Assinatura
    story.append(Spacer(1, 0.9 * cm))
    story.append(
        KeepTogether(
            [
                Table(
                    [
                        [
                            Paragraph("______________________________________________", sub_style),
                            Paragraph("______________________________________________", sub_style),
                        ],
                        [
                            Paragraph("<b>Conferência Técnica</b><br/>IST Ambiental — SENAI Blumenau", sub_style),
                            Paragraph("<b>Liberação Técnica (PRL)</b><br/>Assinatura Digital ICP-BR", sub_style),
                        ],
                    ],
                    colWidths=[largura_util / 2, largura_util / 2],
                )
            ]
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
