"""Tokens de tema e registro do CSS estático do LaudoTech (Figma Dev Mode + POC Seção 8.7)."""

from nicegui import ui

# Variáveis de cor oficiais (Figma Dev Mode — página 'final')
BRAND_BLUE = "#004B8D"
BRAND_BLUE_DARK = "#003566"
BRAND_BLUE_ACTIVE = "#1A64A6"
BRAND_NAVY = "#00497F"
BRAND_CYAN = "#0B9DC3"

VIVID_GREEN = "#16A34A"
VIVID_RED = "#DC2626"
VIVID_AMBER = "#D97706"
PENDING_GRAY = "#71717A"

INK_BLACK = "#111827"
INK_SECONDARY = "#52525B"
INK_MUTED = "#71717A"
BORDER_DEFAULT = "#E4E4E7"
BORDER_STRONG = "#D4D4D8"
SURFACE_WHITE = "#FFFFFF"
SURFACE_SUBTLE = "#F4F4F5"
SURFACE_CANVAS = "#FAFAFA"
ROW_SELECTED_BG = "#F0F6FC"


def aplicar_tema_global() -> None:
    """Configura paleta Quasar, carrega Google Fonts e vincula a folha estática /assets/laudotech.css."""
    ui.colors(
        primary=BRAND_BLUE,
        secondary=BRAND_BLUE_ACTIVE,
        positive=VIVID_GREEN,
        negative=VIVID_RED,
        warning=VIVID_AMBER,
        dark="#111827",
    )

    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/assets/laudotech.css">
        """,
        shared=False,
    )
