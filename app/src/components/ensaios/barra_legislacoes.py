"""
Componente Barra de Legislações e Métricas — LaudoTech
Renderiza o cabeçalho de contexto da amostra, as legislações aplicadas
(conforme o esboço) e badges de resumo de conformidade.
"""

import streamlit as st
from data.mock_data import LEGISLACOES


def renderizar_barra_legislacoes(amostra: dict, legislacoes: list, resumo_info: dict):
    """
    Exibe a linha com o resumo de conformidade à esquerda e as
    Legislações aplicadas à direita, utilizando componentes nativos do Streamlit.
    """
    col_info_esq, col_legs_dir = st.columns([1, 1], vertical_alignment="center")

    with col_info_esq:
        # Pílulas ou indicadores rápidos de conformidade
        c_conf = resumo_info.get("Conforme", 0)
        c_nc = resumo_info.get("Não conforme", 0)
        c_pend = resumo_info.get("Pendente", 0)

        st.markdown(
            f"""
            <div style="display: flex; gap: 8px; align-items: center; font-size: 0.82rem; margin: 4px 0 8px 0;">
                <span style="background-color: #F0FDF4; color: #166534; padding: 3px 8px; border-radius: 6px; font-weight: 600; border: 1px solid #BBF7D0;">
                    ✓ {c_conf} Conformes
                </span>
                <span style="background-color: {'#FEF2F2' if c_nc > 0 else '#F8FAFC'}; color: {'#991B1B' if c_nc > 0 else '#64748B'}; padding: 3px 8px; border-radius: 6px; font-weight: 600; border: 1px solid {'#FECACA' if c_nc > 0 else '#E2E8F0'};">
                    ✕ {c_nc} Não conformes
                </span>
                <span style="background-color: {'#FFFBEB' if c_pend > 0 else '#F8FAFC'}; color: {'#92400E' if c_pend > 0 else '#64748B'}; padding: 3px 8px; border-radius: 6px; font-weight: 600; border: 1px solid {'#FDE68A' if c_pend > 0 else '#E2E8F0'};">
                    ⏳ {c_pend} Pendentes
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_legs_dir:
        # Legislações aplicadas: l1, l2, l3 (conforme esboço)
        siglas = [LEGISLACOES.get(l, {}).get("sigla", l) for l in legislacoes if l in LEGISLACOES]
        siglas_texto = ", ".join(siglas) if siglas else "Nenhuma selecionada"

        st.markdown(
            f"""
            <div style="text-align: right; font-size: 0.85rem; color: #334155; margin: 4px 0 8px 0;">
                <span style="color: #64748B; font-weight: 500;">Legislações aplicadas:</span>
                <strong style="color: #0F172A; margin-left: 4px;">{siglas_texto}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
