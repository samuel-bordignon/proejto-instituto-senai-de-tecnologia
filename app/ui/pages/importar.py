"""Tela B3 — Importar Planilha UltraLIMS (/importar) com suporte multi-amostra em abas + Tabela Dinâmica por KPI."""

from __future__ import annotations

from urllib.parse import quote

from nicegui import app, events, ui

from app.core.models import ResultadoPreLeitura, ResultadoPreLeituraLote
from app.repo.demo_fixtures import gerar_lote_demonstracao
from app.repo.mock_repo import repo
from app.ui.components.badges import status_pill_html
from app.ui.layout import criar_shell, mostrar_toast_aviso, mostrar_toast_sucesso


_KPI_DEFINICOES = [
    ("mapeados", "Ensaios mapeados", "MAPEADOS", "#16A34A", "Encontrados no catálogo UltraLIMS"),
    ("sem_vmp", "Sem VMP na norma", "SEM VMP", "#71717A", "Armazenados sem avaliação legal"),
    ("ignorados", "Ignorados (RN-02)", "IGNORADOS", "#71717A", "Não analisados (______) e controle SVOC"),
    ("avisos", "Avisos de revisão", "ATENÇÃO", "#D97706", "Formatação, RN-01 e divergência de unidade"),
]


def registrar_pagina_importar() -> None:
    @ui.page("/importar")
    def pagina_importar() -> None:
        criar_shell(aba_ativa="importar")

        clientes = repo.listar_clientes()
        cliente_ini = clientes[0]
        propostas_ini = repo.listar_propostas(cliente_ini)
        proposta_ini = propostas_ini[0]
        locais_ini = repo.listar_locais(cliente_ini, proposta_ini)
        local_ini = locais_ini[0]
        origem_ini = "Efluente Tratado"

        estado: dict = {
            "lote": None,                 # ResultadoPreLeituraLote | None
            "amostra_ativa": None,        # codigo_amostra_principal da aba ativa
            "kpis_expandidos": {"avisos", "mapeados"},  # grupos expandidos na tabela dinâmica por KPI
            "kpi_foco": None,             # último KPI clicado no card
            "cliente": cliente_ini,
            "proposta": proposta_ini,
            "local": local_ini,
            "origem": origem_ini,
            "normas": [
                {"sigla": "CONAMA 430", "classe": "Sanitário (Art. 21)"},
                {"sigla": "CONAMA 430", "classe": "Sem Classe (Art. 16)"},
            ],
        }

        def _obter_amostra_ativa() -> ResultadoPreLeitura | None:
            lote: ResultadoPreLeituraLote | None = estado["lote"]
            if not lote or not lote.amostras:
                return None
            for am in lote.amostras:
                if am.codigo_amostra_principal == estado["amostra_ativa"]:
                    return am
            estado["amostra_ativa"] = lote.amostras[0].codigo_amostra_principal
            return lote.amostras[0]

        # =====================================================================
        # BARRA DE ABAS DAS AMOSTRAS LOGO ABAIXO DO HEADER (Requisito 2)
        # =====================================================================
        @ui.refreshable
        def render_barra_abas_amostras() -> None:
            lote: ResultadoPreLeituraLote | None = estado["lote"]
            if not lote or not lote.amostras:
                return

            with ui.row().classes(
                "lt-sample-tabs-bar items-center justify-between gap-[16px] flex-wrap"
            ):
                with ui.row().classes("items-center gap-[12px] no-wrap overflow-x-auto"):
                    ui.label("AMOSTRAS DO ARQUIVO").classes(
                        "text-[10px] font-bold tracking-[0.5px] text-[#71717A] shrink-0"
                    )
                    with ui.tabs(
                        value=estado["amostra_ativa"],
                        on_change=lambda e: _trocar_aba_amostra(str(e.value)),
                    ).props(
                        "dense align=left indicator-color=primary active-color=primary no-caps outside-arrows mobile-arrows"
                    ).classes("lt-sample-tabs"):
                        for am in lote.amostras:
                            cod = am.codigo_amostra_principal
                            cor_dot = "#D97706" if am.total_avisos > 0 else "#16A34A"
                            with ui.tab(name=cod, label=""):
                                with ui.row().classes("items-center gap-[7px] no-wrap"):
                                    ui.element("div").classes(
                                        "w-[7px] h-[7px] rounded-full shrink-0"
                                    ).style(f"background-color: {cor_dot};")
                                    ui.label(cod).classes("font-mono-lt text-[12px] font-bold")
                                    ui.label(f"({am.total_mapeados})").classes(
                                        "font-mono-lt text-[11px] font-normal text-[#71717A]"
                                    )

                ui.label(
                    f"{len(lote.amostras)} amostra(s) detectada(s) em {lote.nome_arquivo}"
                ).classes("text-[11px] text-[#71717A] py-[10px]")

        render_barra_abas_amostras()

        # =====================================================================
        # CONTEÚDO PRINCIPAL DA PÁGINA /importar
        # =====================================================================
        with ui.column().classes(
            "w-full max-w-[1280px] mx-auto px-[24px] lg:px-[32px] py-[26px] gap-[20px]"
        ):
            # Título
            with ui.row().classes("w-full items-center justify-between gap-[16px] flex-wrap"):
                with ui.column().classes("gap-[4px]"):
                    ui.label("Importar Planilha UltraLIMS").classes(
                        "text-[24px] font-bold text-[#111827] leading-tight"
                    )
                    ui.label(
                        "Envie um arquivo com uma ou várias amostras, confira todos os itens captados na tabela dinâmica por KPI e aplique o contexto e as normas (1 a 3)."
                    ).classes("text-[13px] text-[#52525B]")

                ui.button(
                    "Cancelar e voltar ao Painel",
                    color="white",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("unelevated no-caps").classes("lt-btn-secondary")

            # =================================================================
            # SEÇÃO 1 — Arquivo, KPIs Clicáveis e Tabela Dinâmica por KPI
            # =================================================================
            @ui.refreshable
            def render_secao_validacao() -> None:
                lote: ResultadoPreLeituraLote | None = estado["lote"]
                pre = _obter_amostra_ativa()

                with ui.column().classes("w-full lt-card p-[24px] gap-[18px]"):
                    with ui.row().classes("w-full items-center justify-between gap-[12px] flex-wrap"):
                        with ui.row().classes("items-center gap-[10px] no-wrap"):
                            badge_bg = "#16A34A" if pre else "#004B8D"
                            with ui.element("div").classes(
                                "w-[26px] h-[26px] rounded-full flex items-center justify-center text-white text-[12px] font-bold"
                            ).style(f"background-color: {badge_bg};"):
                                if pre:
                                    ui.icon("check", size="16px", color="white")
                                else:
                                    ui.label("1")
                            ui.label("1. Arquivo e Validação").classes(
                                "text-[16px] font-bold text-[#111827]"
                            )

                        if not pre:
                            ui.button(
                                "Carregar planilha de demonstração (3 amostras)",
                                icon="science",
                                color="white",
                                on_click=_carregar_demo,
                            ).props("unelevated no-caps").classes("lt-btn-secondary")
                        else:
                            ui.button(
                                "Trocar arquivo",
                                icon="refresh",
                                color="white",
                                on_click=_limpar_arquivo,
                            ).props("unelevated no-caps").classes("lt-btn-secondary")

                    if not pre or not lote:
                        with ui.column().classes(
                            "w-full border border-dashed border-[#D4D4D8] rounded-[8px] "
                            "bg-[#FAFAFA] p-[24px] items-center gap-[12px]"
                        ):
                            ui.icon("upload_file", size="34px", color="#004B8D")
                            ui.label(
                                "Arraste ou selecione o arquivo .xlsx / .csv exportado do UltraLIMS"
                            ).classes("text-[14px] font-semibold text-[#111827]")
                            ui.label(
                                "Suporta múltiplas amostras por arquivo — cada amostra abre em uma aba logo abaixo do cabeçalho."
                            ).classes("text-[12px] text-[#71717A]")

                            ui.upload(
                                label="Selecionar arquivo UltraLIMS (.xlsx ou .csv)",
                                auto_upload=True,
                                on_upload=_ao_enviar_arquivo,
                            ).props('accept=".xlsx,.xls,.csv" flat bordered color="primary"').classes(
                                "w-full max-w-[480px] bg-white"
                            )
                    else:
                        # Faixa da amostra ativa na aba
                        with ui.row().classes(
                            "w-full items-center justify-between bg-[#FAFAFA] border border-[#E4E4E7] "
                            "rounded-[8px] px-[16px] py-[12px] flex-wrap gap-[10px]"
                        ):
                            with ui.row().classes("items-center gap-[12px] no-wrap"):
                                with ui.element("div").classes(
                                    "w-[36px] h-[36px] rounded-[6px] bg-[#EFF6FF] border border-[#BFDBFE] "
                                    "flex items-center justify-center shrink-0"
                                ):
                                    ui.icon("description", size="18px", color="#004B8D")
                                with ui.column().classes("gap-[2px]"):
                                    with ui.row().classes("items-center gap-[8px] flex-wrap"):
                                        ui.label(f"Amostra {pre.codigo_amostra_principal}").classes(
                                            "font-mono-lt text-[14px] font-bold text-[#111827]"
                                        )
                                        ui.label("·").classes("text-[#71717A]")
                                        ui.label(pre.nome_arquivo).classes(
                                            "font-mono-lt text-[12px] text-[#52525B]"
                                        )
                                    concl_str = (
                                        pre.data_conclusao.strftime("%d/%m/%Y")
                                        if pre.data_conclusao
                                        else "Sem data conclusão (RN-01)"
                                    )
                                    ui.label(
                                        f"Coleta: {pre.data_coleta.strftime('%d/%m/%Y')} · "
                                        f"Conclusão: {concl_str} · "
                                        f"{len(lote.amostras)} amostra(s) no lote"
                                    ).classes("text-[11px] text-[#52525B]")
                            if pre.total_avisos > 0:
                                ui.html(
                                    status_pill_html(f"{pre.total_avisos} AVISO(S) DE REVISÃO", "outline-amber"),
                                    sanitize=False,
                                )
                            else:
                                ui.html(status_pill_html("PRÉ-LEITURA SEM AVISOS", "solid-green"), sanitize=False)

                        # 4 KPI Cards clicáveis (clicar expande/destaca aquele KPI na tabela dinâmica!)
                        contagens = {
                            "mapeados": pre.total_mapeados,
                            "sem_vmp": pre.total_sem_vmp,
                            "ignorados": pre.total_ignorados,
                            "avisos": pre.total_avisos,
                        }
                        with ui.row().classes("w-full gap-[14px] flex-wrap"):
                            for kpi_key, titulo, tag, cor_dot, subtitulo in _KPI_DEFINICOES:
                                ativo = estado["kpi_foco"] == kpi_key
                                card_cls = (
                                    "flex-1 min-w-[200px] bg-white border border-[#E4E4E7] rounded-[8px] "
                                    "px-[18px] py-[14px] gap-[6px] lt-kpi-clickable "
                                    + ("lt-kpi-active" if ativo else "")
                                )
                                with ui.column().classes(card_cls).on(
                                    "click", lambda _, k=kpi_key: _focar_kpi(k)
                                ):
                                    with ui.row().classes("w-full items-center justify-between no-wrap"):
                                        ui.label(titulo).classes("text-[12px] font-medium text-[#52525B]")
                                        with ui.row().classes("items-center gap-[5px] no-wrap"):
                                            ui.element("div").classes("w-[8px] h-[8px] rounded-full").style(
                                                f"background-color: {cor_dot};"
                                            )
                                            ui.label(tag).classes(
                                                "text-[9px] font-bold tracking-[0.4px] text-[#71717A]"
                                            )
                                    ui.label(str(contagens[kpi_key])).classes(
                                        "font-mono-lt text-[26px] font-bold text-[#111827] leading-tight"
                                    )
                                    ui.label(subtitulo).classes("text-[11px] text-[#71717A]")

                        # =====================================================
                        # TABELA DINÂMICA DE CONFERÊNCIA POR KPI (Requisito 3)
                        # Mostra TODOS os itens captados da planilha por KPI!
                        # =====================================================
                        total_itens_captados = sum(len(pre.itens_por_kpi.get(k, [])) for k, *_ in _KPI_DEFINICOES)
                        with ui.column().classes(
                            "w-full border border-[#E4E4E7] rounded-[8px] overflow-hidden gap-0"
                        ):
                            with ui.row().classes(
                                "w-full items-center justify-between px-[18px] py-[12px] bg-white border-b border-[#E4E4E7] flex-wrap gap-[10px]"
                            ):
                                with ui.column().classes("gap-[2px]"):
                                    ui.label(
                                        "Tabela Dinâmica de Conferência por KPI"
                                    ).classes("text-[13px] font-bold text-[#111827]")
                                    ui.label(
                                        f"Expanda qualquer KPI acima ou abaixo para inspecionar todos os {total_itens_captados} registros captados da amostra {pre.codigo_amostra_principal}."
                                    ).classes("text-[11px] text-[#71717A]")

                                with ui.row().classes("items-center gap-[8px]"):
                                    ui.button(
                                        "Expandir todos",
                                        color="white",
                                        on_click=_expandir_todos_kpis,
                                    ).props("unelevated no-caps dense").classes(
                                        "lt-btn-secondary text-[11px] h-[30px] px-[10px]"
                                    )
                                    ui.button(
                                        "Recolher todos",
                                        color="white",
                                        on_click=_recolher_todos_kpis,
                                    ).props("unelevated no-caps dense").classes(
                                        "lt-btn-secondary text-[11px] h-[30px] px-[10px]"
                                    )

                            # Cabeçalho alinhado da tabela dinâmica
                            with ui.element("div").classes(
                                "w-full grid items-center bg-[#F4F4F5] border-b border-[#E4E4E7] "
                                "px-[18px] py-[10px] text-[11px] font-semibold text-[#111827]"
                            ).style("grid-template-columns: 2.2fr 0.8fr 2.4fr 0.7fr; gap: 12px;"):
                                ui.label("KPI (agrupamento)")
                                ui.label("Registros")
                                ui.label("Descrição do grupo")
                                ui.label("Status").classes("text-right")

                            for idx_k, (kpi_key, titulo, tag, cor_dot, subtitulo) in enumerate(_KPI_DEFINICOES):
                                itens = pre.itens_por_kpi.get(kpi_key, [])
                                is_exp = kpi_key in estado["kpis_expandidos"]
                                b_top = "border-t border-[#E4E4E7]" if idx_k > 0 else ""

                                # Linha pai clicável do KPI
                                with ui.element("div").classes(
                                    f"w-full grid items-center px-[18px] py-[12px] cursor-pointer "
                                    f"transition hover:bg-[#F8FAFC] {b_top} "
                                    + ("bg-[#F8FBFF]" if is_exp else "bg-white")
                                ).style("grid-template-columns: 2.2fr 0.8fr 2.4fr 0.7fr; gap: 12px;").on(
                                    "click", lambda _, k=kpi_key: _toggle_kpi_grupo(k)
                                ):
                                    with ui.row().classes("items-center gap-[8px] no-wrap"):
                                        ui.icon(
                                            "keyboard_arrow_down" if is_exp else "keyboard_arrow_right",
                                            size="18px",
                                            color="#52525B",
                                        )
                                        ui.element("div").classes(
                                            "w-[8px] h-[8px] rounded-full shrink-0"
                                        ).style(f"background-color: {cor_dot};")
                                        ui.label(titulo).classes("text-[13px] font-bold text-[#111827]")

                                    ui.label(f"{len(itens)} item(ns)").classes(
                                        "font-mono-lt text-[12px] font-semibold text-[#111827]"
                                    )
                                    ui.label(subtitulo).classes("text-[12px] text-[#52525B]")

                                    with ui.row().classes("justify-end"):
                                        pill_var = (
                                            "outline-green"
                                            if kpi_key == "mapeados"
                                            else ("outline-amber" if kpi_key == "avisos" and itens else "outline-gray")
                                        )
                                        ui.html(status_pill_html(tag, pill_var), sanitize=False)  # type: ignore[arg-type]

                                # Sub-tabela expandida com TODOS os itens captados daquele KPI
                                if is_exp:
                                    with ui.column().classes(
                                        "w-full bg-white border-t border-[#E4E4E7] px-[32px] py-[14px] gap-[8px]"
                                    ):
                                        if not itens:
                                            ui.label(
                                                "Nenhuma ocorrência registrada neste KPI para esta amostra."
                                            ).classes("text-[12px] text-[#71717A] py-[4px]")
                                        else:
                                            with ui.column().classes(
                                                "w-full border border-[#E4E4E7] rounded-[8px] overflow-hidden gap-0"
                                            ):
                                                # Sub-header
                                                with ui.element("div").classes(
                                                    "w-full grid items-center bg-[#FAFAFA] border-b border-[#E4E4E7] "
                                                    "px-[14px] py-[8px] text-[10px] font-semibold uppercase tracking-[0.4px] text-[#71717A]"
                                                ).style("grid-template-columns: 155px 1.4fr 140px 2fr; gap: 10px;"):
                                                    ui.label("Classificação")
                                                    ui.label("Ensaio / Coluna")
                                                    ui.label("Valor Bruto")
                                                    ui.label("Ação Automática do Motor")

                                                for idx_it, oc in enumerate(itens):
                                                    b_it = "border-t border-[#E4E4E7]" if idx_it > 0 else ""
                                                    variant_oc = f"outline-{oc.tipo_pill}"
                                                    with ui.element("div").classes(
                                                        f"w-full grid items-center px-[14px] py-[9px] hover:bg-[#F8FAFC] {b_it}"
                                                    ).style("grid-template-columns: 155px 1.4fr 140px 2fr; gap: 10px;"):
                                                        ui.html(
                                                            status_pill_html(oc.classificacao, variant_oc),  # type: ignore[arg-type]
                                                            sanitize=False,
                                                        )
                                                        ui.label(oc.ensaio_coluna).classes(
                                                            "text-[12px] font-semibold text-[#111827]"
                                                        )
                                                        ui.label(oc.valor_bruto).classes(
                                                            "font-mono-lt text-[12px] font-medium text-[#111827]"
                                                        )
                                                        ui.label(oc.acao_motor).classes(
                                                            "text-[12px] text-[#52525B]"
                                                        )

            # =================================================================
            # SEÇÃO 2 — Contexto Comercial e Normas (aplicado a todo o lote D3)
            # =================================================================
            @ui.refreshable
            def render_secao_contexto_normas() -> None:
                lote: ResultadoPreLeituraLote | None = estado["lote"]
                if not lote or not lote.amostras:
                    return

                n_amostras = len(lote.amostras)

                with ui.column().classes("w-full gap-[20px]"):
                    with ui.column().classes("w-full lt-card p-[24px] gap-[16px]"):
                        with ui.row().classes("items-center justify-between gap-[10px] flex-wrap"):
                            with ui.row().classes("items-center gap-[10px] no-wrap"):
                                with ui.element("div").classes(
                                    "w-[26px] h-[26px] rounded-full bg-[#004B8D] flex items-center justify-center "
                                    "text-white text-[12px] font-bold"
                                ):
                                    ui.label("2")
                                ui.label("2. Contexto Comercial e Origem da Amostra").classes(
                                    "text-[16px] font-bold text-[#111827]"
                                )
                            ui.label(
                                f"Contexto único aplicado às {n_amostras} amostra(s) do arquivo (D3)"
                            ).classes("text-[11px] text-[#71717A]")

                        propostas_disp = repo.listar_propostas(estado["cliente"])
                        if estado["proposta"] not in propostas_disp and propostas_disp:
                            estado["proposta"] = propostas_disp[0]

                        locais_disp = repo.listar_locais(estado["cliente"], estado["proposta"])
                        if estado["local"] not in locais_disp and locais_disp:
                            estado["local"] = locais_disp[0]

                        with ui.grid(columns=2).classes("w-full gap-[16px]"):
                            with ui.column().classes("gap-[6px] w-full"):
                                ui.label("Cliente").classes("text-[12px] font-semibold text-[#111827]")
                                ui.select(
                                    options=repo.listar_clientes(),
                                    value=estado["cliente"],
                                    on_change=lambda e: _trocar_cliente(e.value),
                                ).props("outlined dense options-dense").classes("w-full lt-field")

                            with ui.column().classes("gap-[6px] w-full"):
                                ui.label("Proposta Comercial").classes("text-[12px] font-semibold text-[#111827]")
                                ui.select(
                                    options=propostas_disp,
                                    value=estado["proposta"],
                                    on_change=lambda e: _trocar_proposta(e.value),
                                ).props("outlined dense options-dense").classes("w-full lt-field")

                            with ui.column().classes("gap-[6px] w-full"):
                                ui.label("Local de Coleta").classes("text-[12px] font-semibold text-[#111827]")
                                ui.select(
                                    options=locais_disp,
                                    value=estado["local"],
                                    on_change=lambda e: estado.__setitem__("local", e.value),
                                ).props("outlined dense options-dense").classes("w-full lt-field")

                            with ui.column().classes("gap-[6px] w-full"):
                                ui.label(
                                    "Origem da Amostra (filtra legislações compatíveis)"
                                ).classes("text-[12px] font-semibold text-[#111827]")
                                ui.select(
                                    options=repo.listar_origens(),
                                    value=estado["origem"],
                                    on_change=lambda e: _trocar_origem(e.value),
                                ).props("outlined dense options-dense").classes("w-full lt-field")

                    # Legislações e Classes (1 a 3 normas)
                    with ui.column().classes("w-full lt-card p-[24px] gap-[14px]"):
                        with ui.row().classes("w-full items-center justify-between gap-[12px] flex-wrap"):
                            with ui.column().classes("gap-[2px]"):
                                ui.label("Legislações e Classes Aplicáveis (1 a 3 normas)").classes(
                                    "text-[15px] font-bold text-[#111827]"
                                )
                                ui.label(
                                    "Portarias operam sem classe; Resoluções CONAMA exigem seleção de classe ou artigo."
                                ).classes("text-[12px] text-[#71717A]")

                            atingiu_limite = len(estado["normas"]) >= 3
                            if atingiu_limite:
                                ui.button(
                                    "Limite atingido (3/3 normas)",
                                    icon="add",
                                ).props("disable outline no-caps").classes(
                                    "rounded-[6px] text-[12px] font-semibold text-[#71717A]"
                                ).style("height: 36px;")
                            else:
                                ui.button(
                                    "Adicionar",
                                    icon="add",
                                    on_click=_adicionar_norma,
                                ).props("outline no-caps").classes(
                                    "rounded-[6px] text-[12px] font-semibold text-[#004B8D]"
                                ).style("height: 36px; border-color: #004B8D;")

                        legs_compativeis = repo.listar_legislacoes_por_origem(estado["origem"])
                        opcoes_legs = {m["sigla"]: m["nome_completo"] for m in legs_compativeis}
                        siglas_disp = list(opcoes_legs.keys())

                        for idx, item_norma in enumerate(estado["normas"]):
                            if item_norma["sigla"] not in siglas_disp and siglas_disp:
                                item_norma["sigla"] = siglas_disp[0]
                                cl_disp = repo.listar_classes_legislacao(item_norma["sigla"])
                                item_norma["classe"] = cl_disp[0] if cl_disp else None

                            classes_disp = repo.listar_classes_legislacao(item_norma["sigla"])
                            if classes_disp and item_norma["classe"] not in classes_disp:
                                item_norma["classe"] = classes_disp[0]
                            elif not classes_disp:
                                item_norma["classe"] = None

                            with ui.row().classes(
                                "w-full items-center gap-[12px] bg-[#FAFAFA] border border-[#E4E4E7] "
                                "rounded-[8px] px-[14px] py-[10px] no-wrap"
                            ):
                                with ui.element("div").classes(
                                    "w-[30px] h-[30px] rounded-[6px] bg-[#004B8D] flex items-center "
                                    "justify-center text-white text-[11px] font-bold shrink-0"
                                ):
                                    ui.label(f"L{idx + 1}")

                                ui.select(
                                    options=opcoes_legs,
                                    value=item_norma["sigla"],
                                    on_change=lambda e, i=idx: _trocar_legislacao(i, e.value),
                                ).props("outlined dense options-dense").classes("flex-1 lt-field")

                                if classes_disp:
                                    opcoes_cl = {c: f"Classe: {c}" for c in classes_disp}
                                    ui.select(
                                        options=opcoes_cl,
                                        value=item_norma["classe"],
                                        on_change=lambda e, i=idx: _trocar_classe(i, e.value),
                                    ).props("outlined dense options-dense").classes("flex-1 lt-field")
                                else:
                                    ui.input(value="Sem classe (Portaria)").props(
                                        "outlined dense disable"
                                    ).classes("flex-1 lt-field")

                                btn_del = ui.button(
                                    icon="delete_outline",
                                    on_click=lambda _, i=idx: _remover_norma(i),
                                ).props("flat round dense").classes(
                                    "text-[#52525B] hover:text-[#DC2626] shrink-0"
                                )
                                if len(estado["normas"]) <= 1:
                                    btn_del.props("disable")

                    # Rodapé de confirmação
                    with ui.row().classes("w-full items-center justify-between pt-[4px]"):
                        ui.button(
                            "Cancelar e voltar ao Painel",
                            color="white",
                            on_click=lambda: ui.navigate.to("/"),
                        ).props("unelevated no-caps").classes("lt-btn-secondary")

                        lbl_confirm = (
                            f"Confirmar e Abrir Conferência ({n_amostras} amostras)"
                            if n_amostras > 1
                            else "Confirmar e Abrir Conferência"
                        )
                        ui.button(
                            lbl_confirm,
                            icon="check",
                            on_click=_confirmar_importacao,
                        ).props("unelevated no-caps").classes("lt-btn-primary")

            # --- Handlers ---
            def _aplicar_lote(lote: ResultadoPreLeituraLote) -> None:
                estado["lote"] = lote
                estado["amostra_ativa"] = lote.amostras[0].codigo_amostra_principal if lote.amostras else None
                estado["kpis_expandidos"] = {"avisos", "mapeados"}
                estado["kpi_foco"] = None
                render_barra_abas_amostras.refresh()
                render_secao_validacao.refresh()
                render_secao_contexto_normas.refresh()

            async def _ao_enviar_arquivo(e: events.UploadEventArguments) -> None:
                raw_bytes = await e.file.read()
                nome = e.file.name
                try:
                    lote = repo.analisar_planilha(raw_bytes, nome)
                except Exception as exc:
                    mostrar_toast_aviso(f"Não foi possível ler '{nome}': {exc}")
                    return
                _aplicar_lote(lote)

            def _carregar_demo() -> None:
                _aplicar_lote(gerar_lote_demonstracao())

            def _limpar_arquivo() -> None:
                estado["lote"] = None
                estado["amostra_ativa"] = None
                estado["kpi_foco"] = None
                render_barra_abas_amostras.refresh()
                render_secao_validacao.refresh()
                render_secao_contexto_normas.refresh()

            def _trocar_aba_amostra(cod: str) -> None:
                if cod != estado["amostra_ativa"]:
                    estado["amostra_ativa"] = cod
                    estado["kpi_foco"] = None
                    render_secao_validacao.refresh()

            def _focar_kpi(kpi_key: str) -> None:
                estado["kpi_foco"] = kpi_key
                estado["kpis_expandidos"] = {kpi_key}
                render_secao_validacao.refresh()

            def _toggle_kpi_grupo(kpi_key: str) -> None:
                if kpi_key in estado["kpis_expandidos"]:
                    estado["kpis_expandidos"].remove(kpi_key)
                else:
                    estado["kpis_expandidos"].add(kpi_key)
                render_secao_validacao.refresh()

            def _expandir_todos_kpis() -> None:
                estado["kpis_expandidos"] = {k for k, *_ in _KPI_DEFINICOES}
                render_secao_validacao.refresh()

            def _recolher_todos_kpis() -> None:
                estado["kpis_expandidos"] = set()
                estado["kpi_foco"] = None
                render_secao_validacao.refresh()

            def _trocar_cliente(novo_cliente: str) -> None:
                estado["cliente"] = novo_cliente
                props = repo.listar_propostas(novo_cliente)
                estado["proposta"] = props[0] if props else ""
                locais = repo.listar_locais(novo_cliente, estado["proposta"])
                estado["local"] = locais[0] if locais else ""
                render_secao_contexto_normas.refresh()

            def _trocar_proposta(nova_proposta: str) -> None:
                estado["proposta"] = nova_proposta
                locais = repo.listar_locais(estado["cliente"], nova_proposta)
                estado["local"] = locais[0] if locais else ""
                render_secao_contexto_normas.refresh()

            def _trocar_origem(nova_origem: str) -> None:
                estado["origem"] = nova_origem
                legs = repo.listar_legislacoes_por_origem(nova_origem)
                if legs:
                    sigla0 = legs[0]["sigla"]
                    cl0 = legs[0]["classes"][0] if legs[0]["classes"] else None
                    estado["normas"] = [{"sigla": sigla0, "classe": cl0}]
                render_secao_contexto_normas.refresh()

            def _adicionar_norma() -> None:
                if len(estado["normas"]) >= 3:
                    return
                legs = repo.listar_legislacoes_por_origem(estado["origem"])
                usados = {(n["sigla"], n["classe"]) for n in estado["normas"]}
                escolhido = None
                for m in legs:
                    if m["classes"]:
                        for c in m["classes"]:
                            if (m["sigla"], c) not in usados:
                                escolhido = {"sigla": m["sigla"], "classe": c}
                                break
                    else:
                        if (m["sigla"], None) not in usados:
                            escolhido = {"sigla": m["sigla"], "classe": None}
                    if escolhido:
                        break
                if not escolhido and legs:
                    m0 = legs[0]
                    escolhido = {"sigla": m0["sigla"], "classe": m0["classes"][0] if m0["classes"] else None}
                if escolhido:
                    estado["normas"].append(escolhido)
                render_secao_contexto_normas.refresh()

            def _remover_norma(idx: int) -> None:
                if len(estado["normas"]) > 1 and 0 <= idx < len(estado["normas"]):
                    estado["normas"].pop(idx)
                    render_secao_contexto_normas.refresh()

            def _trocar_legislacao(idx: int, nova_sigla: str) -> None:
                estado["normas"][idx]["sigla"] = nova_sigla
                classes = repo.listar_classes_legislacao(nova_sigla)
                estado["normas"][idx]["classe"] = classes[0] if classes else None
                render_secao_contexto_normas.refresh()

            def _trocar_classe(idx: int, nova_classe: str) -> None:
                estado["normas"][idx]["classe"] = nova_classe

            def _confirmar_importacao() -> None:
                lote: ResultadoPreLeituraLote | None = estado["lote"]
                if not lote or not lote.amostras:
                    mostrar_toast_aviso("Envie uma planilha antes de confirmar.")
                    return

                pares = [(n["sigla"], n["classe"]) for n in estado["normas"]]
                if len(pares) != len(set(pares)):
                    mostrar_toast_aviso("Remova legislações/classes duplicadas antes de continuar.")
                    return

                criadas = repo.criar_lote_importado(
                    lote=lote,
                    cliente=estado["cliente"],
                    proposta=estado["proposta"],
                    local_coleta=estado["local"],
                    origem=estado["origem"],
                    normas_selecionadas=pares,
                )
                codigos_lote = [a.codigo for a in criadas]
                app.storage.user["lote_conferencia"] = codigos_lote

                # Abre na amostra que estava ativa na aba (ou a primeira criada)
                destino = codigos_lote[0]
                if estado["amostra_ativa"] in codigos_lote:
                    destino = estado["amostra_ativa"]

                msg = (
                    f"{len(criadas)} amostras importadas e avaliadas"
                    if len(criadas) > 1
                    else f"Amostra {destino} importada e avaliada"
                )
                mostrar_toast_sucesso(msg)
                ui.navigate.to(f"/amostra/{quote(destino, safe='')}")

            # Renderização inicial
            render_secao_validacao()
            render_secao_contexto_normas()
