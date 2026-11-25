"""Tela B5 — Análise por Local de Coleta (/analise) com Gráfico de Barras Empilhadas e Tabela Dinâmica."""

from __future__ import annotations

from urllib.parse import quote

from nicegui import ui

from app.core.models import GrupoEnsaioLocal
from app.repo import repo
from app.ui.components.grafico_evolucao import construir_option_evolucao_conformidade
from app.ui.components.tabela_dinamica_local import renderizar_tabela_dinamica_local
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
            "expandidos": set(),
            "mostrar_todas": set(),
            "inicializado": False,
        }

        with ui.column().classes(
            "w-full max-w-[1360px] mx-auto px-[24px] lg:px-[32px] py-[28px] gap-[20px]"
        ):
            ui.label("Análise por Local de Coleta").classes(
                "text-[24px] font-bold text-[#111827] leading-tight"
            )

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

                        with ui.row().classes("items-center gap-[16px] flex-wrap"):
                            for cor_leg, texto_leg in [
                                ("#16A34A", f"Favoráveis ({tot_fav})"),
                                ("#94A3B8", f"Pendentes ({tot_pend})"),
                                ("#DC2626", f"Não favoráveis ({tot_nfav})"),
                            ]:
                                with ui.row().classes("items-center gap-[6px] no-wrap"):
                                    ui.element("div").classes(
                                        "w-[10px] h-[10px] rounded-[2px]"
                                    ).style(f"background-color: {cor_leg};")
                                    ui.label(texto_leg).classes(
                                        "text-[11px] font-medium text-[#52525B]"
                                    )

                    ui.echart(option).classes("w-full h-[250px]")

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

                renderizar_tabela_dinamica_local(
                    grupos=grupos,
                    periodo_meses=estado["periodo_meses"],
                    expandidos=estado["expandidos"],
                    mostrar_todas=estado["mostrar_todas"],
                    on_toggle_grupo=_toggle_grupo,
                    on_toggle_mostrar_todas=_toggle_mostrar_todas,
                    on_abrir_amostra=_abrir_amostra,
                )

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

            render_filtros()
            render_grafico_evolucao()
            render_tabela_dinamica()
