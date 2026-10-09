"""
Gerador de relatório e parecer técnico em PDF utilizando ReportLab.
"""

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


def gerar_pdf_amostra(amostra: dict, legislacoes_info: list, linhas: list, minuta_texto: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    titulo_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1C2B33"),
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5E6E76"),
    )
    secao_style = ParagraphStyle(
        "Secao",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1C2B33"),
        spaceBefore=8,
        spaceAfter=4,
    )
    normal_style = ParagraphStyle(
        "NormalText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1C2B33"),
    )
    minuta_style = ParagraphStyle(
        "MinutaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1C2B33"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1C2B33"),
    )
    cell_muted = ParagraphStyle(
        "CellMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#5E6E76"),
    )

    story = []

    # 1. Cabeçalho Institucional
    story.append(Paragraph("LAUDOTECH · IST AMBIENTAL", titulo_style))
    story.append(Paragraph("Instituto SENAI de Tecnologia Ambiental — Blumenau / SC", sub_style))
    story.append(Paragraph("Parecer Técnico de Conformidade Analítica de Qualidade de Água", sub_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1C2B33"), spaceAfter=10))

    # 2. Dados Cadastrais da Amostra
    data_coleta_str = amostra.get("coleta", "")
    if isinstance(data_coleta_str, date):
        data_coleta_str = data_coleta_str.strftime("%d/%m/%Y")

    dados_cadastrais = [
        [
            Paragraph("<b>Identificação da Amostra:</b>", normal_style),
            Paragraph(f"Amostra {amostra.get('codigo', '—')}", normal_style),
            Paragraph("<b>Data da Coleta:</b>", normal_style),
            Paragraph(str(data_coleta_str), normal_style),
        ],
        [
            Paragraph("<b>Cliente:</b>", normal_style),
            Paragraph(amostra.get("cliente", "—"), normal_style),
            Paragraph("<b>Proposta Comercial:</b>", normal_style),
            Paragraph(amostra.get("proposta", "—"), normal_style),
        ],
        [
            Paragraph("<b>Ponto / Local de Coleta:</b>", normal_style),
            Paragraph(amostra.get("local", "—"), normal_style),
            Paragraph("<b>Data da Emissão:</b>", normal_style),
            Paragraph(date.today().strftime("%d/%m/%Y"), normal_style),
        ],
    ]

    t_info = Table(dados_cadastrais, colWidths=[4.2 * cm, 5.5 * cm, 3.8 * cm, 4.5 * cm])
    t_info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_info)
    story.append(Spacer(1, 0.4 * cm))

    # 3. Legislações Aplicadas
    story.append(Paragraph("Normas Legais e Regulamentares Vinculadas", secao_style))
    legs_text = "<br/>".join(
        f"• <b>{l.get('sigla', '')}</b> — {l.get('nome', '')} ({l.get('escopo', '')})"
        for l in legislacoes_info
    )
    story.append(Paragraph(legs_text, normal_style))
    story.append(Spacer(1, 0.4 * cm))

    # 4. Tabela de Ensaios
    story.append(Paragraph("Resultados Analíticos e Avaliação de Conformidade", secao_style))

    # Monta cabeçalho da tabela dinâmico com base nas legislações
    header_row = ["Cód.", "Ensaio", "Resultado"]
    for l in legislacoes_info:
        header_row.append(f"VMP ({l.get('sigla', '')})")
    header_row.extend(["Conformidade", "Observação"])

    largura_base = [1.2 * cm, 4.0 * cm, 2.5 * cm]
    largura_legs = [2.6 * cm] * len(legislacoes_info)
    largura_fim = [2.4 * cm, 5.3 * cm]
    col_widths = largura_base + largura_legs + largura_fim

    table_data = [header_row]

    for item in linhas:
        row = [
            str(item.get("codigo", "")),
            item.get("ensaio", ""),
            item.get("resultado", ""),
        ]
        for l in legislacoes_info:
            sigla = l.get("id", "")
            info_vmp = item.get("por_leg", {}).get(sigla, ("—", True))
            row.append(str(info_vmp[0]))
        row.append(item.get("status", "Pendente"))
        row.append(item.get("observacao", "") or "—")
        table_data.append(row)

    # Estilos da tabela analítica
    t_ensaios = Table(table_data, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1C2B33")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE1")),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ]

    # Cores de linhas por status
    for i, item in enumerate(linhas, start=1):
        st = item.get("status", "")
        if st == "Não conforme":
            ts.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FDF2F2")))
            ts.append(("TEXTCOLOR", (-2, i), (-2, i), colors.HexColor("#A3271F")))
            ts.append(("FONTNAME", (-2, i), (-2, i), "Helvetica-Bold"))
        elif st == "Pendente":
            ts.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFFBEB")))
            ts.append(("TEXTCOLOR", (-2, i), (-2, i), colors.HexColor("#B45309")))
            ts.append(("FONTNAME", (-2, i), (-2, i), "Helvetica-Bold"))
        else:
            ts.append(("TEXTCOLOR", (-2, i), (-2, i), colors.HexColor("#15803D")))

    t_ensaios.setStyle(TableStyle(ts))
    story.append(t_ensaios)
    story.append(Spacer(1, 0.5 * cm))

    # 5. Minuta / Parecer Técnico do Responsável
    story.append(Paragraph("Minuta do Parecer Técnico / Conclusão do Analista", secao_style))
    texto_minuta = (
        minuta_texto.strip()
        if minuta_texto and minuta_texto.strip()
        else "Nenhum parecer técnico foi registrado previamente para esta amostra."
    )
    # Formata quebras de linha
    texto_formatado = texto_minuta.replace("\n", "<br/>")

    t_minuta = Table(
        [[Paragraph(texto_formatado, minuta_style)]],
        colWidths=[sum(col_widths)],
    )
    t_minuta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(t_minuta)
    story.append(Spacer(1, 0.8 * cm))

    # 6. Assinatura do Responsável Técnico
    story.append(
        KeepTogether(
            [
                Table(
                    [
                        [
                            Paragraph("___________________________________________________", sub_style),
                            Paragraph("___________________________________________________", sub_style),
                        ],
                        [
                            Paragraph("<b>Responsável Técnico pela Análise</b><br/>IST Ambiental", sub_style),
                            Paragraph("<b>Responsabilidade Técnica Geral / RT</b><br/>CRQ / CRBio Habilitado", sub_style),
                        ],
                    ],
                    colWidths=[9 * cm, 9 * cm],
                )
            ]
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
