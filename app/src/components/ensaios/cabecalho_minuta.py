import streamlit as st

def renderizar_cabecalho_minuta(
    amostra: dict,
    on_nova_amostra_callback,
) -> str:
    cod_amostra = amostra.get("codigo", "padrao")
    chave_texto = f"text_minuta_{cod_amostra}"

    # Inicializa no session_state se não existir
    if chave_texto not in st.session_state:
        st.session_state[chave_texto] = amostra.get("minuta", "")

    # Linha 1: Título da tela à esquerda e Botão 'Adicionar amostra' à direita
    col_titulo, col_btn_amostra = st.columns([5, 1], vertical_alignment="center")

    with col_titulo:
        st.markdown(
            """
            <div style="margin-bottom: 0.15rem;">
                <h2 style="font-size: 1.35rem; font-weight: 700; color: #0F172A; margin: 0; line-height: 1.2;">
                    Visualização de Ensaios
                </h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_btn_amostra:
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button("Adicionar amostra", type="secondary", icon=":material/add:"):
                on_nova_amostra_callback()

    # Linha 2: Campo de descrição / minuta 
    col_txt = st.container(vertical_alignment="bottom")

    with col_txt:
        minuta_digitada = st.text_area(
            "Descrição / Minuta Técnica:",
            key=chave_texto,
            height=90,
            placeholder="Elabore a descrição ou parecer técnico do responsável, ou clique ao lado para gerar com IA...",
            help="Texto técnico que integrará o relatório/parecer oficial em PDF.",
        )

    return st.session_state.get(chave_texto, minuta_digitada)
