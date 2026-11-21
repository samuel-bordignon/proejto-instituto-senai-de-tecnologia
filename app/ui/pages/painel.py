"""Tela B2 — Painel de Conferência (/) conforme POC Seção 6.3 (sem KPIs, sem filtros Cliente/Origem)."""

from __future__ import annotations

from urllib.parse import quote

from nicegui import ui

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    GERAL_PENDENTE,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.models import Amostra
from app.repo.mock_repo import repo
from app.ui.components.badges import status_pill_html
from app.ui.layout import criar_shell


def _montar_pills_diagnostico(amostra: Amostra) -> str:
    """Monta múltiplas pills StatusPillV3 para a coluna Diagnóstico da B2."""
    pills: list[str] = []

    qtd_nc = sum(1 for e in amostra.ensaios if e.status == STATUS_NAO_CONFORME)
    qtd_pend = sum(1 for e in amostra.ensaios if e.status == STATUS_PENDENTE)
    tem_desvio = any(e.estatistica and e.estatistica.alerta_desvio for e in amostra.ensaios)
    tem_unid_div = any(
        any(av.motivo == "UNIDADE_DIVERGENTE" for av in e.avaliacoes.values())
        for e in amostra.ensaios
    )

    if qtd_nc > 0:
        label = f"{qtd_nc} NÃO CONFORME" if qtd_nc == 1 else f"{qtd_nc} NÃO CONFORMES"
        pills.append(status_pill_html(label, "solid-red"))
    elif qtd_pend == 0:
        pills.append(status_pill_html("FAVORÁVEL", "solid-green"))

    if qtd_pend > 0:
        label = f"{qtd_pend} PENDENTE" if qtd_pend == 1 else f"{qtd_pend} PENDENTES"
        pills.append(status_pill_html(label, "solid-amber" if qtd_nc == 0 else "outline-amber"))

    if tem_unid_div:
        pills.append(status_pill_html("UNID. DIVERGENTE", "outline-gray"))

    if tem_desvio:
        pills.append(status_pill_html("DESVIO > μ+0,20σ", "outline-amber"))

    return '<div class="flex flex-wrap items-center gap-[6px]">' + "".join(pills) + "</div>"


def _serializar_linhas(amostras: list[Amostra]) -> list[dict]:
    rows = []
    for a in amostras:
        rows.append(
            {
                "codigo": a.codigo,
                "data_coleta": a.data_coleta.strftime("%d/%m/%Y"),
                "cliente": a.cliente,
                "local_coleta": a.local_coleta,
                "origem": a.origem,
                "normas": a.normas_resumo,
                "diagnostico_html": _montar_pills_diagnostico(a),
            }
        )
    return rows


def registrar_pagina_painel() -> None:
    @ui.page("/")
    def pagina_painel() -> None:
        criar_shell(aba_ativa="painel")

        estado = {"status": "Todos", "busca": ""}

        with ui.column().classes(
            "w-full max-w-[1360px] mx-auto px-[24px] lg:px-[32px] py-[28px] gap-[20px]"
        ):
            # Cabeçalho da página (Sem KPIs — D1, D6, Seção 6.3)
            with ui.row().classes("w-full items-center justify-between gap-[16px]"):
                ui.label("Painel de Conferência").classes(
                    "text-[24px] font-bold text-[#111827] leading-tight"
                )
                ui.button(
                    "Importar Amostra",
                    icon="upload",
                    on_click=lambda: ui.navigate.to("/importar"),
                ).classes("lt-btn-primary")

            # Barra de filtros enxuta (Seção 6.3: somente Status + Busca por código)
            with ui.row().classes(
                "w-full lt-card px-[16px] py-[12px] items-center justify-between gap-[12px] flex-wrap"
            ):
                with ui.row().classes("items-center gap-[12px] flex-wrap"):
                    sel_status = (
                        ui.select(
                            options=["Todos", GERAL_FAVORAVEL, GERAL_NAO_FAVORAVEL, GERAL_PENDENTE],
                            value="Todos",
                            label="Status",
                            on_change=lambda e: _atualizar_filtro("status", e.value),
                        )
                        .props("outlined dense options-dense")
                        .classes("w-[190px] lt-field")
                    )

                    inp_busca = (
                        ui.input(
                            placeholder="Buscar amostra (ex: 63450/2026)...",
                            on_change=lambda e: _atualizar_filtro("busca", e.value or ""),
                        )
                        .props("outlined dense clearable")
                        .classes("w-[310px] lt-field")
                    )
                    with inp_busca.add_slot("prepend"):
                        ui.icon("search", size="18px", color="#71717A")

                contador_label = ui.label("").classes("text-[12px] text-[#71717A]")

            # Tabela de amostras (6 colunas exatas da Seção 6.3 e Figma 69:1699)
            columns = [
                {"name": "amostra", "label": "Amostra / Coleta", "field": "codigo", "align": "left"},
                {"name": "cliente_local", "label": "Cliente e Local de Coleta", "field": "cliente", "align": "left"},
                {"name": "origem", "label": "Origem", "field": "origem", "align": "left"},
                {"name": "normas", "label": "Normas e Classes", "field": "normas", "align": "left"},
                {"name": "diagnostico", "label": "Diagnóstico", "field": "diagnostico_html", "align": "left"},
                {"name": "abrir", "label": "Abrir", "field": "codigo", "align": "right"},
            ]

            tabela = (
                ui.table(
                    columns=columns,
                    rows=[],
                    row_key="codigo",
                    pagination={"rowsPerPage": 0},
                )
                .props("flat hide-bottom")
                .classes("w-full lt-table")
            )

            tabela.add_slot(
                "body",
                r"""
                <q-tr :props="props" class="cursor-pointer" @click="$parent.$emit('open_sample', props.row.codigo)">
                  <q-td key="amostra" :props="props" style="min-width:136px;">
                    <div class="flex flex-col gap-[2px]">
                      <span class="font-mono-lt text-[13px] font-bold text-[#111827]">{{ props.row.codigo }}</span>
                      <span class="font-mono-lt text-[11px] text-[#71717A]">{{ props.row.data_coleta }}</span>
                    </div>
                  </q-td>
                  <q-td key="cliente_local" :props="props" style="min-width:240px;">
                    <div class="flex flex-col gap-[2px]">
                      <span class="text-[13px] font-semibold text-[#111827]">{{ props.row.cliente }}</span>
                      <span class="text-[12px] text-[#52525B]">{{ props.row.local_coleta }}</span>
                    </div>
                  </q-td>
                  <q-td key="origem" :props="props" style="min-width:132px;">
                    <span class="text-[12px] text-[#111827]">{{ props.row.origem }}</span>
                  </q-td>
                  <q-td key="normas" :props="props" style="min-width:220px;">
                    <span class="text-[12px] font-medium text-[#111827]">{{ props.row.normas }}</span>
                  </q-td>
                  <q-td key="diagnostico" :props="props" style="min-width:260px;">
                    <div v-html="props.row.diagnostico_html"></div>
                  </q-td>
                  <q-td key="abrir" :props="props" class="text-right" style="width:70px;">
                    <button
                      type="button"
                      title="Abrir conferência da amostra"
                      @click.stop="$parent.$emit('open_sample', props.row.codigo)"
                      class="inline-flex items-center justify-center w-[32px] h-[32px] rounded-[6px]
                             border border-[#E4E4E7] bg-white hover:bg-[#F4F4F5] hover:border-[#D4D4D8]
                             text-[#111827] transition cursor-pointer"
                    >
                      <span class="material-icons" style="font-size:16px;">open_in_new</span>
                    </button>
                  </q-td>
                </q-tr>
                """,
            )

            def _abrir_amostra(e) -> None:
                codigo = str(e.args)
                ui.navigate.to(f"/amostra/{quote(codigo, safe='')}")

            tabela.on("open_sample", _abrir_amostra)

            def _recarregar_tabela() -> None:
                amostras = repo.listar_amostras(
                    status_filtro=estado["status"],
                    busca=estado["busca"],
                )
                tabela.rows = _serializar_linhas(amostras)
                tabela.update()
                qtd = len(amostras)
                contador_label.set_text(
                    f"{qtd} amostra encontrada" if qtd == 1 else f"{qtd} amostras encontradas"
                )

            def _atualizar_filtro(chave: str, valor: str) -> None:
                estado[chave] = valor
                _recarregar_tabela()

            _recarregar_tabela()
