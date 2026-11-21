"""Modal OV3 — Histórico de Alterações (RN-10 / Seção 6.6)."""

from __future__ import annotations

from nicegui import ui

from app.core.models import LogAlteracao
from app.ui.components.badges import status_pill_html


def abrir_modal_historico(logs: list[LogAlteracao], codigo_amostra: str) -> None:
    """Abre o modal OV3 fiel ao Figma (69:3152) no formato 'usuário alterou de X para Y'."""
    with ui.dialog() as dialog:
        with ui.card().classes(
            "p-0 rounded-[12px] border border-[#E4E4E7] bg-white overflow-hidden"
        ).style("width: 600px; max-width: 92vw; box-shadow: 0 14px 34px -4px rgba(17,24,39,0.18);"):
            # Cabeçalho do Modal
            with ui.row().classes(
                "w-full items-center justify-between px-[24px] py-[16px] border-b border-[#E4E4E7] no-wrap"
            ):
                with ui.column().classes("gap-[2px]"):
                    ui.label("Histórico de Alterações").classes(
                        "text-[17px] font-bold text-[#111827] leading-tight"
                    )
                    ui.label(f"Amostra {codigo_amostra} · trilha imutável RN-10").classes(
                        "text-[11px] text-[#71717A]"
                    )
                ui.button(icon="close", on_click=dialog.close).props(
                    "flat round dense"
                ).classes("text-[#52525B]")

            # Lista de alterações
            with ui.column().classes(
                "w-full gap-[12px] px-[24px] py-[20px] max-h-[60vh] overflow-y-auto"
            ):
                if not logs:
                    with ui.column().classes("w-full items-center py-[28px] gap-[8px]"):
                        ui.icon("history", size="32px", color="#A1A1AA")
                        ui.label("Nenhuma alteração manual registrada para esta amostra.").classes(
                            "text-[13px] text-[#71717A]"
                        )
                else:
                    for lg in logs:
                        if lg.campo_alterado == "conformidade":
                            pill = status_pill_html("ENSAIO", "outline-gray")
                            titulo_item = f"Ensaio {lg.ensaio_codigo} — {lg.ensaio_nome}"
                        elif lg.campo_alterado == "parecer_geral":
                            pill = status_pill_html("PARECER GERAL", "outline-amber")
                            titulo_item = "Status Geral da Amostra (derivado)"
                        else:
                            pill = status_pill_html("PARECER", "outline-amber")
                            titulo_item = "Texto do Parecer Técnico (Minuta)"

                        with ui.column().classes(
                            "w-full bg-[#FAFAFA] border border-[#E4E4E7] rounded-[8px] px-[16px] py-[14px] gap-[6px]"
                        ):
                            with ui.row().classes("w-full items-center justify-between no-wrap"):
                                with ui.row().classes("items-center gap-[8px] no-wrap"):
                                    ui.icon("schedule", size="14px", color="#71717A")
                                    ui.label(lg.data_alteracao.strftime("%d/%m/%Y %H:%M")).classes(
                                        "font-mono-lt text-[12px] font-semibold text-[#111827]"
                                    )
                                    ui.label("·").classes("text-[12px] text-[#71717A]")
                                    ui.label(lg.usuario).classes(
                                        "text-[12px] font-semibold text-[#111827]"
                                    )
                                ui.html(pill, sanitize=False)

                            ui.label(titulo_item).classes("text-[13px] font-semibold text-[#111827]")

                            # Formato obrigatório da Seção 6.6: "usuário alterou de X para Y"
                            resumo_ant = (
                                lg.valor_anterior
                                if len(lg.valor_anterior) <= 95
                                else lg.valor_anterior[:92] + "..."
                            )
                            resumo_novo = (
                                lg.valor_novo
                                if len(lg.valor_novo) <= 95
                                else lg.valor_novo[:92] + "..."
                            )
                            ui.label(
                                f"{lg.usuario} alterou de '{resumo_ant}' para '{resumo_novo}'"
                            ).classes("text-[12px] font-medium text-[#111827] leading-snug")

                            if lg.observacao:
                                ui.label(f"Observação: '{lg.observacao}'").classes(
                                    "text-[12px] text-[#52525B] leading-snug"
                                )

            # Rodapé
            with ui.row().classes(
                "w-full items-center justify-between px-[24px] py-[14px] bg-[#FAFAFA] border-t border-[#E4E4E7]"
            ):
                ui.button("Fechar", on_click=dialog.close).classes("lt-btn-primary")
                ui.label(f"{len(logs)} registro(s)").classes("text-[11px] text-[#71717A]")

    dialog.open()
