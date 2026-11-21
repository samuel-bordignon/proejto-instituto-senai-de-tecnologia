"""Tela B3 — Importar Planilha UltraLIMS (/importar) com suporte multi-amostra em abas + Tabela Dinâmica por KPI."""

from __future__ import annotations

from urllib.parse import quote

from nicegui import events, ui

from app.core.models import ResultadoPreLeitura, ResultadoPreLeituraLote
from app.repo.demo_fixtures import gerar_lote_demonstracao
from app.repo.mock_repo import repo
from app.ui.components.badges import status_pill_html
from app.ui.components.barra_lote import (
    ItemAbaAmostra,
    definir_lote_sessao,
    renderizar_barra_abas_amostras,
)
from app.ui.components.seletor_normas import renderizar_secao_contexto_e_normas
from app.ui.components.tabela_kpi_importacao import (
    KPI_DEFINICOES,
    renderizar_kpis_e_tabela_dinamica,
)
from app.ui.layout import criar_shell, mostrar_toast_aviso, mostrar_toast_sucesso


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

        estado: dict = {
            "lote": None,
            "amostra_ativa": None,
            "kpis_expandidos": {"avisos", "mapeados"},
            "kpi_foco": None,
            "cliente": cliente_ini,
            "proposta": proposta_ini,
            "local": local_ini,
            "origem": "Efluente Tratado",
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

        @ui.refreshable
        def render_barra_abas_amostras() -> None:
            lote: ResultadoPreLeituraLote | None = estado["lote"]
            if not lote or not lote.amostras:
                return

            itens_abas = [
                ItemAbaAmostra(
                    codigo=am.codigo_amostra_principal,
                    cor_dot="#D97706" if am.total_avisos > 0 else "#16A34A",
                    sufixo=f"({am.total_mapeados})",
                )
                for am in lote.amostras
            ]
            renderizar_barra_abas_amostras(
                titulo_prefixo="AMOSTRAS DO ARQUIVO",
                itens=itens_abas,
                valor_ativo=estado["amostra_ativa"],
                on_select=_trocar_aba_amostra,
                texto_direita=f"{len(lote.amostras)} amostra(s) detectada(s) em {lote.nome_arquivo}",
            )

        render_barra_abas_amostras()

        with ui.column().classes(
            "w-full max-w-[1280px] mx-auto px-[24px] lg:px-[32px] py-[26px] gap-[20px]"
        ):
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

                        renderizar_kpis_e_tabela_dinamica(
                            pre=pre,
                            kpi_foco=estado["kpi_foco"],
                            kpis_expandidos=estado["kpis_expandidos"],
                            on_focar_kpi=_focar_kpi,
                            on_toggle_grupo=_toggle_kpi_grupo,
                            on_expandir_todos=_expandir_todos_kpis,
                            on_recolher_todos=_recolher_todos_kpis,
                        )

            @ui.refreshable
            def render_secao_contexto_normas() -> None:
                lote: ResultadoPreLeituraLote | None = estado["lote"]
                if not lote or not lote.amostras:
                    return

                propostas_disp = repo.listar_propostas(estado["cliente"])
                if estado["proposta"] not in propostas_disp and propostas_disp:
                    estado["proposta"] = propostas_disp[0]

                locais_disp = repo.listar_locais(estado["cliente"], estado["proposta"])
                if estado["local"] not in locais_disp and locais_disp:
                    estado["local"] = locais_disp[0]

                renderizar_secao_contexto_e_normas(
                    n_amostras=len(lote.amostras),
                    cliente=estado["cliente"],
                    proposta=estado["proposta"],
                    local=estado["local"],
                    origem=estado["origem"],
                    normas=estado["normas"],
                    clientes=repo.listar_clientes(),
                    propostas_disp=propostas_disp,
                    locais_disp=locais_disp,
                    origens=repo.listar_origens(),
                    legs_compativeis=repo.listar_legislacoes_por_origem(estado["origem"]),
                    listar_classes_fn=repo.listar_classes_legislacao,
                    on_trocar_cliente=_trocar_cliente,
                    on_trocar_proposta=_trocar_proposta,
                    on_trocar_local=lambda novo_loc: estado.__setitem__("local", novo_loc),
                    on_trocar_origem=_trocar_origem,
                    on_adicionar_norma=_adicionar_norma,
                    on_remover_norma=_remover_norma,
                    on_trocar_legislacao=_trocar_legislacao,
                    on_trocar_classe=_trocar_classe,
                    on_cancelar=lambda: ui.navigate.to("/"),
                    on_confirmar=_confirmar_importacao,
                )

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
                estado["kpis_expandidos"] = {k for k, *_ in KPI_DEFINICOES}
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
                    elif (m["sigla"], None) not in usados:
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
                definir_lote_sessao(codigos_lote)

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

            render_secao_validacao()
            render_secao_contexto_normas()
