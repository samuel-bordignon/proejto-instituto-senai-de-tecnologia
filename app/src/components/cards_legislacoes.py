"""
Componente de destaque para exibição das legislações aplicadas em cards horizontais.
"""

import streamlit as st
from data.mock_data import LEGISLACOES


def renderizar_cards_legislacoes(legislacoes_ids: list):
    if not legislacoes_ids:
        return

    cols = st.columns(len(legislacoes_ids))
    for col, leg_id in zip(cols, legislacoes_ids):
        info = LEGISLACOES.get(leg_id, {"sigla": leg_id, "nome": leg_id, "tipo": "Norma", "escopo": "Geral"})
        with col:
            st.markdown(
                f"""
                <div style="
                    background: #white;
                    border-radius: 6px;
                    border: solid 1px;
                    padding: 10px 14px;
                    margin-bottom: 8px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                    </div>
                    <div style="font-size: 0.78rem; font-weight: 500; color: #334155; line-height: 1.25; margin-bottom: 3px;">
                        {info['nome']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
