"""Gráfico temporal histórico por ensaio com Plotly (suporte completo a MENOR_IGUAL, MENOR_ESTRITO, MAIOR_IGUAL e FAIXA)."""

from __future__ import annotations

from typing import Optional

import plotly.graph_objects as go

from app.core.config import STATUS_NAO_CONFORME
from app.core.models import AvaliacaoNorma, EnsaioResultado
from app.core.motor_conformidade import formatar_numero_br


def _obter_avaliacao_principal(ensaio: EnsaioResultado) -> tuple[Optional[AvaliacaoNorma], Optional[str], Optional[str]]:
    """
    Seleciona a avaliação regulatória mais restritiva do ensaio:
      - MAIOR_IGUAL (ex: OD): maior valor_min exigido (ex: Classe 1 >= 6 mg/L sobre Classe 2 >= 5 mg/L)
      - FAIXA (ex: pH): menor amplitude / maior valor_min e menor valor_max
      - MENOR_IGUAL / MENOR_ESTRITO: menor valor_max permitido
    """
    candidatos = [
        av
        for av in ensaio.avaliacoes.values()
        if av.motivo != "UNIDADE_DIVERGENTE"
        and (av.vmp_min is not None or av.vmp_max is not None or av.vmp_numerico_ref is not None)
    ]
    if not candidatos:
        qualquer = next(iter(ensaio.avaliacoes.values()), None)
        if qualquer:
            return None, qualquer.vmp_texto, qualquer.norma_titulo
        return None, None, None

    op0 = candidatos[0].operador
    if op0 == "MAIOR_IGUAL":
        escolhido = max(
            candidatos,
            key=lambda a: a.vmp_min if a.vmp_min is not None else (a.vmp_numerico_ref or float("-inf")),
        )
    elif op0 == "FAIXA":
        escolhido = min(
            candidatos,
            key=lambda a: (
                (a.vmp_max if a.vmp_max is not None else float("inf"))
                - (a.vmp_min if a.vmp_min is not None else 0.0)
            ),
        )
    else:
        escolhido = min(
            candidatos,
            key=lambda a: a.vmp_max if a.vmp_max is not None else (a.vmp_numerico_ref or float("inf")),
        )
    return escolhido, escolhido.vmp_texto, escolhido.norma_titulo


def _resolver_limiares_estatisticos(
    ensaio: EnsaioResultado, operador: str
) -> tuple[str, str, Optional[float], Optional[float]]:
    """Retorna (rotulo_header, valor_header, limiar_inferior_plot, limiar_superior_plot)."""
    stats = ensaio.estatistica
    if not stats or stats.n_anteriores < 3:
        if operador == "MAIOR_IGUAL":
            return "Limiar μ−0,20σ:", "—", None, None
        if operador == "FAIXA":
            return "Faixa μ±0,20σ:", "—", None, None
        return "Limiar μ+0,20σ:", "—", None, None

    if operador == "MAIOR_IGUAL":
        txt = formatar_numero_br(stats.limiar_inferior, 2) if stats.limiar_inferior is not None else "—"
        return "Limiar μ−0,20σ:", txt, stats.limiar_inferior, None

    if operador == "FAIXA":
        inf_t = formatar_numero_br(stats.limiar_inferior, 2)
        sup_t = formatar_numero_br(stats.limiar_superior, 2)
        return "Faixa μ±0,20σ:", f"{inf_t} a {sup_t}", stats.limiar_inferior, stats.limiar_superior

    txt = formatar_numero_br(stats.limiar_superior, 2) if stats.limiar_superior is not None else "—"
    return "Limiar μ+0,20σ:", txt, None, stats.limiar_superior


def construir_figura_historico(ensaio: EnsaioResultado) -> tuple[go.Figure, dict[str, str]]:
    """
    Constrói a figura Plotly do ensaio selecionado na tela B4:
      - Série das últimas 6 coletas (janela calendário de 6 meses)
      - Linha horizontal da Média (μ)
      - Linhas de Limiar estatístico: μ+0,20σ (MENOR_*), μ−0,20σ (MAIOR_IGUAL) ou ambas (FAIXA)
      - Linhas de VMP: única (MENOR_* / MAIOR_IGUAL) ou dupla VMP mín. / VMP máx. (FAIXA)
      - Marcadores distintos para Medição Exata, <LQ, >LS, Desvio e Violação Atual
    """
    av_ref, vmp_texto, vmp_norma = _obter_avaliacao_principal(ensaio)
    operador = (
        av_ref.operador
        if av_ref is not None
        else (next(iter(ensaio.avaliacoes.values())).operador if ensaio.avaliacoes else "MENOR_IGUAL")
    )
    stats = ensaio.estatistica
    limiar_label, limiar_txt, lim_inf_plot, lim_sup_plot = _resolver_limiares_estatisticos(ensaio, operador)

    meta_header = {
        "media": formatar_numero_br(stats.media, 2) if stats and stats.media is not None else "—",
        "sigma": formatar_numero_br(stats.desvio_padrao, 2) if stats and stats.desvio_padrao is not None else "—",
        "limiar_label": limiar_label,
        "limiar": limiar_txt,
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

    # 2. Classifica marcadores por categoria
    idx_exata, idx_lq, idx_ls, idx_desvio, idx_atual_nc = [], [], [], [], []

    def _fora_limiar(valor: float) -> bool:
        if operador == "MAIOR_IGUAL":
            return lim_inf_plot is not None and valor < lim_inf_plot
        if operador == "FAIXA":
            abaixo = lim_inf_plot is not None and valor < lim_inf_plot
            acima = lim_sup_plot is not None and valor > lim_sup_plot
            return abaixo or acima
        return lim_sup_plot is not None and valor > lim_sup_plot

    for i, p in enumerate(pontos_validos):
        if p.is_atual and ensaio.status == STATUS_NAO_CONFORME:
            idx_atual_nc.append(i)
        elif p.is_lq:
            idx_lq.append(i)
        elif p.is_ls:
            idx_ls.append(i)
        elif p.valor_numerico is not None and _fora_limiar(float(p.valor_numerico)):
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

    rotulo_desvio = (
        "Desvio (< μ−0,20σ)"
        if operador == "MAIOR_IGUAL"
        else ("Desvio (μ±0,20σ)" if operador == "FAIXA" else "Desvio (> μ+0,20σ)")
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
        rotulo_desvio,
        dict(symbol="circle", size=10, color="#D97706", line=dict(color="#FFFFFF", width=1.5)),
        show_always=False,
    )

    if idx_atual_nc:
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

    # 3. Linhas horizontais de referência (Média μ, Limiares estatísticos e VMPs)
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

    if lim_sup_plot is not None:
        ref_vals.append(lim_sup_plot)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[0], x_labels[-1]],
                y=[lim_sup_plot, lim_sup_plot],
                mode="lines",
                name="Limiar μ+0,20σ",
                line=dict(color="#D97706", width=1.6, dash="dash"),
                hovertemplate=f"Limiar μ+0,20σ: <b>{formatar_numero_br(lim_sup_plot, 2)} {ensaio.unidade_trabalho}</b><extra></extra>",
            )
        )

    if lim_inf_plot is not None:
        ref_vals.append(lim_inf_plot)
        fig.add_trace(
            go.Scatter(
                x=[x_labels[0], x_labels[-1]],
                y=[lim_inf_plot, lim_inf_plot],
                mode="lines",
                name="Limiar μ−0,20σ",
                line=dict(color="#D97706", width=1.6, dash="dash"),
                hovertemplate=f"Limiar μ−0,20σ: <b>{formatar_numero_br(lim_inf_plot, 2)} {ensaio.unidade_trabalho}</b><extra></extra>",
            )
        )

    if av_ref is not None:
        if av_ref.operador == "FAIXA":
            if av_ref.vmp_min is not None:
                ref_vals.append(av_ref.vmp_min)
                fig.add_trace(
                    go.Scatter(
                        x=[x_labels[0], x_labels[-1]],
                        y=[av_ref.vmp_min, av_ref.vmp_min],
                        mode="lines",
                        name=f"VMP mín. ({formatar_numero_br(av_ref.vmp_min)})",
                        line=dict(color="#DC2626", width=1.6, dash="dash"),
                        hovertemplate=f"VMP mín. ({vmp_norma}): <b>{formatar_numero_br(av_ref.vmp_min)}</b><extra></extra>",
                    )
                )
            if av_ref.vmp_max is not None:
                ref_vals.append(av_ref.vmp_max)
                fig.add_trace(
                    go.Scatter(
                        x=[x_labels[0], x_labels[-1]],
                        y=[av_ref.vmp_max, av_ref.vmp_max],
                        mode="lines",
                        name=f"VMP máx. ({formatar_numero_br(av_ref.vmp_max)})",
                        line=dict(color="#DC2626", width=1.6, dash="dash"),
                        hovertemplate=f"VMP máx. ({vmp_norma}): <b>{formatar_numero_br(av_ref.vmp_max)}</b><extra></extra>",
                    )
                )
        else:
            vmp_unico = (
                av_ref.vmp_min
                if av_ref.operador == "MAIOR_IGUAL" and av_ref.vmp_min is not None
                else (av_ref.vmp_max if av_ref.vmp_max is not None else av_ref.vmp_numerico_ref)
            )
            if vmp_unico is not None:
                ref_vals.append(vmp_unico)
                lbl_vmp = "VMP mín." if av_ref.operador == "MAIOR_IGUAL" else "VMP"
                fig.add_trace(
                    go.Scatter(
                        x=[x_labels[0], x_labels[-1]],
                        y=[vmp_unico, vmp_unico],
                        mode="lines",
                        name=lbl_vmp,
                        line=dict(color="#DC2626", width=1.6, dash="dash"),
                        hovertemplate=f"{lbl_vmp} ({vmp_norma}): <b>{vmp_texto}</b><extra></extra>",
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
