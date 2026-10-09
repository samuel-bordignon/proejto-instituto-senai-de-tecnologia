"""
Componente de barra lateral com filtros de contexto e roteamento principal.
"""

import streamlit as st
from data.mock_data import CLIENTES


def renderizar_sidebar(
    cliente_atual: str,
    proposta_atual: str,
    local_atual: str,
    tela_atual: str,
    on_cliente_change,
    on_proposta_change,
    on_local_change,
    on_navegar,
):
    with st.sidebar:
        st.markdown(
            """
            <div style="margin-bottom: 16px;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #0F172A; letter-spacing: -0.02em;">
                    LaudoTech
                </div>
                <div style="font-size: 0.8rem; font-weight: 500; color: #64748B; margin-top: -2px;">
                    IST Ambiental
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Seletores de Contexto
        cliente_sel = st.selectbox(
            "Cliente",
            list(CLIENTES.keys()),
            index=list(CLIENTES.keys()).index(cliente_atual) if cliente_atual in CLIENTES else 0,
            key="sb_cliente",
            on_change=on_cliente_change,
        )

        cliente_data = CLIENTES.get(cliente_sel, list(CLIENTES.values())[0])
        propostas_disponiveis = list(cliente_data.keys())
        idx_prop = propostas_disponiveis.index(proposta_atual) if proposta_atual in propostas_disponiveis else 0

        proposta_sel = st.selectbox(
            "Proposta Comercial",
            propostas_disponiveis,
            index=idx_prop,
            key="sb_proposta",
            format_func=lambda k: f"{k} ({cliente_data[k]['descricao']})",
            on_change=on_proposta_change,
        )

        proposta_data = cliente_data.get(proposta_sel, list(cliente_data.values())[0])
        locais_disponiveis = proposta_data["locais"]
        idx_loc = locais_disponiveis.index(local_atual) if local_atual in locais_disponiveis else 0

        local_sel = st.selectbox(
            "Local de Coleta",
            locais_disponiveis,
            index=idx_loc,
            key="sb_local",
            on_change=on_local_change,
        )

        st.divider()

        # Botões de navegação
        st.button(
            "Amostras do local",
            width="stretch",
            icon=":material/table_chart:",
            on_click=on_navegar,
            args=("amostras",),
            type="primary" if tela_atual == "amostras" else "secondary",
        )

        st.button(
            "Visualização de ensaios",
            width="stretch",
            icon=":material/analytics:",
            on_click=on_navegar,
            args=("ensaios",),
            type="primary" if tela_atual == "ensaios" else "secondary",
        )

    return cliente_sel, proposta_sel, local_sel
