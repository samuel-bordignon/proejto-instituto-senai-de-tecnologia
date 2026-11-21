"""Shell global do LaudoTech (Slim Nav Rail 92px + Top Header Bar 56px + Toasts OV5/OV5c)."""

from __future__ import annotations

from nicegui import ui

from app.ui.auth import logout_usuario, obter_usuario_logado
from app.ui.theme import aplicar_tema_global


def mostrar_toast_sucesso(mensagem: str) -> None:
    """Exibe toast escuro no canto superior direito igual aos frames OV5 e OV5c do Figma."""
    ui.notify(
        mensagem,
        position="top-right",
        color="dark",
        icon="check_circle",
        close_button="×",
        timeout=4000,
        classes="lt-toast-dark",
    )


def mostrar_toast_aviso(mensagem: str) -> None:
    ui.notify(
        mensagem,
        position="top-right",
        color="warning",
        icon="warning",
        close_button="×",
        timeout=4000,
    )


def criar_shell(aba_ativa: str = "painel") -> None:
    """
    Monta o layout corporativo oficial da POC (Seção 6.1 & D2):
      - Barra lateral azul (#004B8D) com 92px: Logo, Painel, Importar e Sair (sem 'Análise').
      - Cabeçalho branco (56px): LaudoTech / IST Ambiental · SENAI Blumenau + usuário + iniciais (sem papel).
    """
    aplicar_tema_global()
    user = obter_usuario_logado() or {"nome_usuario": "samuel.wiegand", "iniciais": "SW"}

    def _sair() -> None:
        logout_usuario()
        ui.navigate.to("/login")

    # Left Navigation Rail (92px, #004B8D — Figma 69:1591 + POC Seção 6.1, vai até o topo)
    with ui.left_drawer(value=True, fixed=True, top_corner=True).props(
        "width=92 breakpoint=0 persistent"
    ).classes("lt-nav-rail p-0"):
        with ui.column().classes(
            "w-full h-full items-center justify-between px-[10px] py-[18px] no-wrap"
        ):
            # Topo: Logo + Itens de navegação
            with ui.column().classes("w-full items-center gap-[16px] no-wrap"):
                with ui.element("div").classes(
                    "w-[44px] h-[44px] rounded-[10px] bg-[#1A64A6] flex items-center justify-center "
                    "cursor-pointer overflow-hidden shadow-sm hover:brightness-110 transition"
                ).on("click", lambda: ui.navigate.to("/")):
                    ui.image("/assets/laudotech_logo_icon.png").classes(
                        "w-[34px] h-[34px] object-contain"
                    )

                with ui.column().classes("w-full items-center gap-[8px] no-wrap"):
                    # NAV: Painel
                    cls_painel = "lt-nav-item active" if aba_ativa == "painel" else "lt-nav-item opacity-85"
                    with ui.element("div").classes(cls_painel).on("click", lambda: ui.navigate.to("/")):
                        ui.icon("grid_view", size="20px", color="white")
                        ui.label("Painel").classes(
                            "text-[11px] leading-none text-white "
                            + ("font-semibold" if aba_ativa == "painel" else "font-medium")
                        )

                    # NAV: Importar
                    cls_imp = "lt-nav-item active" if aba_ativa == "importar" else "lt-nav-item opacity-85"
                    with ui.element("div").classes(cls_imp).on("click", lambda: ui.navigate.to("/importar")):
                        ui.icon("upload", size="20px", color="white")
                        ui.label("Importar").classes(
                            "text-[11px] leading-none text-white "
                            + ("font-semibold" if aba_ativa == "importar" else "font-medium")
                        )

                    # NAV: Análise por Local (B5)
                    cls_an = "lt-nav-item active" if aba_ativa == "analise" else "lt-nav-item opacity-85"
                    with ui.element("div").classes(cls_an).on("click", lambda: ui.navigate.to("/analise")):
                        ui.icon("bar_chart", size="20px", color="white")
                        ui.label("Análise").classes(
                            "text-[11px] leading-none text-white "
                            + ("font-semibold" if aba_ativa == "analise" else "font-medium")
                        )

            # Rodapé fixo: NAV: Sair
            with ui.element("div").classes("lt-nav-item opacity-85").on("click", _sair):
                ui.icon("logout", size="18px", color="white")
                ui.label("Sair").classes("text-[11px] font-medium leading-none text-white")

    # Top Header Bar (56px — Figma 69:1622 + D2: SEM o texto "Responsável Técnico")
    with ui.header(elevated=False).classes(
        "lt-top-header px-[28px] py-0 flex items-center justify-between"
    ):
        with ui.row().classes("items-center gap-[8px] no-wrap"):
            ui.label("LaudoTech").classes(
                "text-[15px] font-bold text-[#111827] cursor-pointer"
            ).on("click", lambda: ui.navigate.to("/"))
            ui.label("/").classes("text-[14px] text-[#71717A]")
            ui.label("IST Ambiental · SENAI Blumenau").classes(
                "text-[13px] font-normal text-[#52525B]"
            )

        with ui.row().classes("items-center gap-[10px] no-wrap"):
            ui.label(user["nome_usuario"]).classes(
                "text-[12px] font-semibold text-[#111827]"
            )
            with ui.element("div").classes(
                "w-[32px] h-[32px] rounded-full bg-[#004B8D] flex items-center justify-center shrink-0"
            ):
                ui.label(user["iniciais"]).classes("text-[11px] font-bold text-white leading-none")
