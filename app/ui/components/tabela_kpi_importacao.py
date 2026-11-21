"""Cards KPI clicáveis e Tabela Dinâmica de Conferência por KPI da Tela B3 (/importar)."""

from __future__ import annotations

from typing import Callable, Optional

from nicegui import ui

from app.core.models import ResultadoPreLeitura
from app.ui.components.badges import status_pill_html

KPI_DEFINICOES = [
    ("mapeados", "Ensaios mapeados", "MAPEADOS", "#16A34A", "Encontrados no catálogo UltraLIMS"),
    ("sem_vmp", "Sem VMP na norma", "SEM VMP", "#71717A", "Armazenados sem avaliação legal"),
    ("ignorados", "Ignorados (RN-02)", "IGNORADOS", "#71717A", "Não analisados (______) e controle SVOC"),
    ("avisos", "Avisos de revisão", "ATENÇÃO", "#D97706", "Formatação, RN-01 e divergência de unidade"),
]


def renderizar_kpis_e_tabela_dinamica(
    pre: ResultadoPreLeitura,
    kpi_foco: Optional[str],
    kpis_expandidos: set[str],
    on_focar_kpi: Callable[[str], None],
    on_toggle_grupo: Callable[[str], None],
    on_expandir_todos: Callable[[], None],
    on_recolher_todos: Callable[[], None],
) -> None:
    """Renderiza os 4 KPIs clicáveis e a tabela dinâmica por KPI com todos os registros captados."""
    contagens = {
        "mapeados": pre.total_mapeados,
        "sem_vmp": pre.total_sem_vmp,
        "ignorados": pre.total_ignorados,
        "avisos": pre.total_avisos,
    }

    with ui.row().classes("w-full gap-[14px] flex-wrap"):
        for kpi_key, titulo, tag, cor_dot, subtitulo in KPI_DEFINICOES:
            ativo = kpi_foco == kpi_key
            card_cls = (
                "flex-1 min-w-[200px] bg-white border border-[#E4E4E7] rounded-[8px] "
                "px-[18px] py-[14px] gap-[6px] lt-kpi-clickable "
                + ("lt-kpi-active" if ativo else "")
            )
            with ui.column().classes(card_cls).on(
                "click", lambda _, k=kpi_key: on_focar_kpi(k)
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

    total_itens_captados = sum(len(pre.itens_por_kpi.get(k, [])) for k, *_ in KPI_DEFINICOES)
    with ui.column().classes(
        "w-full border border-[#E4E4E7] rounded-[8px] overflow-hidden gap-0"
    ):
        with ui.row().classes(
            "w-full items-center justify-between px-[18px] py-[12px] bg-white border-b border-[#E4E4E7] flex-wrap gap-[10px]"
        ):
            with ui.column().classes("gap-[2px]"):
                ui.label("Tabela Dinâmica de Conferência por KPI").classes(
                    "text-[13px] font-bold text-[#111827]"
                )
                ui.label(
                    f"Expanda qualquer KPI acima ou abaixo para inspecionar todos os {total_itens_captados} registros captados da amostra {pre.codigo_amostra_principal}."
                ).classes("text-[11px] text-[#71717A]")

            with ui.row().classes("items-center gap-[8px]"):
                ui.button(
                    "Expandir todos",
                    color="white",
                    on_click=on_expandir_todos,
                ).props("unelevated no-caps dense").classes(
                    "lt-btn-secondary text-[11px] h-[30px] px-[10px]"
                )
                ui.button(
                    "Recolher todos",
                    color="white",
                    on_click=on_recolher_todos,
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

        for idx_k, (kpi_key, titulo, tag, cor_dot, subtitulo) in enumerate(KPI_DEFINICOES):
            itens = pre.itens_por_kpi.get(kpi_key, [])
            is_exp = kpi_key in kpis_expandidos
            b_top = "border-t border-[#E4E4E7]" if idx_k > 0 else ""

            with ui.element("div").classes(
                f"w-full grid items-center px-[18px] py-[12px] cursor-pointer "
                f"transition hover:bg-[#F8FAFC] {b_top} "
                + ("bg-[#F8FBFF]" if is_exp else "bg-white")
            ).style("grid-template-columns: 2.2fr 0.8fr 2.4fr 0.7fr; gap: 12px;").on(
                "click", lambda _, k=kpi_key: on_toggle_grupo(k)
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
