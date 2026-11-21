"""Tela B1 — Login (/login) fiel ao Figma (69:1557) + POC Seção 6.2."""

from __future__ import annotations

from nicegui import app, ui

from app.repo.mock_repo import repo
from app.ui.auth import login_usuario
from app.ui.theme import aplicar_tema_global


def registrar_pagina_login() -> None:
    @ui.page("/login")
    def pagina_login() -> None:
        aplicar_tema_global()

        if app.storage.user.get("authenticated", False):
            ui.navigate.to("/")
            return

        with ui.element("div").classes(
            "w-screen min-h-screen flex flex-col lg:flex-row bg-white overflow-hidden"
        ):
            # Painel Esquerdo Institucional (foto FIESC/SENAI + overlay #003566)
            with ui.element("div").classes(
                "relative flex-1 min-h-[260px] lg:min-h-screen bg-[#003566] "
                "flex flex-col justify-between p-[40px] lg:p-[56px] overflow-hidden"
            ):
                # Foto de fundo local (baixada do Figma, opacity 0.39)
                ui.html(
                    '<img src="/assets/fiesc_senai_bg.png" alt="FIESC SENAI" '
                    'style="position:absolute; inset:0; width:100%; height:100%; '
                    'object-fit:cover; opacity:0.39; pointer-events:none;" />',
                    sanitize=False,
                )

                # Espaçador superior (mantém equilíbrio do Figma atualizado)
                ui.element("div").classes("relative z-10 h-[32px]")

                # Bloco textual inferior esquerdo
                with ui.column().classes("relative z-10 gap-[20px] max-w-[468px]"):
                    ui.element("div").classes("w-[44px] h-[4px] rounded-[2px] bg-[#16A34A]")
                    ui.label("Conferência técnica assistida para laudos ambientais.").classes(
                        "text-[28px] lg:text-[34px] font-bold text-white leading-[1.24]"
                    )
                    ui.label(
                        "Valide planilhas exportadas do UltraLIMS contra múltiplas legislações, "
                        "acompanhe desvios históricos por ponto de coleta e gere pareceres prontos "
                        "para liberação no PRL."
                    ).classes("text-[15px] font-normal text-white/85 leading-[24px]")

            # Painel Direito — Logo horizontal + Card de Login
            with ui.element("div").classes(
                "w-full lg:w-[559px] shrink-0 bg-white flex flex-col items-center "
                "justify-center gap-[56px] py-[40px] px-[24px]"
            ):
                # Logo horizontal (ícone + LaudoTech nas cores do Figma)
                with ui.row().classes("items-center justify-center gap-[18px] no-wrap"):
                    ui.image("/assets/laudotech_logo_icon.png").classes(
                        "w-[74px] h-[64px] object-contain"
                    )
                    ui.html(
                        '<span style="font-family: Inter, IBM Plex Sans, sans-serif; '
                        'font-weight: 700; font-size: 40px; letter-spacing: -0.02em; line-height: 1;">'
                        '<span style="color:#00497F;">Laudo</span>'
                        '<span style="color:#0B9DC3;">Tech</span>'
                        "</span>",
                        sanitize=False,
                    )

                # Card de Acesso do Conferente
                with ui.column().classes(
                    "w-full max-w-[400px] bg-white border border-[#E4E4E7] "
                    "rounded-[8px] p-[36px] gap-[20px]"
                ):
                    with ui.column().classes("gap-[6px] w-full"):
                        ui.label("Acesso do Conferente").classes(
                            "text-[22px] font-bold text-[#111827] leading-tight"
                        )
                        ui.label(
                            "Identifique-se para registrar conferências e alterações manuais."
                        ).classes("text-[13px] text-[#52525B] leading-[19px]")

                    erro_label = ui.label("").classes(
                        "text-[12px] font-medium text-[#DC2626] bg-[#FEF2F2] "
                        "border border-[#FECACA] rounded-[6px] px-[10px] py-[8px] w-full"
                    )
                    erro_label.set_visibility(False)

                    with ui.column().classes("gap-[6px] w-full"):
                        ui.label("Usuário").classes("text-[12px] font-semibold text-[#111827]")
                        inp_usuario = (
                            ui.input(value="samuel.wiegand", placeholder="ex: samuel.wiegand")
                            .props("outlined dense")
                            .classes("w-full lt-field font-mono-lt")
                        )

                    with ui.column().classes("gap-[6px] w-full"):
                        ui.label("Senha").classes("text-[12px] font-semibold text-[#111827]")
                        inp_senha = (
                            ui.input(
                                value="123456",
                                password=True,
                                password_toggle_button=True,
                                placeholder="••••••••",
                            )
                            .props("outlined dense")
                            .classes("w-full lt-field")
                        )

                    def _tentar_login() -> None:
                        user = repo.autenticar(inp_usuario.value or "", inp_senha.value or "")
                        if not user:
                            erro_label.set_text(
                                "Usuário ou senha inválidos. Para testar a POC use samuel.wiegand / 123456."
                            )
                            erro_label.set_visibility(True)
                            return

                        erro_label.set_visibility(False)
                        login_usuario(user)
                        destino = app.storage.user.pop("referrer_path", "/")
                        if destino == "/login":
                            destino = "/"
                        ui.navigate.to(destino)

                    inp_usuario.on("keydown.enter", lambda _: _tentar_login())
                    inp_senha.on("keydown.enter", lambda _: _tentar_login())

                    ui.button("Entrar", on_click=_tentar_login).classes(
                        "w-full lt-btn-primary h-[42px]"
                    )

                    ui.label(
                        "Autenticação simplificada da POC · dados mockados em memória (senha padrão: 123456)."
                    ).classes("text-[11px] text-[#71717A] leading-[16px]")
