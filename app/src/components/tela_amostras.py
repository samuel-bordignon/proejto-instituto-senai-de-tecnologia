"""
Tela de Amostras do Local — Apresentação tabular nativa com botão de abertura rápida.
"""

import pandas as pd
import streamlit as st
from data.mock_data import LEGISLACOES
from data.motor_conformidade import linhas_resultado, resumo


def renderizar_tela_amostras(
    cliente: str,
    proposta: str,
    local: str,
    legislacoes: list,
    amostras: list,
    on_nova_amostra_callback,
    on_abrir_ensaios_callback,
):
    # Topo: Identificação do Local e Botão de Ação
    topo_esq, topo_dir = st.columns([3, 1], vertical_alignment="bottom")
    with topo_esq:
        st.markdown(
            f"""
            <div style="margin-bottom: 2px;">
                <h2 style="font-size: 1.35rem; font-weight: 700; color: #0F172A; margin: 0; line-height: 1.2;">
                    {local}
                </h2>
                <p style="font-size: 0.82rem; color: #64748B; margin: 2px 0 0 0;">
                    {cliente} · {proposta}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with topo_dir:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Nova amostra", type="primary", icon=":material/add:"):
                on_nova_amostra_callback()

    # Legislações vinculadas
    nomes_leg = ", ".join(f"{LEGISLACOES[l]['sigla']} ({LEGISLACOES[l]['nome']})" for l in legislacoes if l in LEGISLACOES)
    st.markdown(
        f"""
        <div style="font-size: 0.8rem; color: #334155; margin: 8px 0 16px 0;">
            <span style="font-weight: 600; color: #64748B; text-transform: uppercase; font-size: 0.72rem; margin-right: 4px;">
                Legislações aplicadas:
            </span>
            {nomes_leg}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not amostras:
        st.info("Nenhuma amostra registrada para este ponto de coleta. Use o botão 'Nova amostra' acima para enviar o arquivo CSV do UltraLIMS.")
        return

    # Monta DataFrame das Amostras
    linhas_tabela = []
    for idx, a in enumerate(amostras, start=1):
        res = linhas_resultado(a, legislacoes)
        r = resumo(res)

        if r["Não conforme"] > 0:
            st_geral = "Não conforme"
        elif r["Pendente"] > 0 or not a.get("revisada", False):
            st_geral = "Pendente"
        else:
            st_geral = "Conforme"

        data_formatada = a.get("coleta", "")
        if hasattr(data_formatada, "strftime"):
            data_formatada = data_formatada.strftime("%d/%m/%Y")
        elif isinstance(data_formatada, str) and "-" in data_formatada:
            partes = data_formatada.split("-")
            if len(partes) == 3:
                data_formatada = f"{partes[2]}/{partes[1]}/{partes[0]}"

        linhas_tabela.append({
            "_indice": idx - 1,
            "Amostra": f"Amostra {idx} ({a.get('codigo', '')})",
            "Data da Coleta": str(data_formatada),
            "Total Ensaios": len(res),
            "Não Conformes": r["Não conforme"],
            "Pendentes": r["Pendente"],
            "Status Geral": st_geral,
            "Abrir": ":material/open_in_new:",
        })

    df = pd.DataFrame(linhas_tabela)

    # Estilização visual de cores para status
    def colorir_status(val):
        if val == "Não conforme":
            return "background-color: #FDF2F2; color: #991B1B; font-weight: 600;"
        elif val == "Pendente":
            return "background-color: #FFFBEB; color: #92400E; font-weight: 600;"
        elif val == "Conforme":
            return "background-color: #F0FDF4; color: #166534; font-weight: 600;"
        return ""

    def colorir_nc(val):
        if isinstance(val, int) and val > 0:
            return "color: #DC2626; font-weight: 600;"
        return "color: #94A3B8;"

    styled_df = (
        df.drop(columns=["_indice"])
        .style.map(colorir_status, subset=["Status Geral"])
        .map(colorir_nc, subset=["Não Conformes"])
    )

    # Callback ao clicar no botão 'Abrir'
    def on_click_abrir():
        click_state = st.session_state.get("btn_click_abrir_amostra")
        if click_state is not None and "row" in click_state:
            linha_idx = click_state["row"]
            if 0 <= linha_idx < len(amostras):
                on_abrir_ensaios_callback(amostras[linha_idx])

    # Renderiza tabela nativa st.dataframe
    selecao = st.dataframe(
        styled_df,
        column_config={
            "Amostra": st.column_config.TextColumn("Amostra", width="medium"),
            "Data da Coleta": st.column_config.TextColumn("Data da Coleta", width="small"),
            "Total Ensaios": st.column_config.NumberColumn("Ensaios", format="%d", width="small"),
            "Não Conformes": st.column_config.NumberColumn("Não Conformes", format="%d", width="small"),
            "Pendentes": st.column_config.NumberColumn("Pendentes", format="%d", width="small"),
            "Status Geral": st.column_config.TextColumn("Status", width="medium"),
            "Abrir": st.column_config.ButtonColumn(
                "Abrir",
                help="Abrir exibição dos ensaios desta amostra",
                width="small",
                type="tertiary",
                on_click=on_click_abrir,
                key="btn_click_abrir_amostra",
            ),
        },
        hide_index=True,
        width="stretch",
        selection_mode="single-row",
        on_select="rerun",
        key="tabela_amostras_df",
    )

    # Suporte a seleção de linha alternativa
    if selecao and selecao.selection and selecao.selection.rows:
        linha_selecionada = selecao.selection.rows[0]
        if 0 <= linha_selecionada < len(amostras):
            on_abrir_ensaios_callback(amostras[linha_selecionada])
