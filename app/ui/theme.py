"""Tokens de tema e CSS global do LaudoTech (extraídos do Figma Dev Mode + POC Seção 8.7)."""

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
    """Injeta Google Fonts (IBM Plex Sans & Mono), variáveis CSS e estilos base na página atual."""
    ui.colors(
        primary=BRAND_BLUE,
        secondary=BRAND_BLUE_ACTIVE,
        positive=VIVID_GREEN,
        negative=VIVID_RED,
        warning=VIVID_AMBER,
        dark="#111827",
    )

    ui.add_head_html(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
          :root {{
            --lt-brand-blue: {BRAND_BLUE};
            --lt-brand-blue-dark: {BRAND_BLUE_DARK};
            --lt-brand-blue-active: {BRAND_BLUE_ACTIVE};
            --lt-brand-navy: {BRAND_NAVY};
            --lt-brand-cyan: {BRAND_CYAN};
            --lt-green: {VIVID_GREEN};
            --lt-red: {VIVID_RED};
            --lt-amber: {VIVID_AMBER};
            --lt-gray: {PENDING_GRAY};
            --lt-ink-black: {INK_BLACK};
            --lt-ink-secondary: {INK_SECONDARY};
            --lt-ink-muted: {INK_MUTED};
            --lt-border: {BORDER_DEFAULT};
            --lt-border-strong: {BORDER_STRONG};
            --lt-white: {SURFACE_WHITE};
            --lt-surface-subtle: {SURFACE_SUBTLE};
            --lt-canvas: {SURFACE_CANVAS};
            --lt-row-selected: {ROW_SELECTED_BG};
          }}

          html, body, .q-page, .nicegui-content {{
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: var(--lt-ink-black);
            background-color: var(--lt-white);
            margin: 0;
          }}

          .font-mono-lt {{
            font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace !important;
            font-variant-numeric: tabular-nums;
          }}

          /* Remove padding padrão excessivo do nicegui-content */
          .nicegui-content {{
            padding: 0 !important;
          }}

          /* Slim Nav Rail (92px exato do Figma) */
          .lt-nav-rail {{
            background-color: var(--lt-brand-blue) !important;
            color: #FFFFFF !important;
          }}
          .lt-nav-item {{
            width: 100%;
            border-radius: 8px;
            padding: 10px 4px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 5px;
            cursor: pointer;
            transition: background-color 0.15s ease, opacity 0.15s ease;
            text-decoration: none;
            color: #FFFFFF;
          }}
          .lt-nav-item:hover {{
            background-color: rgba(255, 255, 255, 0.12);
          }}
          .lt-nav-item.active {{
            background-color: rgba(255, 255, 255, 0.18);
          }}

          /* Top Header Bar (56px exato do Figma) */
          .lt-top-header {{
            height: 56px;
            background-color: var(--lt-white) !important;
            color: var(--lt-ink-black) !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.08) !important;
            border-bottom: 1px solid var(--lt-border);
          }}

          /* Cards e superfícies */
          .lt-card {{
            background-color: var(--lt-white);
            border: 1px solid var(--lt-border);
            border-radius: 8px;
          }}

          /* Botões padrão Figma */
          .q-btn.lt-btn-primary {{
            background: var(--lt-brand-blue) !important;
            background-color: var(--lt-brand-blue) !important;
            color: #FFFFFF !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            text-transform: none !important;
            box-shadow: none !important;
            padding: 0 16px !important;
            height: 38px !important;
          }}
          .q-btn.lt-btn-primary:hover {{
            background: #003d73 !important;
            background-color: #003d73 !important;
          }}
          .q-btn.lt-btn-secondary {{
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
            color: var(--lt-ink-black) !important;
            border: 1px solid var(--lt-border-strong) !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            text-transform: none !important;
            box-shadow: none !important;
            padding: 0 14px !important;
            height: 36px !important;
          }}
          .q-btn.lt-btn-secondary .q-icon {{
            color: var(--lt-ink-secondary) !important;
          }}
          .q-btn.lt-btn-secondary:hover {{
            background: var(--lt-surface-subtle) !important;
            background-color: var(--lt-surface-subtle) !important;
          }}

          /* StatusPillV3 (exato do Figma + Seção 8.7) */
          .lt-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 11px 4px 10px;
            border-radius: 999px;
            font-family: 'IBM Plex Sans', sans-serif;
            font-weight: 700;
            font-size: 10px;
            line-height: 1.2;
            letter-spacing: 0.4px;
            white-space: nowrap;
            user-select: none;
          }}
          .lt-pill-dot {{
            width: 7px;
            height: 7px;
            border-radius: 999px;
            flex-shrink: 0;
          }}
          .lt-pill-solid-red {{
            background-color: var(--lt-red);
            color: #FFFFFF;
          }}
          .lt-pill-solid-red .lt-pill-dot {{ background-color: #FFFFFF; }}

          .lt-pill-solid-green {{
            background-color: var(--lt-green);
            color: #FFFFFF;
          }}
          .lt-pill-solid-green .lt-pill-dot {{ background-color: #FFFFFF; }}

          .lt-pill-solid-amber {{
            background-color: var(--lt-amber);
            color: #FFFFFF;
          }}
          .lt-pill-solid-amber .lt-pill-dot {{ background-color: #FFFFFF; }}

          .lt-pill-solid-gray {{
            background-color: var(--lt-gray);
            color: #FFFFFF;
          }}
          .lt-pill-solid-gray .lt-pill-dot {{ background-color: #FFFFFF; }}

          .lt-pill-outline {{
            background-color: #FFFFFF;
            color: var(--lt-ink-black);
            border: 1px solid var(--lt-border);
            box-shadow: 0 1px 1.5px rgba(0, 0, 0, 0.06);
          }}
          .lt-pill-outline-amber .lt-pill-dot {{ background-color: var(--lt-amber); }}
          .lt-pill-outline-red .lt-pill-dot {{ background-color: var(--lt-red); }}
          .lt-pill-outline-gray .lt-pill-dot {{ background-color: var(--lt-gray); }}
          .lt-pill-outline-green .lt-pill-dot {{ background-color: var(--lt-green); }}

          .lt-pill-clickable {{
            cursor: pointer;
            transition: transform 0.1s ease, filter 0.12s ease;
          }}
          .lt-pill-clickable:hover {{
            filter: brightness(0.93);
            transform: translateY(-0.5px);
          }}

          /* Tabelas corporativas Quasar */
          .lt-table {{
            border: 1px solid var(--lt-border) !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            background: #FFFFFF !important;
            overflow: hidden;
          }}
          .lt-table thead tr {{
            background-color: var(--lt-surface-subtle) !important;
            height: 40px !important;
          }}
          .lt-table thead th {{
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 11px !important;
            color: var(--lt-ink-black) !important;
            border-bottom: 1px solid var(--lt-border) !important;
            padding: 10px 12px !important;
          }}
          .lt-table tbody tr {{
            transition: background-color 0.12s ease;
          }}
          .lt-table tbody tr:hover {{
            background-color: #F8FAFC !important;
          }}
          .lt-table tbody tr.lt-row-active {{
            background-color: var(--lt-row-selected) !important;
          }}
          .lt-table tbody tr.lt-row-active td:first-child {{
            box-shadow: inset 4px 0 0 0 var(--lt-brand-blue);
          }}
          .lt-table tbody td {{
            border-bottom: 1px solid var(--lt-border) !important;
            padding: 12px !important;
            vertical-align: middle !important;
          }}
          .lt-table tbody tr:last-child td {{
            border-bottom: none !important;
          }}

          /* Input inline discreto na coluna Observação da B4 */
          .lt-obs-input {{
            width: 100%;
            min-width: 110px;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 4px 6px;
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 12px;
            color: var(--lt-ink-secondary);
            background: transparent;
            outline: none;
            transition: border-color 0.15s ease, background-color 0.15s ease;
          }}
          .lt-obs-input:hover {{
            border-color: var(--lt-border);
            background: #FFFFFF;
          }}
          .lt-obs-input:focus {{
            border-color: var(--lt-brand-blue);
            background: #FFFFFF;
            color: var(--lt-ink-black);
          }}
          .lt-obs-input::placeholder {{
            color: #A1A1AA;
          }}

          /* Inputs / Selects Quasar mais limpos (estilo Figma 36px/40px) */
          .lt-field .q-field__control {{
            border-radius: 6px !important;
            background: #FFFFFF !important;
          }}
          .lt-field .q-field__control:before {{
            border-color: var(--lt-border-strong) !important;
          }}
          .lt-textarea .q-field__control {{
            border-radius: 6px !important;
            background: var(--lt-canvas) !important;
          }}
          .lt-textarea .q-field__control:before {{
            border-color: var(--lt-border-strong) !important;
          }}

          /* Toast escuro OV5 / OV5c */
          .q-notification.lt-toast-dark {{
            background-color: #111827 !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            font-family: 'IBM Plex Sans', sans-serif !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 4px 10px !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25) !important;
          }}

          /* Barra de abas de amostras logo abaixo do Header (B3 e B4 em lote) */
          .lt-sample-tabs-bar {{
            width: 100%;
            background: #FFFFFF;
            border-bottom: 1px solid var(--lt-border);
            padding: 0 28px;
          }}
          .lt-sample-tabs .q-tab {{
            min-height: 44px !important;
            padding: 0 16px !important;
            text-transform: none !important;
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            color: var(--lt-ink-secondary) !important;
          }}
          .lt-sample-tabs .q-tab--active {{
            color: var(--lt-brand-blue) !important;
          }}
          .lt-sample-tabs .q-tabs__arrow {{
            color: var(--lt-ink-secondary) !important;
          }}

          /* Cards KPI clicáveis (B3 pré-validação) */
          .lt-kpi-clickable {{
            cursor: pointer;
            transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
          }}
          .lt-kpi-clickable:hover {{
            border-color: var(--lt-brand-blue) !important;
            box-shadow: 0 2px 8px rgba(0, 75, 141, 0.08);
          }}
          .lt-kpi-active {{
            border-color: var(--lt-brand-blue) !important;
            box-shadow: 0 0 0 1px var(--lt-brand-blue), 0 2px 8px rgba(0, 75, 141, 0.10);
            background-color: #F8FBFF !important;
          }}
        </style>
        """,
        shared=False,
    )
