"""Seção 2 da Tela B3 (/importar): Contexto Comercial e Seletor de 1 a 3 Legislações/Classes."""

from __future__ import annotations

from typing import Callable

from nicegui import ui


def renderizar_secao_contexto_e_normas(
    n_amostras: int,
    cliente: str,
    proposta: str,
    local: str,
    origem: str,
    normas: list[dict],
    clientes: list[str],
    propostas_disp: list[str],
    locais_disp: list[str],
    origens: list[str],
    legs_compativeis: list[dict],
    listar_classes_fn: Callable[[str], list[str]],
    on_trocar_cliente: Callable[[str], None],
    on_trocar_proposta: Callable[[str], None],
    on_trocar_local: Callable[[str], None],
    on_trocar_origem: Callable[[str], None],
    on_adicionar_norma: Callable[[], None],
    on_remover_norma: Callable[[int], None],
    on_trocar_legislacao: Callable[[int, str], None],
    on_trocar_classe: Callable[[int, str], None],
    on_cancelar: Callable[[], None],
    on_confirmar: Callable[[], None],
) -> None:
    """Renderiza os cards de Contexto Comercial (2x2), Legislações/Classes (1..3) e rodapé de ação."""
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

            with ui.grid(columns=2).classes("w-full gap-[16px]"):
                with ui.column().classes("gap-[6px] w-full"):
                    ui.label("Cliente").classes("text-[12px] font-semibold text-[#111827]")
                    ui.select(
                        options=clientes,
                        value=cliente,
                        on_change=lambda e: on_trocar_cliente(e.value),
                    ).props("outlined dense options-dense").classes("w-full lt-field")

                with ui.column().classes("gap-[6px] w-full"):
                    ui.label("Proposta Comercial").classes("text-[12px] font-semibold text-[#111827]")
                    ui.select(
                        options=propostas_disp,
                        value=proposta,
                        on_change=lambda e: on_trocar_proposta(e.value),
                    ).props("outlined dense options-dense").classes("w-full lt-field")

                with ui.column().classes("gap-[6px] w-full"):
                    ui.label("Local de Coleta").classes("text-[12px] font-semibold text-[#111827]")
                    ui.select(
                        options=locais_disp,
                        value=local,
                        on_change=lambda e: on_trocar_local(e.value),
                    ).props("outlined dense options-dense").classes("w-full lt-field")

                with ui.column().classes("gap-[6px] w-full"):
                    ui.label(
                        "Origem da Amostra (filtra legislações compatíveis)"
                    ).classes("text-[12px] font-semibold text-[#111827]")
                    ui.select(
                        options=origens,
                        value=origem,
                        on_change=lambda e: on_trocar_origem(e.value),
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

                if len(normas) >= 3:
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
                        on_click=on_adicionar_norma,
                    ).props("outline no-caps").classes(
                        "rounded-[6px] text-[12px] font-semibold text-[#004B8D]"
                    ).style("height: 36px; border-color: #004B8D;")

            opcoes_legs = {m["sigla"]: m["nome_completo"] for m in legs_compativeis}
            siglas_disp = list(opcoes_legs.keys())

            for idx, item_norma in enumerate(normas):
                if item_norma["sigla"] not in siglas_disp and siglas_disp:
                    item_norma["sigla"] = siglas_disp[0]
                    cl_disp = listar_classes_fn(item_norma["sigla"])
                    item_norma["classe"] = cl_disp[0] if cl_disp else None

                classes_disp = listar_classes_fn(item_norma["sigla"])
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
                        on_change=lambda e, i=idx: on_trocar_legislacao(i, e.value),
                    ).props("outlined dense options-dense").classes("flex-1 lt-field")

                    if classes_disp:
                        opcoes_cl = {c: f"Classe: {c}" for c in classes_disp}
                        ui.select(
                            options=opcoes_cl,
                            value=item_norma["classe"],
                            on_change=lambda e, i=idx: on_trocar_classe(i, e.value),
                        ).props("outlined dense options-dense").classes("flex-1 lt-field")
                    else:
                        ui.input(value="Sem classe (Portaria)").props(
                            "outlined dense disable"
                        ).classes("flex-1 lt-field")

                    btn_del = ui.button(
                        icon="delete_outline",
                        on_click=lambda _, i=idx: on_remover_norma(i),
                    ).props("flat round dense").classes(
                        "text-[#52525B] hover:text-[#DC2626] shrink-0"
                    )
                    if len(normas) <= 1:
                        btn_del.props("disable")

        # Rodapé de confirmação
        with ui.row().classes("w-full items-center justify-between pt-[4px]"):
            ui.button(
                "Cancelar e voltar ao Painel",
                color="white",
                on_click=on_cancelar,
            ).props("unelevated no-caps").classes("lt-btn-secondary")

            lbl_confirm = (
                f"Confirmar e Abrir Conferência ({n_amostras} amostras)"
                if n_amostras > 1
                else "Confirmar e Abrir Conferência"
            )
            ui.button(
                lbl_confirm,
                icon="check",
                on_click=on_confirmar,
            ).props("unelevated no-caps").classes("lt-btn-primary")
