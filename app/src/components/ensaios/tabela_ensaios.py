"""
Componente Tabela de Ensaios — LaudoTech
Renderiza a tabela de ensaios analíticos com colunas customizadas
(nome, valor_bruto, p1, p2, p3, status, ações), destaque por cores vivas
de conformidade e editor interativo via st.data_editor.
"""

import pandas as pd
import streamlit as st
from data.mock_data import LEGISLACOES, STATUS_OPCOES


def renderizar_tabela_ensaios(
    amostra: dict,
    legislacoes: list,
    linhas: list,
    key_prefix: str,
) -> pd.DataFrame:
    """
    Constrói e renderiza a tabela de ensaios com colunas de acordo com o esboço:
    nome | valor_bruto | p1 | p2 | p3 | status | ações
    Aplica cores aos status e limites violados.
    """

    # Monta lista de dados com as colunas do esboço
    dados_tabela = []
    for l in linhas:
        item = {
            "codigo": l["codigo"],
            "nome": l["ensaio"],
            "valor_bruto": l["resultado"],
        }
        for leg in legislacoes:
            vmp, v = l["por_leg"].get(leg, ("—", True))
            sigla = LEGISLACOES.get(leg, {}).get("sigla", leg)
            # Sinaliza violação textual se false
            if v is False:
                item[sigla] = f"{vmp} (Violação)"
            elif v is None:
                item[sigla] = f"{vmp} (Pendente)" if vmp != "—" else "—"
            else:
                item[sigla] = f"{vmp}"

        item["status"] = l["status"]
        item["acoes"] = l["observacao"]
        dados_tabela.append(item)

    df = pd.DataFrame(dados_tabela)

    # Funções de estilização por cores (alto contraste e acessibilidade)
    def style_status(val):
        if val == "Não conforme":
            return "background-color: #FEE2E2; color: #991B1B; font-weight: 700;"
        elif val == "Pendente":
            return "background-color: #FEF3C7; color: #92400E; font-weight: 700;"
        elif val == "Conforme":
            return "background-color: #ECFDF5; color: #065F46; font-weight: 600;"
        return ""

    def style_violacao(val):
        if isinstance(val, str) and "Violação" in val:
            return "background-color: #FEF2F2; color: #DC2626; font-weight: 700;"
        return "color: #334155;"

    def style_nome(val):
        return "font-weight: 600; color: #0F172A;"

    def style_valor(val):
        return "font-family: monospace; font-weight: 600; color: #1E293B;"

    # Aplica Styler
    styler = df.style.map(style_status, subset=["status"])
    styler = styler.map(style_nome, subset=["nome"])
    styler = styler.map(style_valor, subset=["valor_bruto"])

    colunas_legs_siglas = []
    for leg in legislacoes:
        sigla = LEGISLACOES.get(leg, {}).get("sigla", leg)
        colunas_legs_siglas.append(sigla)
        if sigla in df.columns:
            styler = styler.map(style_violacao, subset=[sigla])

    # Configuração de exibição das colunas no data_editor
    col_config = {
        "codigo": st.column_config.NumberColumn("Cód.", width="small", disabled=True),
        "nome": st.column_config.TextColumn("Nome", width="large", disabled=True),
        "valor_bruto": st.column_config.TextColumn("Valor Bruto", width="medium", disabled=True),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=STATUS_OPCOES,
            required=True,
            width="medium",
            help="Status técnico avaliado contra as legislações",
        ),
        "acoes": st.column_config.TextColumn(
            "Ações",
            width="large",
            help="Observações técnicas, ressalvas ou ações corretivas do analista",
        ),
    }

    for sigla in colunas_legs_siglas:
        col_config[sigla] = st.column_config.TextColumn(f"Limite {sigla}", width="medium", disabled=True)

    # Renderiza st.data_editor nativo
    altura = min(42 + 37 * len(df), 540)
    df_editado = st.data_editor(
        styler,
        key=f"editor_ensaios_{key_prefix}",
        hide_index=True,
        width="stretch",
        height=altura,
        column_config=col_config,
        disabled=[c for c in df.columns if c not in ("status", "acoes")],
    )

    return df_editado
