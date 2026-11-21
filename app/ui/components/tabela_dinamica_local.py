"""Tabela Dinâmica Agrupada por Ensaio (Accordion / Pivot) da Tela B5 (/analise)."""

from __future__ import annotations

from typing import Callable

from nicegui import ui

from app.core.models import GrupoEnsaioLocal
from app.ui.components.badges import status_pill_html


def renderizar_tabela_dinamica_local(
    grupos: list[GrupoEnsaioLocal],
    periodo_meses: int,
    expandidos: set[int],
    mostrar_todas: set[int],
    on_toggle_grupo: Callable[[int], None],
    on_toggle_mostrar_todas: Callable[[int], None],
    on_abrir_amostra: Callable[[str], None],
) -> None:
    """Renderiza a tabela dinâmica de 6 colunas com expansão das últimas 3 ou todas as coletas."""
    rotulo_media = f"Média ({periodo_meses}m)"

    with ui.column().classes("w-full lt-card overflow-hidden gap-0"):
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
            is_exp = g.codigo_ensaio in expandidos
            border_cls = "border-t border-[#E4E4E7]" if idx_g > 0 else ""

            with ui.element("div").classes(
                f"w-full grid items-center px-[20px] py-[14px] cursor-pointer "
                f"transition hover:bg-[#F8FAFC] {border_cls} "
                + ("bg-[#FAFAFA]" if is_exp else "bg-white")
            ).style(
                "grid-template-columns: 2.3fr 0.7fr 1.1fr 1fr 0.9fr 1.4fr; gap: 12px;"
            ).on("click", lambda _, cod=g.codigo_ensaio: on_toggle_grupo(cod)):
                with ui.row().classes("items-center gap-[8px] no-wrap"):
                    ui.icon(
                        "keyboard_arrow_down" if is_exp else "keyboard_arrow_right",
                        size="18px",
                        color="#52525B",
                    )
                    ui.label(f"{g.codigo_ensaio} — {g.nome_ensaio}").classes(
                        "text-[13px] font-bold text-[#111827]"
                    )

                ui.label(str(g.total_coletas)).classes("font-mono-lt text-[12px] text-[#111827]")
                ui.label(g.media_texto).classes("font-mono-lt text-[12px] text-[#111827]")
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

            if is_exp:
                ver_todas = g.codigo_ensaio in mostrar_todas
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
                            ).on("click", lambda _, cod=g.codigo_ensaio: on_toggle_mostrar_todas(cod))

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
                                with ui.element("button").props(
                                    'type="button" title="Abrir conferência da amostra"'
                                ).classes(
                                    "inline-flex items-center justify-center w-[32px] h-[32px] rounded-[6px] "
                                    "border border-[#E4E4E7] bg-white hover:bg-[#F4F4F5] "
                                    "text-[#111827] transition cursor-pointer"
                                ).on("click", lambda _, cod=col.codigo_amostra: on_abrir_amostra(cod)):
                                    ui.icon("open_in_new", size="16px")
