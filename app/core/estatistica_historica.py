"""Motor Estatístico de Desvio Histórico (RN-08, RN-09, Seção 5.5)."""

from __future__ import annotations

import calendar
from collections import deque
import math
from datetime import date
from typing import Optional

from app.core.config import (
    FATOR_DESVIO_PADRAO_K,
    JANELA_MESES,
    MAX_RESULTADOS_HISTORICO,
    MIN_AMOSTRAS_HISTORICO,
    STATUS_PENDENTE,
)
from app.core.models import EstatisticaHistorica, PontoHistorico


_MENSAGEM_AVISO_LQ_LS = (
    "Resultado expresso em limite de quantificação (<LQ/>LS) — "
    "recomenda-se verificação técnica da sensibilidade do método."
)


def _subtrair_meses(data_ref: date, meses: int) -> date:
    """Subtrai `meses` calendário preservando o último dia válido do mês destino."""
    ano = data_ref.year
    mes = data_ref.month - meses
    while mes <= 0:
        mes += 12
        ano -= 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(data_ref.day, ultimo_dia))


def calcular_estatistica_historica(
    pontos: list[PontoHistorico],
    valor_atual: Optional[float],
    qualificador_atual: Optional[str] = None,
    operador: str = "MENOR_IGUAL",
    k: float = FATOR_DESVIO_PADRAO_K,
    status_conformidade: Optional[str] = None,
    data_referencia: Optional[date] = None,
    janela_meses: int = JANELA_MESES,
    max_resultados: int = MAX_RESULTADOS_HISTORICO,
    min_amostras: int = MIN_AMOSTRAS_HISTORICO,
) -> EstatisticaHistorica:
    """
    Avalia desvio histórico por (local_coleta, ensaio) usando até os últimos 6
    resultados anteriores dentro da janela calendário de 6 meses (RN-08 / CT-15).
    Exige n >= 3 medições numéricas anteriores.

    Sinalização <LQ/>LS (RN-09 / CT-14): o aviso textual de reavaliação da
    sensibilidade do método é emitido somente quando o resultado atual possui
    qualificador '<' ou '>' E (gera alerta de desvio OU está Pendente no VMP).
    """
    ref = data_referencia
    if ref is None:
        atual_pts = [p.data_coleta for p in pontos if p.is_atual]
        if atual_pts:
            ref = max(atual_pts)

    candidatos = [p for p in pontos if not p.is_atual and p.valor_numerico is not None]
    if ref is not None and janela_meses > 0:
        data_corte = _subtrair_meses(ref, janela_meses)
        candidatos = [p for p in candidatos if data_corte <= p.data_coleta < ref]

    # Ordena os resultados anteriores em ordem cronológica e alimenta uma
    # Fila Circular de tamanho fixo (deque com maxlen = 6).
    # Quando um novo ponto entra após o limite, o mais antigo é descartado
    # automaticamente pela esquerda em O(1), garantindo memória constante O(1).
    candidatos.sort(key=lambda ponto: ponto.data_coleta)
    janela_circular: deque[float] = deque(maxlen=max_resultados)
    for ponto in candidatos:
        if ponto.valor_numerico is not None:
            janela_circular.append(float(ponto.valor_numerico))

    anteriores = list(janela_circular)

    n = len(anteriores)
    if n < min_amostras:
        aviso_lq = (
            _MENSAGEM_AVISO_LQ_LS
            if qualificador_atual in ("<", ">") and status_conformidade == STATUS_PENDENTE
            else None
        )
        return EstatisticaHistorica(
            n_anteriores=n,
            alerta_desvio=False,
            motivo="HISTORICO_INSUFICIENTE",
            aviso_lq_ls=aviso_lq,
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
            elif operador == "MAIOR_IGUAL" and valor_atual < media:
                alerta = True
                motivo = "VARIACAO_SOBRE_SERIE_CONSTANTE"
            elif operador == "FAIXA" and valor_atual != media:
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
    if qualificador_atual in ("<", ">") and (alerta or status_conformidade == STATUS_PENDENTE):
        aviso_lq_ls = _MENSAGEM_AVISO_LQ_LS

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
