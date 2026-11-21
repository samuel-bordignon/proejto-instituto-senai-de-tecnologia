"""Motor Estatístico de Desvio Histórico (RN-08, RN-09, Seção 5.5)."""

from __future__ import annotations

import math
from typing import Optional

from app.core.config import (
    FATOR_DESVIO_PADRAO_K,
    MAX_RESULTADOS_HISTORICO,
    MIN_AMOSTRAS_HISTORICO,
)
from app.core.models import EstatisticaHistorica, PontoHistorico


def calcular_estatistica_historica(
    pontos: list[PontoHistorico],
    valor_atual: Optional[float],
    qualificador_atual: Optional[str] = None,
    operador: str = "MENOR_IGUAL",
    k: float = FATOR_DESVIO_PADRAO_K,
) -> EstatisticaHistorica:
    """
    Avalia desvio histórico por (local_coleta, ensaio) usando até os últimos 6
    resultados anteriores dentro da janela de 6 meses (RN-08).
    Exige n >= 3 medições numéricas anteriores e σ > 0.
    """
    anteriores = [
        p.valor_numerico
        for p in pontos
        if not p.is_atual and p.valor_numerico is not None
    ][-MAX_RESULTADOS_HISTORICO:]

    n = len(anteriores)
    if n < MIN_AMOSTRAS_HISTORICO:
        return EstatisticaHistorica(
            n_anteriores=n,
            alerta_desvio=False,
            motivo="HISTORICO_INSUFICIENTE",
        )

    media = sum(anteriores) / n
    variancia = sum((x - media) ** 2 for x in anteriores) / (n - 1)
    sigma = math.sqrt(variancia)

    limiar_sup = media + k * sigma
    limiar_inf = max(0.0, media - k * sigma)

    alerta = False
    motivo = "DENTRO_DA_FAIXA"

    if valor_atual is not None:
        if sigma == 0:
            if operador in ("MENOR_IGUAL", "MENOR_ESTRITO") and valor_atual > media:
                alerta = True
                motivo = "VARIACAO_SOBRE_SERIE_CONSTANTE"
            else:
                motivo = "SERIE_CONSTANTE"
        else:
            if operador in ("MENOR_IGUAL", "MENOR_ESTRITO"):
                if valor_atual > limiar_sup:
                    alerta = True
                    motivo = "ACIMA_LIMIAR"
            elif operador == "MAIOR_IGUAL":
                if valor_atual < limiar_inf:
                    alerta = True
                    motivo = "ABAIXO_LIMIAR"
            elif operador == "FAIXA":
                if abs(valor_atual - media) > k * sigma:
                    alerta = True
                    motivo = "FORA_DA_FAIXA_HISTORICA"

    aviso_lq_ls = None
    if qualificador_atual in ("<", ">") and (alerta or qualificador_atual == "<"):
        aviso_lq_ls = (
            "Resultado expresso em limite de quantificação (<LQ/>LS) — "
            "recomenda-se verificação técnica da sensibilidade do método."
        )

    return EstatisticaHistorica(
        media=round(media, 4),
        desvio_padrao=round(sigma, 4),
        limiar_superior=round(limiar_sup, 4),
        limiar_inferior=round(limiar_inf, 4),
        alerta_desvio=alerta,
        motivo=motivo,
        aviso_lq_ls=aviso_lq_ls,
        n_anteriores=n,
    )
