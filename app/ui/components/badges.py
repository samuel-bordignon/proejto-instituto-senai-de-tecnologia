"""Componente StatusPillV3 (alto contraste do Figma + paleta semântica da Seção 8.7)."""

from __future__ import annotations

import html
from typing import Literal

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    STATUS_CONFORME,
    STATUS_NAO_CONFORME,
)

PillVariant = Literal[
    "solid-red",
    "solid-green",
    "solid-amber",
    "solid-gray",
    "outline-red",
    "outline-amber",
    "outline-gray",
    "outline-green",
]


def status_pill_html(texto: str, variant: PillVariant = "solid-gray", clickable: bool = False) -> str:
    """Gera HTML padronizado de uma pill StatusPillV3."""
    safe_txt = html.escape(texto)
    if variant.startswith("outline-"):
        cls = f"lt-pill lt-pill-outline lt-pill-{variant}"
    else:
        cls = f"lt-pill lt-pill-{variant}"
    if clickable:
        cls += " lt-pill-clickable"
    return f'<span class="{cls}"><span class="lt-pill-dot"></span><span>{safe_txt}</span></span>'


def variante_status_ensaio(status: str) -> PillVariant:
    if status == STATUS_NAO_CONFORME:
        return "solid-red"
    if status == STATUS_CONFORME:
        return "solid-green"
    return "solid-amber"


def variante_status_geral(status_geral: str) -> PillVariant:
    if status_geral == GERAL_NAO_FAVORAVEL:
        return "solid-red"
    if status_geral == GERAL_FAVORAVEL:
        return "solid-green"
    return "solid-amber"
