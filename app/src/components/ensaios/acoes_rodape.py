"""
Componente Ações de Rodapé — LaudoTech
Renderiza o botão 'Voltar' à esquerda, e à direita os botões de exportação (PDF/XLSX)
e o botão principal 'Salvar' (conforme o esboço de design).
"""

import io
import pandas as pd
import streamlit as st
from data.mock_data import LEGISLACOES
from app.src.services.relatorio_pdf import gerar_pdf_amostra


def gerar_xlsx_amostra(amostra: dict, linhas: list, legislacoes: list, minuta_texto: str) -> bytes:
    """Gera planilha XLSX formatada com os dados de ensaios e a minuta."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        dados = []
        for l in linhas:
            item = {
                "Código Ensaio": l["codigo"],
                "Ensaio": l["ensaio"],
                "Resultado Medido": l["resultado"],
            }
            for leg in legislacoes:
                sigla = LEGISLACOES.get(leg, {}).get("sigla", leg)
                vmp, v = l["por_leg"].get(leg, ("—", True))
                item[f"VMP ({sigla})"] = vmp
            item["Status"] = l["status"]
            item["Observações / Ações"] = l["observacao"]
            dados.append(item)

        df = pd.DataFrame(dados)
        df.to_excel(writer, sheet_name="Ensaios", index=False)

        # Aba de metadados e parecer
        df_meta = pd.DataFrame([
            {"Campo": "Amostra", "Valor": amostra.get("codigo", "")},
            {"Campo": "Cliente", "Valor": amostra.get("cliente", "")},
            {"Campo": "Proposta", "Valor": amostra.get("proposta", "")},
            {"Campo": "Local de Coleta", "Valor": amostra.get("local", "")},
            {"Campo": "Data de Coleta", "Valor": amostra.get("coleta", "")},
            {"Campo": "Minuta Técnica / Parecer", "Valor": minuta_texto},
        ])
        df_meta.to_excel(writer, sheet_name="Parecer Técnico", index=False)

    return buffer.getvalue()


def renderizar_acoes_rodape(
    amostra: dict,
    legislacoes: list,
    linhas_atualizadas: list,
    minuta_texto: str,
    on_voltar_callback,
    on_salvar_callback,
    rotulo_salvar: str = "Salvar",
):
    """
    Renderiza o rodapé com ações de navegação à esquerda e ações de exportação e salvamento à direita.
    """
    st.divider()

    col_esq, col_espaco, col_pdf, col_xlsx, col_salvar = st.columns([3, 1, 2, 2, 2], vertical_alignment="center")

    with col_esq:
        if st.button("Voltar para lista de amostras", icon=":material/arrow_back:"):
            on_voltar_callback()

    cod_amostra = amostra.get("codigo", "padrao").replace("/", "_")
    legs_info = [LEGISLACOES[l] for l in legislacoes if l in LEGISLACOES]

    with col_pdf:
        pdf_bytes = gerar_pdf_amostra(
            amostra=amostra,
            legislacoes_info=legs_info,
            linhas=linhas_atualizadas,
            minuta_texto=minuta_texto,
        )
        st.download_button(
            label="Exportar PDF",
            data=pdf_bytes,
            file_name=f"Parecer_Tecnico_{cod_amostra}.pdf",
            mime="application/pdf",
            key=f"btn_pdf_export_{cod_amostra}",
            icon=":material/picture_as_pdf:",
            use_container_width=True,
        )

    with col_xlsx:
        xlsx_bytes = gerar_xlsx_amostra(
            amostra=amostra,
            linhas=linhas_atualizadas,
            legislacoes=legislacoes,
            minuta_texto=minuta_texto,
        )
        st.download_button(
            label="Exportar XLSX",
            data=xlsx_bytes,
            file_name=f"Revisao_{cod_amostra}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"btn_xlsx_export_{cod_amostra}",
            icon=":material/table_view:",
            use_container_width=True,
        )

    with col_salvar:
        if st.button(rotulo_salvar, type="primary", icon=":material/save:", use_container_width=True):
            on_salvar_callback()
