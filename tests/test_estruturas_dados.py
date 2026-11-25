"""Testes dedicados das otimizações com Estruturas de Dados e Complexidade (DEV-17)."""

from __future__ import annotations

from datetime import date, datetime

from app.core.estatistica_historica import calcular_estatistica_historica
from app.core.models import Amostra, PontoHistorico
from app.core.motor_conformidade import ordenar_lote_por_prioridade
from app.core.parser_ultralims import _extrair_unidades_referencia, _mapear_cabecalho_ultralims
from app.repo.postgres_repo import _construir_pilha_logs_auditoria


def test_pilha_lifo_auditoria_com_deque_appendleft() -> None:
    """Valida a Pilha LIFO (deque + appendleft em O(1)) mantendo o evento mais recente no topo."""
    rows_mais_recente_primeiro = [
        {
            "id": "log-2",
            "data_alteracao": datetime(2026, 7, 28, 15, 0),
            "usuario": "maria.cardoso",
            "campo_alterado": "minuta",
            "ensaio_codigo": None,
            "ensaio_nome": None,
            "valor_anterior": "Minuta A",
            "valor_novo": "Minuta B",
            "observacao": None,
        },
        {
            "id": "log-1",
            "data_alteracao": datetime(2026, 7, 28, 14, 0),
            "usuario": "samuel.wiegand",
            "campo_alterado": "conformidade",
            "ensaio_codigo": 106,
            "ensaio_nome": "Nitrogênio Amoniacal",
            "valor_anterior": "Pendente",
            "valor_novo": "Conforme",
            "observacao": "Revisado",
        },
    ]

    pilha = _construir_pilha_logs_auditoria(rows_mais_recente_primeiro)
    assert [lg.id for lg in pilha] == ["log-2", "log-1"]
    assert pilha[0].usuario == "maria.cardoso"
    assert pilha[1].ensaio_codigo == 106


def test_fila_circular_deque_maxlen_6_estatistica() -> None:
    """Valida que a Fila Circular (deque maxlen=6) mantém apenas os 6 registros mais recentes."""
    pontos = [
        PontoHistorico(
            data_coleta=date(2026, mes, 10),
            rotulo_mes=f"0{mes}/26",
            codigo_amostra=f"A{mes}/2026",
            valor_bruto=str(val),
            valor_numerico=float(val),
            is_atual=False,
        )
        for mes, val in [
            (2, 99.0),  # 7º mais antigo dentro de 6 meses -> descartado pela Fila Circular!
            (3, 10.0),
            (4, 10.0),
            (5, 10.0),
            (6, 10.0),
            (7, 10.0),
            (8, 10.0),
        ]
    ]
    pontos.append(
        PontoHistorico(
            data_coleta=date(2026, 8, 25),
            rotulo_mes="08/26 Atual",
            codigo_amostra="ATUAL/2026",
            valor_bruto="10,0",
            valor_numerico=10.0,
            is_atual=True,
        )
    )

    stats = calcular_estatistica_historica(pontos, valor_atual=10.0, janela_meses=12, max_resultados=6)
    assert stats.n_anteriores == 6
    assert stats.media == 10.0
    assert stats.desvio_padrao == 0.0


def test_fila_de_prioridade_heapq_para_lotes() -> None:
    """Valida a Fila de Prioridade (heapq): 1º Não favorável, 2º Pendente, 3º Favorável (estável)."""
    def _am(cod: str, status: str) -> Amostra:
        return Amostra(
            codigo=cod,
            data_coleta=date(2026, 7, 20),
            cliente="Cliente Teste",
            proposta="Proposta Teste",
            local_coleta="Local Teste",
            origem="Efluente Tratado",
            status_geral=status,  # type: ignore[arg-type]
        )

    lote_bruto = [
        _am("FAV-1", "Favorável"),
        _am("PEND-1", "Pendente"),
        _am("NF-1", "Não favorável"),
        _am("FAV-2", "Favorável"),
        _am("NF-2", "Não favorável"),
        _am("PEND-2", "Pendente"),
    ]

    ordenado = ordenar_lote_por_prioridade(lote_bruto)
    assert [a.codigo for a in ordenado] == ["NF-1", "NF-2", "PEND-1", "PEND-2", "FAV-1", "FAV-2"]


def test_preprocessamento_cabecalho_parser_e_deduplicacao_on() -> None:
    """Valida o pré-processamento único do cabeçalho UltraLIMS e deduplicação O(n)."""
    colunas = [
        "Código da Amostra",
        "Código Externo",
        "Data Coleta",
        "Data Conclusão",
        "794 - pH",
        "106 - Nitrogênio Amoniacal",
        "Observação Livre",
    ]
    mapa = _mapear_cabecalho_ultralims(colunas)
    assert mapa.colunas_codigo_amostra == ["Código da Amostra"]
    assert mapa.colunas_codigo_externo == ["Código Externo"]
    assert mapa.colunas_data_coleta == ["Data Coleta"]
    assert mapa.colunas_data_conclusao == ["Data Conclusão"]
    assert mapa.colunas_ensaios == [
        ("794 - pH", 794, "pH"),
        ("106 - Nitrogênio Amoniacal", 106, "Nitrogênio Amoniacal"),
    ]

    unids = _extrair_unidades_referencia({268: ["ug/L", "µg/L", "mg/L", "mg/L", "ppb"]}, 268)
    assert unids == ["µg/L", "mg/L"]
