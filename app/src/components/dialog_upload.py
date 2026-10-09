"""
Diálogo modal para upload de lotes CSV/XLSX exportados do UltraLIMS.
"""

from datetime import date
import streamlit as st
from data.mock_data import V_ATENCAO, V_CRITICO, V_REGULAR, V_SUPERFICIAL, nova_amostra


def abrir_dialogo_upload(
    cliente: str,
    proposta: str,
    local: str,
    legislacoes: list,
    proximo_codigo: int,
    on_lote_processado_callback,
):
    @st.dialog("Nova amostra", width="small")
    def _dialogo():
        arquivo = st.file_uploader("Envie o arquivo CSV ou XLSX", type=["csv", "xlsx"])
        st.caption("O lote pode conter uma ou múltiplas amostras. Cada amostra será aberta em uma aba na visualização de ensaios.")

        def _carregar_lote(nome_origem: str):
            base = proximo_codigo
            is_superficial = "CONAMA357" in legislacoes
            modelos = [V_CRITICO, V_ATENCAO, V_REGULAR] if not is_superficial else [V_SUPERFICIAL] * 3

            novo_lote = [
                nova_amostra(cliente, proposta, local, f"{base + i}/2026", date.today(), modelos[i])
                for i in range(3)
            ]
            on_lote_processado_callback(novo_lote, nome_origem, base + 3)
            st.rerun()

        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Usar dados de exemplo (3 amostras)"):
                _carregar_lote("exemplo_ultralims_3_amostras.csv")

            if st.button("Processar lote", type="primary", disabled=arquivo is None):
                _carregar_lote(arquivo.name)

    _dialogo()
