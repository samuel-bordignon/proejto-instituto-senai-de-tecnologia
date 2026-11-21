"""Gráfico de Barras Empilhadas — Evolução de Conformidade por Local (B5 / ECharts)."""

from __future__ import annotations

from app.core.models import MesConformidadeLocal


def construir_option_evolucao_conformidade(meses: list[MesConformidadeLocal]) -> dict:
    """
    Monta configuração Apache ECharts fiel ao layout B5:
      - Barras empilhadas arredondadas com separação branca nítida entre blocos
      - 3 séries de amostras: Favorável (#16A34A), Pendente (#94A3B8) e Não favorável (#DC2626)
      - Mês atual destacado em negrito no eixo X
      - Tooltip rico exibindo contagem absoluta e % de cada status no mês
    """
    categorias = [
        {
            "value": m.rotulo_mes,
            "textStyle": {
                "fontWeight": 700 if m.is_atual else 400,
                "color": "#111827" if m.is_atual else "#71717A",
            },
        }
        for m in meses
    ]

    favs = [m.favoraveis for m in meses]
    pends = [m.pendentes for m in meses]
    nfavs = [m.nao_favoraveis for m in meses]

    return {
        "animationDuration": 350,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "#FFFFFF",
            "borderColor": "#E4E4E7",
            "borderWidth": 1,
            "textStyle": {
                "color": "#111827",
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 12,
            },
        },
        "legend": {
            "show": False,  # Legenda customizada no cabeçalho do card (exatamente como no Figma B5)
        },
        "grid": {
            "left": 24,
            "right": 24,
            "top": 18,
            "bottom": 34,
            "containLabel": False,
        },
        "xAxis": {
            "type": "category",
            "data": categorias,
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {
                "margin": 14,
                "fontFamily": "IBM Plex Sans, sans-serif",
                "fontSize": 11,
            },
        },
        "yAxis": {
            "type": "value",
            "show": True,
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {"show": False},
            "splitLine": {
                "show": True,
                "lineStyle": {"color": "#F4F4F5", "width": 1},
            },
        },
        "series": [
            {
                "name": "Favoráveis",
                "type": "bar",
                "stack": "amostras",
                "barWidth": "44%",
                "barMaxWidth": 118,
                "data": favs,
                "itemStyle": {
                    "color": "#16A34A",
                    "borderRadius": [6, 6, 6, 6],
                    "borderColor": "#FFFFFF",
                    "borderWidth": 3,
                },
            },
            {
                "name": "Pendentes",
                "type": "bar",
                "stack": "amostras",
                "barWidth": "44%",
                "barMaxWidth": 118,
                "data": pends,
                "itemStyle": {
                    "color": "#94A3B8",
                    "borderRadius": [6, 6, 6, 6],
                    "borderColor": "#FFFFFF",
                    "borderWidth": 3,
                },
            },
            {
                "name": "Não favoráveis",
                "type": "bar",
                "stack": "amostras",
                "barWidth": "44%",
                "barMaxWidth": 118,
                "data": nfavs,
                "itemStyle": {
                    "color": "#DC2626",
                    "borderRadius": [6, 6, 6, 6],
                    "borderColor": "#FFFFFF",
                    "borderWidth": 3,
                },
            },
        ],
    }
