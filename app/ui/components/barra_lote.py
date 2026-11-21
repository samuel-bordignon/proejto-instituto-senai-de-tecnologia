"""Barra compartilhada de abas multi-amostra (B3 e B4) e gerenciamento de sessão do lote."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from nicegui import app, ui

_CHAVE_SESSAO_LOTE = "lote_conferencia"


@dataclass(frozen=True)
class ItemAbaAmostra:
    """Representa uma aba clicável de amostra na barra superior."""

    codigo: str
    cor_dot: str
    sufixo: str = ""


def obter_lote_sessao(codigo_atual: str) -> list[str]:
    """Retorna os códigos do lote ativo na sessão caso o código atual faça parte dele (>1 amostra)."""
    lote: list[str] = list(app.storage.user.get(_CHAVE_SESSAO_LOTE, []))
    if len(lote) > 1 and codigo_atual in lote:
        return lote
    return []


def definir_lote_sessao(codigos: list[str]) -> None:
    """Armazena na sessão do usuário a lista ordenada de códigos importados em lote."""
    app.storage.user[_CHAVE_SESSAO_LOTE] = list(codigos)


def limpar_lote_sessao() -> None:
    """Remove o lote ativo da sessão do usuário."""
    app.storage.user.pop(_CHAVE_SESSAO_LOTE, None)


def renderizar_barra_abas_amostras(
    titulo_prefixo: str,
    itens: list[ItemAbaAmostra],
    valor_ativo: Optional[str],
    on_select: Callable[[str], None],
    texto_direita: Optional[str] = None,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Renderiza a barra horizontal de abas de amostras logo abaixo do cabeçalho global."""
    if not itens:
        return

    with ui.row().classes(
        "lt-sample-tabs-bar items-center justify-between gap-[16px] flex-wrap"
    ):
        with ui.row().classes("items-center gap-[12px] no-wrap overflow-x-auto"):
            ui.label(titulo_prefixo).classes(
                "text-[10px] font-bold tracking-[0.5px] text-[#71717A] shrink-0"
            )
            with ui.tabs(
                value=valor_ativo,
                on_change=lambda e: on_select(str(e.value)),
            ).props(
                "dense align=left indicator-color=primary active-color=primary no-caps outside-arrows mobile-arrows"
            ).classes("lt-sample-tabs"):
                for item in itens:
                    with ui.tab(name=item.codigo, label=""):
                        with ui.row().classes("items-center gap-[7px] no-wrap"):
                            ui.element("div").classes(
                                "w-[7px] h-[7px] rounded-full shrink-0"
                            ).style(f"background-color: {item.cor_dot};")
                            ui.label(item.codigo).classes("font-mono-lt text-[12px] font-bold")
                            if item.sufixo:
                                ui.label(item.sufixo).classes(
                                    "font-mono-lt text-[11px] font-normal text-[#71717A]"
                                )

        if texto_direita:
            ui.label(texto_direita).classes("text-[11px] text-[#71717A] py-[10px]")

        if on_close is not None:
            ui.button(
                icon="close",
                on_click=on_close,
            ).props("flat round dense").classes("text-[#71717A]").tooltip("Fechar barra do lote")
