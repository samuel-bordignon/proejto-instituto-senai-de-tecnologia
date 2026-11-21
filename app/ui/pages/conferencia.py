"""Tela B4 — Conferência da Amostra (/amostra/{codigo}) conforme POC Seções 5.1–5.5, 6.5, 6.6, 8.3 e 8.6."""

from __future__ import annotations

from urllib.parse import quote, unquote

from nicegui import ui

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.models import Amostra, EnsaioResultado
from app.core.motor_conformidade import (
    calcular_status_geral,
    definir_sinalizacao_ensaio,
    gerar_parecer_automatico,
)
from app.repo.mock_repo import repo
from app.services.pdf_service import gerar_pdf_amostra
from app.ui.auth import obter_usuario_logado
from app.ui.components.badges import status_pill_html, variante_status_geral
from app.ui.components.barra_lote import (
    ItemAbaAmostra,
    limpar_lote_sessao,
    obter_lote_sessao,
    renderizar_barra_abas_amostras,
)
from app.ui.components.grafico_historico import construir_figura_historico
from app.ui.components.modal_historico import abrir_modal_historico
from app.ui.components.tabela_ensaios import (
    criar_tabela_ensaios,
    montar_rows_tabela_ensaios,
)
from app.ui.layout import criar_shell, mostrar_toast_aviso, mostrar_toast_sucesso


def _escolher_ensaio_inicial(amostra: Amostra) -> int:
    """Seleciona prioritariamente o ensaio com desvio histórico ou violação (ex: 106 na 63450/2026)."""
    for e in amostra.ensaios:
        if e.estatistica and e.estatistica.alerta_desvio:
            return e.codigo
    for e in amostra.ensaios:
        if e.status == STATUS_NAO_CONFORME:
            return e.codigo
    for e in amostra.ensaios:
        if e.status == STATUS_PENDENTE:
            return e.codigo
    return amostra.ensaios[0].codigo if amostra.ensaios else 0


def registrar_pagina_conferencia() -> None:
    @ui.page("/amostra/{codigo:path}")
    def pagina_conferencia(codigo: str) -> None:
        criar_shell(aba_ativa="painel")

        codigo_decod = unquote(codigo)
        amostra = repo.obter_amostra(codigo_decod)

        if not amostra:
            with ui.column().classes(
                "w-full max-w-[900px] mx-auto px-[32px] py-[48px] items-center gap-[16px]"
            ):
                ui.icon("error_outline", size="42px", color="#DC2626")
                ui.label(f"Amostra '{codigo_decod}' não encontrada.").classes(
                    "text-[18px] font-bold text-[#111827]"
                )
                ui.button("Voltar ao Painel", on_click=lambda: ui.navigate.to("/")).classes(
                    "lt-btn-primary"
                )
            return

        usuario_atual = (obter_usuario_logado() or {}).get("nome_usuario", "samuel.wiegand")

        estado: dict = {
            "amostra": amostra,
            "ensaio_selecionado": _escolher_ensaio_inicial(amostra),
            "dirty": False,
        }

        def _obter_ensaio(cod_e: int) -> EnsaioResultado:
            for item in estado["amostra"].ensaios:
                if item.codigo == cod_e:
                    return item
            return estado["amostra"].ensaios[0]

        # Barra de abas de lote logo abaixo do header (quando veio de importação multi-amostra)
        lote_sessao = obter_lote_sessao(codigo_decod)
        if lote_sessao:
            itens_lote: list[ItemAbaAmostra] = []
            for cod_lote in lote_sessao:
                am_tab = repo.obter_amostra(cod_lote)
                st_g = am_tab.status_geral if am_tab else "Pendente"
                cor_tab = (
                    "#16A34A"
                    if st_g == GERAL_FAVORAVEL
                    else ("#DC2626" if st_g == GERAL_NAO_FAVORAVEL else "#D97706")
                )
                itens_lote.append(ItemAbaAmostra(codigo=cod_lote, cor_dot=cor_tab))

            def _fechar_barra_lote() -> None:
                limpar_lote_sessao()
                ui.navigate.to(f"/amostra/{quote(codigo_decod, safe='')}")

            renderizar_barra_abas_amostras(
                titulo_prefixo="LOTE IMPORTADO",
                itens=itens_lote,
                valor_ativo=codigo_decod,
                on_select=lambda novo_cod: (
                    ui.navigate.to(f"/amostra/{quote(novo_cod, safe='')}")
                    if novo_cod != codigo_decod
                    else None
                ),
                on_close=_fechar_barra_lote,
            )

        with ui.column().classes(
            "w-full max-w-[1360px] mx-auto px-[24px] lg:px-[32px] py-[24px] gap-[18px]"
        ):
            # 1. Cabeçalho de Ações (Voltar, Código, Histórico, PDF, Salvar)
            @ui.refreshable
            def render_cabecalho() -> None:
                am: Amostra = estado["amostra"]
                with ui.row().classes(
                    "w-full items-center justify-between gap-[16px] flex-wrap"
                ):
                    with ui.row().classes("items-center gap-[14px] flex-wrap"):
                        ui.button(
                            "Painel",
                            icon="arrow_back",
                            color="white",
                            on_click=lambda: ui.navigate.to("/"),
                        ).props("unelevated no-caps").classes("lt-btn-secondary")

                        with ui.column().classes("gap-[1px]"):
                            with ui.row().classes("items-center gap-[10px] no-wrap"):
                                ui.label(f"Amostra {am.codigo}").classes(
                                    "font-mono-lt text-[22px] font-bold text-[#111827] leading-tight"
                                )
                                if estado["dirty"]:
                                    ui.html(
                                        status_pill_html("ALTERAÇÕES NÃO SALVAS", "outline-amber"),
                                        sanitize=False,
                                    )
                            ui.label(
                                f"{am.cliente} · {am.local_coleta} · {am.origem} · Coleta {am.data_coleta.strftime('%d/%m/%Y')}"
                            ).classes("text-[12px] text-[#71717A]")

                    with ui.row().classes("items-center gap-[10px] flex-wrap"):
                        ui.button(
                            f"Histórico ({len(am.logs)})",
                            icon="history",
                            color="white",
                            on_click=lambda: abrir_modal_historico(
                                estado["amostra"].logs, estado["amostra"].codigo
                            ),
                        ).props("unelevated no-caps").classes("lt-btn-secondary")

                        ui.button(
                            "Exportar PDF",
                            icon="description",
                            color="white",
                            on_click=lambda: _exportar_pdf(),
                        ).props("unelevated no-caps").classes("lt-btn-secondary")

                        ui.button(
                            "Salvar Conferência",
                            icon="save",
                            on_click=lambda: _salvar_conferencia(),
                        ).props("unelevated no-caps").classes("lt-btn-primary")

            # 2. Card Gráfico Histórico por Ensaio (ui.plotly + linha de μ)
            @ui.refreshable
            def render_card_grafico() -> None:
                ensaio = _obter_ensaio(estado["ensaio_selecionado"])
                fig, meta = construir_figura_historico(ensaio)
                unid_txt = f" ({ensaio.unidade_trabalho})" if ensaio.unidade_trabalho else ""

                with ui.column().classes("w-full lt-card px-[20px] pt-[16px] pb-[10px] gap-[6px]"):
                    with ui.row().classes(
                        "w-full items-center justify-between gap-[12px] flex-wrap"
                    ):
                        with ui.row().classes("items-center gap-[10px] flex-wrap"):
                            ui.label(
                                f"Desvio Histórico · {ensaio.codigo} — {ensaio.nome}{unid_txt}"
                            ).classes("text-[15px] font-bold text-[#111827]")
                            if ensaio.sinalizacao and ensaio.sinalizacao_tipo:
                                ui.html(
                                    status_pill_html(
                                        ensaio.sinalizacao,
                                        f"outline-{ensaio.sinalizacao_tipo}",  # type: ignore[arg-type]
                                    ),
                                    sanitize=False,
                                )

                        with ui.row().classes("items-center gap-[16px] flex-wrap"):
                            for rotulo, valor in [
                                ("Média (μ):", meta["media"]),
                                ("Desvio (σ):", meta["sigma"]),
                                ("Limiar μ+0,20σ:", meta["limiar"]),
                                (meta["vmp_label"], meta["vmp_texto"]),
                            ]:
                                with ui.row().classes("items-baseline gap-[4px] no-wrap"):
                                    ui.label(rotulo).classes("text-[12px] text-[#71717A]")
                                    ui.label(valor).classes(
                                        "font-mono-lt text-[12px] font-bold text-[#111827]"
                                    )

                    if meta.get("aviso_historico"):
                        with ui.row().classes(
                            "w-full items-center gap-[8px] bg-[#FFFBEB] border border-[#FDE68A] "
                            "rounded-[6px] px-[12px] py-[6px] mt-[4px]"
                        ):
                            ui.icon("info", size="15px", color="#D97706")
                            ui.label(meta["aviso_historico"]).classes(
                                "text-[12px] text-[#92400E]"
                            )

                    fig_dict = fig.to_plotly_json()
                    fig_dict["config"] = {"displayModeBar": False, "responsive": True}
                    ui.plotly(fig_dict).classes("w-full")

            render_cabecalho()
            render_card_grafico()

            # 3. Tabela de Ensaios (1–3 normas, clique na linha + menu Status + observação inline)
            tabela = criar_tabela_ensaios(
                amostra=amostra,
                ensaio_selecionado=estado["ensaio_selecionado"],
                on_select_row=lambda e: _ao_selecionar_linha(e),
                on_status_change=lambda e: _ao_mudar_status(e),
                on_obs_change=lambda e: _ao_mudar_observacao(e),
            )

            # 4. Card Conclusão da Amostra (Parecer Técnico Editável)
            @ui.refreshable
            def render_card_parecer() -> None:
                am: Amostra = estado["amostra"]
                variante_g = variante_status_geral(am.status_geral)
                pill_geral = status_pill_html(
                    f"PARECER: {am.status_geral.upper()}", variante_g
                )

                with ui.column().classes("w-full lt-card px-[20px] py-[18px] gap-[12px]"):
                    with ui.row().classes("w-full items-center justify-between gap-[12px] flex-wrap"):
                        with ui.row().classes("items-center gap-[12px] flex-wrap"):
                            ui.label("Conclusão da Amostra (Parecer Técnico)").classes(
                                "text-[15px] font-bold text-[#111827]"
                            )
                            ui.html(pill_geral, sanitize=False)
                        ui.label(
                            "Status geral derivado automaticamente dos ensaios (Seção 5.1)"
                        ).classes("text-[11px] text-[#71717A]")

                    def _ao_editar_parecer(e) -> None:
                        novo_txt = e.value or ""
                        if novo_txt != estado["amostra"].parecer:
                            estado["amostra"].parecer = novo_txt
                            if not estado["dirty"]:
                                estado["dirty"] = True
                                render_cabecalho.refresh()

                    ui.textarea(
                        value=am.parecer,
                        on_change=_ao_editar_parecer,
                    ).props("outlined autogrow").classes(
                        "w-full lt-textarea text-[13px] text-[#111827]"
                    )

            # --- Handlers ---
            def _sincronizar_tabela() -> None:
                tabela.rows = montar_rows_tabela_ensaios(
                    estado["amostra"], estado["ensaio_selecionado"]
                )
                tabela.update()

            def _ao_selecionar_linha(e) -> None:
                cod = int(e.args)
                if cod != estado["ensaio_selecionado"]:
                    estado["ensaio_selecionado"] = cod
                    _sincronizar_tabela()
                    render_card_grafico.refresh()

            def _ao_mudar_status(e) -> None:
                payload = e.args
                cod = int(payload["codigo"])
                novo_status = str(payload["status"])
                ensaio = _obter_ensaio(cod)
                if ensaio.status == novo_status:
                    return

                ensaio.status = novo_status  # type: ignore[assignment]
                sinal, sinal_tipo = definir_sinalizacao_ensaio(ensaio)
                ensaio.sinalizacao = sinal
                ensaio.sinalizacao_tipo = sinal_tipo  # type: ignore[arg-type]

                estado["amostra"].status_geral = calcular_status_geral(estado["amostra"].ensaios)  # type: ignore[assignment]
                estado["amostra"].parecer = gerar_parecer_automatico(estado["amostra"])
                estado["dirty"] = True

                _sincronizar_tabela()
                render_cabecalho.refresh()
                render_card_parecer.refresh()
                if cod == estado["ensaio_selecionado"]:
                    render_card_grafico.refresh()

            def _ao_mudar_observacao(e) -> None:
                payload = e.args
                cod = int(payload["codigo"])
                nova_obs = str(payload.get("obs", "")).strip()
                ensaio = _obter_ensaio(cod)
                if ensaio.observacao != nova_obs:
                    ensaio.observacao = nova_obs
                    if not estado["dirty"]:
                        estado["dirty"] = True
                        render_cabecalho.refresh()

            def _salvar_conferencia() -> None:
                am: Amostra = estado["amostra"]
                ed_status = {e.codigo: e.status for e in am.ensaios}
                ed_obs = {e.codigo: e.observacao for e in am.ensaios}

                amostra_salva, qtd_logs = repo.salvar_conferencia(
                    codigo=am.codigo,
                    edicoes_status=ed_status,
                    edicoes_obs=ed_obs,
                    novo_parecer=am.parecer,
                    usuario=usuario_atual,
                )
                estado["amostra"] = amostra_salva
                estado["dirty"] = False

                _sincronizar_tabela()
                render_cabecalho.refresh()
                render_card_parecer.refresh()
                render_card_grafico.refresh()

                if qtd_logs > 0:
                    mostrar_toast_sucesso("Alteração salva e registrada no log")
                else:
                    mostrar_toast_aviso("Nenhuma alteração pendente para salvar.")

            def _exportar_pdf() -> None:
                am: Amostra = estado["amostra"]
                pdf_bytes = gerar_pdf_amostra(am)
                nome_seguro = am.codigo.replace("/", "_").replace(" ", "_")
                ui.download(
                    pdf_bytes,
                    filename=f"LaudoTech_Parecer_{nome_seguro}.pdf",
                    media_type="application/pdf",
                )
                mostrar_toast_sucesso("Arquivo exportado com sucesso")

            render_card_parecer()
