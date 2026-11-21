"""Gráfico temporal histórico por ensaio com Plotly (Seção 5.4, 6.5 e 8.3)."""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

from app.core.config import STATUS_NAO_CONFORME
from app.core.models import EnsaioResultado
from app.core.motor_conformidade import formatar_numero_br


def _obter_vmp_principal(ensaio: EnsaioResultado) -> tuple[Optional[float], Optional[str], Optional[str]]:
    """Retorna (valor_vmp_numerico, texto_vmp, titulo_norma) mais restritivo do ensaio."""
    candidatos = [
        av
        for av in ensaio.avaliacoes.values()
        if av.vmp_numerico_ref is not None and av.motivo != "UNIDADE_DIVERGENTE"
    ]
    if not candidatos:
        # Mesmo se unidade divergir, mostra o texto de referência no cabeçalho mas não plota linha enganosa
        qualquer = next(iter(ensaio.avaliacoes.values()), None)
        if qualquer:
            return None, qualquer.vmp_texto, qualquer.norma_titulo
        return None, None, None

    escolhido = min(candidatos, key=lambda a: a.vmp_numerico_ref or float("inf"))
    return escolhido.vmp_numerico_ref, escolhido.vmp_texto, escolhido.norma_titulo


def construir_figura_historico(ensaio: EnsaioResultado) -> tuple[go.Figure, dict[str, str]]:
    """
    Constrói a figura Plotly do ensaio selecionado na tela B4:
      - Série das últimas 6 coletas (6 meses)
      - Linha horizontal da Média (μ) [nova exigência da Seção 6.5 / D8]
      - Linha horizontal do Limiar μ + 0,20σ (âmbar tracejada, quando n >= 3)
      - Linha horizontal do VMP (vermelha tracejada)
      - Marcadores distintos para Medição Exata, <LQ (losango vazado), >LS (triângulo) e Coleta Atual violando VMP
    """
    vmp_val, vmp_texto, vmp_norma = _obter_vmp_principal(ensaio)
    stats = ensaio.estatistica

    meta_header = {
        "media": formatar_numero_br(stats.media, 2) if stats and stats.media is not None else "—",
        "sigma": formatar_numero_br(stats.desvio_padrao, 2) if stats and stats.desvio_padrao is not None else "—",
        "limiar": formatar_numero_br(stats.limiar_superior, 2) if stats and stats.limiar_superior is not None else "—",
        "vmp_label": f"VMP ({vmp_norma}):" if vmp_norma else "VMP:",
        "vmp_texto": vmp_texto or "—",
        "aviso_historico": (
            f"Histórico insuficiente (n = {stats.n_anteriores} < 3) — sem cálculo de limiar estatístico."
            if stats and stats.motivo == "HISTORICO_INSUFICIENTE"
            else (stats.aviso_lq_ls if stats else None)
        ),
    }

    pontos_validos = [p for p in ensaio.historico if p.valor_numerico is not None]

    fig = go.Figure()

    if not pontos_validos:
        fig.add_annotation(
            text="Sem medições numéricas disponíveis para série histórica.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(family="IBM Plex Sans", size=13, color="#71717A"),
        )
        fig.update_layout(
            height=220,
            margin=dict(l=24, r=24, t=12, b=24),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig, meta_header

    x_labels: list[str] = []
    y_vals: list[float] = []
    hovers: list[str] = []

    for p in pontos_validos:
        sufixo = f"{p.valor_bruto} · LQ" if p.is_lq else (f"{p.valor_bruto} · LS" if p.is_ls else p.valor_bruto)
        if p.is_atual:
            x_labels.append(f"<b>{p.rotulo_mes} ({sufixo})</b>")
        else:
            x_labels.append(f"{p.rotulo_mes} ({sufixo})")
        y_vals.append(float(p.valor_numerico))

        nota_q = ""
        if p.is_lq:
            nota_q = "<br><i>Faixa de incerteza: [0, LQ] (abaixo do limite de quantificação)</i>"
        elif p.is_ls:
            nota_q = "<br><i>Acima do limite superior de quantificação (&gt;LS)</i>"
        hovers.append(
            f"<b>Amostra {p.codigo_amostra}</b><br>"
            f"Coleta: {p.data_coleta.strftime('%d/%m/%Y')}<br>"
            f"Resultado: <b>{p.valor_bruto} {ensaio.unidade_trabalho}</b>{nota_q}"
        )

    # 1. Linha conectora principal
    fig.add_trace(
        go.Scatter(
            x=x_labels,
            y=y_vals,
            mode="lines",
            line=dict(color="#0077B6", width=2.4),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # 2. Classifica marcadores por categoria (Medição exata, <LQ, >LS, Desvio, Atual fora VMP)
    idx_exata, idx_lq, idx_ls, idx_desvio, idx_atual_nc = [], [], [], [], []
    limiar = stats.limiar_superior if stats and stats.n_anteriores >= 3 else None

    for i, p in enumerate(pontos_validos):
        if p.is_atual and ensaio.status == STATUS_NAO_CONFORME:
            idx_atual_nc.append(i)
        elif p.is_lq:
            idx_lq.append(i)
        elif p.is_ls:
            idx_ls.append(i)
        elif limiar is not None and p.valor_numerico is not None and p.valor_numerico > limiar:
            idx_desvio.append(i)
        else:
            idx_exata.append(i)

    def _add_markers(indices: list[int], name: str, marker: dict, show_always: bool = False) -> None:
        if not indices and not show_always:
            return
        fig.add_trace(
            go.Scatter(
                x=[x_labels[i] for i in indices],
                y=[y_vals[i] for i in indices],
                mode="markers",
                name=name,
                marker=marker,
                text=[hovers[i] for i in indices],
                hovertemplate="%{text}<extra></extra>",
                showlegend=True,
            )
        )

    _add_markers(
        idx_exata,
        "Medição exata",
        dict(symbol="circle", size=9, color="#0077B6", line=dict(color="#FFFFFF", width=1.5)),
        show_always=True,
    )
    _add_markers(
        idx_lq,
        "Abaixo do LQ (<LQ)",
        dict(symbol="diamond-open", size=11, color="#3F3F46", line=dict(color="#3F3F46", width=2.3)),
        show_always=bool(idx_lq),
    )
    _add_markers(
        idx_ls,
        "Acima do LS (>LS)",
        dict(symbol="triangle-up-open", size=12, color="#DC2626", line=dict(color="#DC2626", width=2.3)),
        show_always=bool(idx_ls),
    )
    _add_markers(
        idx_desvio,
        "Desvio (> μ+0,20σ)",
        dict(symbol="circle", size=10, color="#D97706", line=dict(color="#FFFFFF", width=1.5)),
        show_always=False,
    )

    if idx_atual_nc:
        # Alvo vermelho concêntrico (exatamente como no Figma B4/B4b)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[i] for i in idx_atual_nc],
                y=[y_vals[i] for i in idx_atual_nc],
                mode="markers",
                name="Violação atual",
                marker=dict(symbol="circle-open", size=17, color="#DC2626", line=dict(color="#DC2626", width=2.5)),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[x_labels[i] for i in idx_atual_nc],
                y=[y_vals[i] for i in idx_atual_nc],
                mode="markers",
                name="Violação atual",
                marker=dict(
                    symbol="triangle-up" if pontos_validos[idx_atual_nc[0]].is_ls else "circle",
                    size=8,
                    color="#DC2626",
                ),
                text=[hovers[i] for i in idx_atual_nc],
                hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            )
        )

    # 3. Linhas horizontais de referência (VMP, μ [nova!], Limiar μ + 0,20σ)
    ref_vals = list(y_vals)

    if stats and stats.media is not None and stats.n_anteriores >= 3:
        ref_vals.append(stats.media)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[0], x_labels[-1]],
                y=[stats.media, stats.media],
                mode="lines",
                name=f"Média (μ = {formatar_numero_br(stats.media, 2)})",
                line=dict(color="#64748B", width=1.5, dash="dot"),
                hovertemplate=f"Média histórica (μ): <b>{formatar_numero_br(stats.media, 2)} {ensaio.unidade_trabalho}</b><extra></extra>",
            )
        )

    if limiar is not None:
        ref_vals.append(limiar)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[0], x_labels[-1]],
                y=[limiar, limiar],
                mode="lines",
                name="Limiar μ+0,20σ",
                line=dict(color="#D97706", width=1.6, dash="dash"),
                hovertemplate=f"Limiar μ+0,20σ: <b>{formatar_numero_br(limiar, 2)} {ensaio.unidade_trabalho}</b><extra></extra>",
            )
        )

    if vmp_val is not None:
        ref_vals.append(vmp_val)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[0], x_labels[-1]],
                y=[vmp_val, vmp_val],
                mode="lines",
                name="VMP",
                line=dict(color="#DC2626", width=1.6, dash="dash"),
                hovertemplate=f"VMP ({vmp_norma}): <b>{vmp_texto}</b><extra></extra>",
            )
        )

    y_min = min(ref_vals)
    y_max = max(ref_vals)
    margem = (y_max - y_min) * 0.22 if y_max != y_min else max(1.0, abs(y_max) * 0.25)

    fig.update_layout(
        height=230,
        margin=dict(l=42, r=24, t=12, b=52),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans", size=11, color="#52525B"),
        hovermode="closest",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            tickfont=dict(family="IBM Plex Mono", size=11, color="#71717A"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False,
            showline=False,
            range=[max(0.0, y_min - margem) if y_min >= 0 else y_min - margem, y_max + margem],
            tickfont=dict(family="IBM Plex Mono", size=10, color="#94A3B8"),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="right",
            x=1.0,
            font=dict(family="IBM Plex Sans", size=11, color="#52525B"),
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    return fig, meta_header
