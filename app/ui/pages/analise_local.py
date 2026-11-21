"""Tela B5 — Análise por Local de Coleta (/analise) com Gráfico de Barras Empilhadas e Tabela Dinâmica."""

from __future__ import annotations

from urllib.parse import quote

from nicegui import ui

from app.core.models import GrupoEnsaioLocal
from app.repo.mock_repo import repo
from app.ui.components.badges import status_pill_html
from app.ui.components.grafico_evolucao import construir_option_evolucao_conformidade
from app.ui.layout import criar_shell


_PERIODOS_OPCOES = {
    3: "Últimos 3 meses",
    6: "Últimos 6 meses",
    12: "Últimos 12 meses",
}


def registrar_pagina_analise_local() -> None:
    @ui.page("/analise")
    def pagina_analise_local() -> None:
        criar_shell(aba_ativa="analise")

        # Pré-seleciona SAMAE Blumenau -> Captação — Rio Itajaí-Açu -> CONAMA 357 — Classe 1 (caso referência B5)
        clientes = repo.listar_clientes()
        cli_padrao = "SAMAE Blumenau" if "SAMAE Blumenau" in clientes else clientes[0]
        locais_ini = repo.listar_locais_por_cliente(cli_padrao)
        loc_padrao = locais_ini[0] if locais_ini else ""
        normas_ini = repo.listar_normas_do_local(cli_padrao, loc_padrao)
        norma_padrao = normas_ini[0] if normas_ini else ""

        estado: dict = {
            "cliente": cli_padrao,
            "local": loc_padrao,
            "norma": norma_padrao,
            "periodo_meses": 6,
            "expandidos": set(),       # códigos de ensaio expandidos
            "mostrar_todas": set(),    # códigos de ensaio exibindo todas as coletas (não só as 3 últimas)
            "inicializado": False,
        }

        with ui.column().classes(
            "w-full max-w-[1360px] mx-auto px-[24px] lg:px-[32px] py-[28px] gap-[20px]"
        ):
            ui.label("Análise por Local de Coleta").classes(
                "text-[24px] font-bold text-[#111827] leading-tight"
            )

            # =================================================================
            # 1. Barra de 4 Filtros em Cascata (Cliente, Local, Norma/Classe, Período)
            # =================================================================
            @ui.refreshable
            def render_filtros() -> None:
                locais_disp = repo.listar_locais_por_cliente(estado["cliente"])
                if estado["local"] not in locais_disp and locais_disp:
                    estado["local"] = locais_disp[0]

                normas_disp = repo.listar_normas_do_local(estado["cliente"], estado["local"])
                if estado["norma"] not in normas_disp and normas_disp:
                    estado["norma"] = normas_disp[0]

                with ui.row().classes(
                    "w-full lt-card px-[16px] py-[12px] items-center gap-[12px] flex-wrap"
                ):
                    ui.select(
                        options=clientes,
                        value=estado["cliente"],
                        label="Cliente",
                        on_change=lambda e: _trocar_cliente(e.value),
                    ).props("outlined dense options-dense").classes("min-w-[220px] flex-1 lt-field")

                    ui.select(
                        options=locais_disp,
                        value=estado["local"],
                        label="Local",
                        on_change=lambda e: _trocar_local(e.value),
                    ).props("outlined dense options-dense").classes("min-w-[240px] flex-1 lt-field")

                    ui.select(
                        options=normas_disp,
                        value=estado["norma"],
                        label="Norma / Classe",
                        on_change=lambda e: _trocar_norma(e.value),
                    ).props("outlined dense options-dense").classes("min-w-[220px] flex-1 lt-field")

                    ui.select(
                        options=_PERIODOS_OPCOES,
                        value=estado["periodo_meses"],
                        label="Período",
                        on_change=lambda e: _trocar_periodo(int(e.value)),
                    ).props("outlined dense options-dense").classes("min-w-[175px] w-[190px] lt-field")

            # =================================================================
            # 2. Gráfico de Barras Empilhadas — Evolução de Conformidade
            # =================================================================
            @ui.refreshable
            def render_grafico_evolucao() -> None:
                meses = repo.obter_evolucao_mensal_local(
                    cliente=estado["cliente"],
                    local_coleta=estado["local"],
                    norma_label=estado["norma"],
                    periodo_meses=estado["periodo_meses"],
                )
                tot_fav = sum(m.favoraveis for m in meses)
                tot_pend = sum(m.pendentes for m in meses)
                tot_nfav = sum(m.nao_favoraveis for m in meses)
                tot_geral = tot_fav + tot_pend + tot_nfav

                option = construir_option_evolucao_conformidade(meses)

                with ui.column().classes("w-full lt-card px-[22px] pt-[18px] pb-[14px] gap-[10px]"):
                    with ui.row().classes(
                        "w-full items-center justify-between gap-[12px] flex-wrap"
                    ):
                        with ui.row().classes("items-baseline gap-[10px] flex-wrap"):
                            ui.label("Evolução de Conformidade").classes(
                                "text-[15px] font-bold text-[#111827]"
                            )
                            ui.label(
                                f"{tot_geral} amostras analisadas no período"
                            ).classes("text-[12px] text-[#71717A]")

                        # Legenda no canto superior direito (exatamente como no layout B5)
                        with ui.row().classes("items-center gap-[16px] flex-wrap"):
                            with ui.row().classes("items-center gap-[6px] no-wrap"):
                                ui.element("div").classes(
                                    "w-[10px] h-[10px] rounded-[2px] bg-[#16A34A]"
                                )
                                ui.label(f"Favoráveis ({tot_fav})").classes(
                                    "text-[11px] font-medium text-[#52525B]"
                                )
                            with ui.row().classes("items-center gap-[6px] no-wrap"):
                                ui.element("div").classes(
                                    "w-[10px] h-[10px] rounded-[2px] bg-[#94A3B8]"
                                )
                                ui.label(f"Pendentes ({tot_pend})").classes(
                                    "text-[11px] font-medium text-[#52525B]"
                                )
                            with ui.row().classes("items-center gap-[6px] no-wrap"):
                                ui.element("div").classes(
                                    "w-[10px] h-[10px] rounded-[2px] bg-[#DC2626]"
                                )
                                ui.label(f"Não favoráveis ({tot_nfav})").classes(
                                    "text-[11px] font-medium text-[#52525B]"
                                )

                    ui.echart(option).classes("w-full h-[250px]")

            # =================================================================
            # 3. Tabela Dinâmica Agrupada por Ensaio (Accordion / Pivot)
            # =================================================================
            @ui.refreshable
            def render_tabela_dinamica() -> None:
                grupos: list[GrupoEnsaioLocal] = repo.obter_tabela_dinamica_local(
                    cliente=estado["cliente"],
                    local_coleta=estado["local"],
                    norma_label=estado["norma"],
                    periodo_meses=estado["periodo_meses"],
                )

                if not estado["inicializado"] and grupos:
                    estado["expandidos"] = {grupos[0].codigo_ensaio}
                    estado["inicializado"] = True

                rotulo_media = f"Média ({estado['periodo_meses']}m)"

                with ui.column().classes(
                    "w-full lt-card overflow-hidden gap-0"
                ):
                    # Cabeçalho fixo alinhado em 6 colunas (idêntico ao print B5)
                    with ui.element("div").classes(
                        "w-full grid items-center bg-[#F4F4F5] border-b border-[#E4E4E7] "
                        "px-[20px] py-[12px] text-[11px] font-semibold text-[#111827]"
                    ).style("grid-template-columns: 2.3fr 0.7fr 1.1fr 1fr 0.9fr 1.4fr; gap: 12px;"):
                        ui.label("Ensaio (agrupamento)")
                        ui.label("Coletas")
                        ui.label(rotulo_media)
                        ui.label("Conformidade")
                        ui.label("Não conformes")
                        ui.label("Pendentes / Desvios")

                    if not grupos:
                        with ui.row().classes("w-full justify-center py-[32px]"):
                            ui.label("Nenhum ensaio encontrado para o filtro selecionado.").classes(
                                "text-[13px] text-[#71717A]"
                            )
                        return

                    for idx_g, g in enumerate(grupos):
                        is_exp = g.codigo_ensaio in estado["expandidos"]
                        border_cls = "border-t border-[#E4E4E7]" if idx_g > 0 else ""

                        # Linha pai clicável (expande/recolhe o grupo)
                        with ui.element("div").classes(
                            f"w-full grid items-center px-[20px] py-[14px] cursor-pointer "
                            f"transition hover:bg-[#F8FAFC] {border_cls} "
                            + ("bg-[#FAFAFA]" if is_exp else "bg-white")
                        ).style(
                            "grid-template-columns: 2.3fr 0.7fr 1.1fr 1fr 0.9fr 1.4fr; gap: 12px;"
                        ).on("click", lambda _, cod=g.codigo_ensaio: _toggle_grupo(cod)):
                            with ui.row().classes("items-center gap-[8px] no-wrap"):
                                ui.icon(
                                    "keyboard_arrow_down" if is_exp else "keyboard_arrow_right",
                                    size="18px",
                                    color="#52525B",
                                )
                                ui.label(f"{g.codigo_ensaio} — {g.nome_ensaio}").classes(
                                    "text-[13px] font-bold text-[#111827]"
                                )

                            ui.label(str(g.total_coletas)).classes(
                                "font-mono-lt text-[12px] text-[#111827]"
                            )
                            ui.label(g.media_texto).classes(
                                "font-mono-lt text-[12px] text-[#111827]"
                            )
                            ui.label(g.conformidade_pct).classes(
                                "font-mono-lt text-[12px] font-bold text-[#111827]"
                            )
                            ui.label(str(g.nao_conformes)).classes(
                                "font-mono-lt text-[12px] "
                                + ("font-bold text-[#DC2626]" if g.nao_conformes > 0 else "text-[#111827]")
                            )
                            ui.label(g.pendentes_desvios_texto).classes(
                                "font-mono-lt text-[12px] text-[#52525B]"
                            )

                        # Painel expandido com os registros individuais das coletas
                        if is_exp:
                            ver_todas = g.codigo_ensaio in estado["mostrar_todas"]
                            coletas_exibidas = g.coletas if ver_todas else g.coletas[:3]
                            total_c = len(g.coletas)

                            with ui.column().classes(
                                "w-full bg-white border-t border-[#E4E4E7] px-[34px] py-[16px] gap-[12px]"
                            ):
                                with ui.row().classes(
                                    "w-full items-center justify-between gap-[12px] flex-wrap"
                                ):
                                    if ver_todas or total_c <= 3:
                                        sub_txt = f"Registros do grupo · exibindo todas as {total_c} coletas"
                                    else:
                                        sub_txt = f"Registros do grupo · exibindo últimas 3 de {total_c} coletas"
                                    ui.label(sub_txt).classes("text-[12px] text-[#52525B]")

                                    if total_c > 3:
                                        link_lbl = (
                                            "Mostrar últimas 3 ↑"
                                            if ver_todas
                                            else "Explorar todas as coletas →"
                                        )
                                        ui.label(link_lbl).classes(
                                            "text-[12px] font-bold text-[#111827] hover:text-[#004B8D] "
                                            "cursor-pointer select-none"
                                        ).on("click", lambda _, cod=g.codigo_ensaio: _toggle_mostrar_todas(cod))

                                # Caixa de sub-linhas das coletas (idêntica ao print B5)
                                with ui.column().classes(
                                    "w-full bg-white border border-[#E4E4E7] rounded-[8px] overflow-hidden gap-0"
                                ):
                                    for idx_c, col in enumerate(coletas_exibidas):
                                        b_sub = "border-t border-[#E4E4E7]" if idx_c > 0 else ""
                                        with ui.element("div").classes(
                                            f"w-full grid items-center px-[16px] py-[11px] hover:bg-[#F8FAFC] {b_sub}"
                                        ).style(
                                            "grid-template-columns: 115px 95px 1.2fr 1.2fr 185px 40px; gap: 12px;"
                                        ):
                                            ui.label(col.codigo_amostra).classes(
                                                "font-mono-lt text-[12px] font-bold text-[#111827]"
                                            )
                                            ui.label(col.data_coleta.strftime("%d/%m/%Y")).classes(
                                                "font-mono-lt text-[12px] text-[#71717A]"
                                            )
                                            with ui.row().classes("items-baseline gap-[6px] no-wrap"):
                                                ui.label("Resultado:").classes(
                                                    "font-mono-lt text-[12px] font-semibold text-[#111827]"
                                                )
                                                ui.label(col.resultado_texto).classes(
                                                    "font-mono-lt text-[12px] font-bold text-[#111827]"
                                                )
                                            ui.label(f"{col.vmp_prefixo}: {col.vmp_texto}").classes(
                                                "font-mono-lt text-[12px] text-[#71717A]"
                                            )
                                            with ui.row().classes("items-center"):
                                                ui.html(
                                                    status_pill_html(col.badge_texto, col.badge_variant),
                                                    sanitize=False,
                                                )
                                            with ui.element("button").props('type="button" title="Abrir conferência da amostra"').classes(
                                                "inline-flex items-center justify-center w-[32px] h-[32px] rounded-[6px] "
                                                "border border-[#E4E4E7] bg-white hover:bg-[#F4F4F5] "
                                                "text-[#111827] transition cursor-pointer"
                                            ).on("click", lambda _, cod=col.codigo_amostra: _abrir_amostra(cod)):
                                                ui.icon("open_in_new", size="16px")

            # --- Handlers ---
            def _recarregar_tudo() -> None:
                estado["inicializado"] = False
                estado["expandidos"] = set()
                estado["mostrar_todas"] = set()
                render_filtros.refresh()
                render_grafico_evolucao.refresh()
                render_tabela_dinamica.refresh()

            def _trocar_cliente(novo_cli: str) -> None:
                estado["cliente"] = novo_cli
                locs = repo.listar_locais_por_cliente(novo_cli)
                estado["local"] = locs[0] if locs else ""
                norms = repo.listar_normas_do_local(novo_cli, estado["local"])
                estado["norma"] = norms[0] if norms else ""
                _recarregar_tudo()

            def _trocar_local(novo_loc: str) -> None:
                estado["local"] = novo_loc
                norms = repo.listar_normas_do_local(estado["cliente"], novo_loc)
                estado["norma"] = norms[0] if norms else ""
                _recarregar_tudo()

            def _trocar_norma(nova_norma: str) -> None:
                estado["norma"] = nova_norma
                _recarregar_tudo()

            def _trocar_periodo(meses: int) -> None:
                estado["periodo_meses"] = meses
                render_grafico_evolucao.refresh()
                render_tabela_dinamica.refresh()

            def _toggle_grupo(cod_ensaio: int) -> None:
                if cod_ensaio in estado["expandidos"]:
                    estado["expandidos"].remove(cod_ensaio)
                else:
                    estado["expandidos"].add(cod_ensaio)
                render_tabela_dinamica.refresh()

            def _toggle_mostrar_todas(cod_ensaio: int) -> None:
                if cod_ensaio in estado["mostrar_todas"]:
                    estado["mostrar_todas"].remove(cod_ensaio)
                else:
                    estado["mostrar_todas"].add(cod_ensaio)
                render_tabela_dinamica.refresh()

            def _abrir_amostra(codigo: str) -> None:
                ui.navigate.to(f"/amostra/{quote(codigo, safe='')}")

            # Renderização inicial
            render_filtros()
            render_grafico_evolucao()
            render_tabela_dinamica()
