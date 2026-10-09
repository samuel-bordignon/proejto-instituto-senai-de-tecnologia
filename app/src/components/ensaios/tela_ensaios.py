import streamlit as st
from data.motor_conformidade import linhas_resultado, resumo
from app.src.components.ensaios.cabecalho_minuta import renderizar_cabecalho_minuta
from app.src.components.ensaios.barra_legislacoes import renderizar_barra_legislacoes
from app.src.components.ensaios.tabela_ensaios import renderizar_tabela_ensaios
from app.src.components.ensaios.acoes_rodape import renderizar_acoes_rodape


def renderizar_tela_ensaios(
    legislacoes: list,
    lote: list,
    on_nova_amostra_callback,
    on_voltar_callback,
    on_salvar_callback,
):
    if not lote:
        st.info("Nenhuma amostra ativa para exibição de ensaios. Selecione uma amostra na lista ou envie um novo lote CSV.")
        if st.button("Voltar para lista de amostras", icon=":material/arrow_back:"):
            on_voltar_callback()
        return

    # Índice da amostra ativa para a minuta técnica no topo
    if "idx_amostra_minuta" not in st.session_state:
        st.session_state.idx_amostra_minuta = 0

    if st.session_state.idx_amostra_minuta >= len(lote):
        st.session_state.idx_amostra_minuta = 0

    amostra_topo = lote[st.session_state.idx_amostra_minuta]

    # 1. Topo: Título, Adicionar Amostra e Minuta Técnica com botão Gerar com IA
    minuta_texto = renderizar_cabecalho_minuta(
        amostra=amostra_topo,
        on_nova_amostra_callback=on_nova_amostra_callback,
    )

    st.write("")

    # 2. Abas por amostra do lote (Amostra 1, Amostra 2, Amostra 3...)
    rotulos_abas = [f"Amostra {index} ({amostra.get('codigo', '')})" for index, amostra in enumerate(lote, start=1)]
    abas = st.tabs(rotulos_abas)

    editores_data = {}
    linhas_por_amostra = {}

    for idx, (aba, a) in enumerate(zip(abas, lote), start=1):
        cod_amostra = a.get("codigo", f"AMO-{idx}")

        with aba:
            linhas = linhas_resultado(a, legislacoes)
            r = resumo(linhas)
            linhas_por_amostra[cod_amostra] = linhas

            # 3. Barra com Legislações aplicadas à direita e métricas de conferência à esquerda
            renderizar_barra_legislacoes(
                amostra=a,
                legislacoes=legislacoes,
                resumo_info=r,
            )

            # 4. Tabela de ensaios com colunas: nome | valor_bruto | p1 | p2 | p3 | status | ações
            df_editado = renderizar_tabela_ensaios(
                amostra=a,
                legislacoes=legislacoes,
                linhas=linhas,
                key_prefix=cod_amostra,
            )
            editores_data[cod_amostra] = df_editado

    # Prepara as linhas atualizadas da amostra em foco para exportação de PDF / XLSX
    cod_foco = amostra_topo.get("codigo", "")
    linhas_foco = linhas_por_amostra.get(cod_foco, [])
    df_foco = editores_data.get(cod_foco)

    linhas_atualizadas_foco = []
    if df_foco is not None:
        for row in df_foco.itertuples():
            l_orig = next((item for item in linhas_foco if item["codigo"] == int(row.codigo)), {})
            linhas_atualizadas_foco.append({
                "codigo": row.codigo,
                "ensaio": row.nome,
                "resultado": row.valor_bruto,
                "unidade": l_orig.get("unidade", ""),
                "por_leg": l_orig.get("por_leg", {}),
                "status": row.status,
                "observacao": getattr(row, "acoes", "") or "",
            })
    else:
        linhas_atualizadas_foco = linhas_foco

    # Callback para persistir alterações ao clicar no botão Salvar
    def executar_salvamento():
        lote_salvo = []
        for a in lote:
            cod = a.get("codigo")
            df_amostra = editores_data.get(cod)
            minuta_final = st.session_state.get(f"text_minuta_{cod}", a.get("minuta", ""))

            if df_amostra is not None:
                nova_revisao = {}
                for row in df_amostra.itertuples():
                    nova_revisao[int(row.codigo)] = (row.status, getattr(row, "acoes", "") or "")
                revisada = not (df_amostra["status"] == "Pendente").any()
                a_atualizada = dict(a)
                a_atualizada["revisao"] = nova_revisao
                a_atualizada["revisada"] = revisada
                a_atualizada["minuta"] = minuta_final
                lote_salvo.append(a_atualizada)
            else:
                lote_salvo.append(a)

        on_salvar_callback(lote_salvo)
        st.toast("Alterações e parecer técnico salvos com sucesso!")
        st.rerun()

    # 5. Rodapé: Voltar, Exportar PDF, Exportar XLSX e Salvar
    rotulo_salvar = "Salvar" if len(lote) == 1 else f"Salvar ({len(lote)} amostras)"
    renderizar_acoes_rodape(
        amostra=amostra_topo,
        legislacoes=legislacoes,
        linhas_atualizadas=linhas_atualizadas_foco,
        minuta_texto=minuta_texto,
        on_voltar_callback=on_voltar_callback,
        on_salvar_callback=executar_salvamento,
        rotulo_salvar=rotulo_salvar,
    )
