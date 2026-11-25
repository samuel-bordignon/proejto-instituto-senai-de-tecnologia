"""Testes automatizados do Motor Estatístico de Desvio Histórico (CT-12 a CT-15)."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.estatistica_historica import calcular_estatistica_historica
from app.core.models import PontoHistorico
from app.repo import PostgresRepository
from app.ui.components.grafico_historico import construir_figura_historico


def _pt(dt_str: str, cod: str, bruto: str, num: float | None, qual: str | None = None, atual: bool = False) -> PontoHistorico:
    dt = date.fromisoformat(dt_str)
    return PontoHistorico(
        data_coleta=dt,
        rotulo_mes=dt.strftime("%m/%y"),
        codigo_amostra=cod,
        valor_bruto=bruto,
        valor_numerico=num,
        qualificador=qual,  # type: ignore[arg-type]
        is_atual=atual,
    )


def test_ct12_historico_insuficiente_n_menor_3(db_repo: PostgresRepository) -> None:
    """CT-12: Local novo com apenas 1 ou 2 coletas anteriores não dispara alerta amarelo (RN-08)."""
    pts_2 = [
        _pt("2026-05-10", "A1", "10,0", 10.0),
        _pt("2026-06-10", "A2", "12,0", 12.0),
        _pt("2026-07-10", "A3", "95,0", 95.0, atual=True),
    ]
    st = calcular_estatistica_historica(pts_2, valor_atual=95.0, operador="MENOR_IGUAL")
    assert st.n_anteriores == 2
    assert st.alerta_desvio is False
    assert st.motivo == "HISTORICO_INSUFICIENTE"
    assert st.limiar_superior is None

    # Verifica também na amostra real 67019/2026 no banco (apenas 1 coleta anterior 66120/2026)
    am67019 = db_repo.obter_amostra("67019/2026")
    assert am67019 is not None
    e800 = next(e for e in am67019.ensaios if e.codigo == 800)
    assert e800.estatistica is not None
    assert e800.estatistica.n_anteriores == 1
    assert e800.estatistica.alerta_desvio is False


def test_ct13_desvio_estatistico_dentro_do_vmp(db_repo: PostgresRepository) -> None:
    """CT-13: 5 coletas estáveis (18, 20, 19, 21, 20) + atual 38,0 (VMP=120) -> Conforme + Alerta Amarelo."""
    pts = [
        _pt("2026-02-15", "H1", "18,0", 18.0),
        _pt("2026-03-15", "H2", "20,0", 20.0),
        _pt("2026-04-15", "H3", "19,0", 19.0),
        _pt("2026-05-15", "H4", "21,0", 21.0),
        _pt("2026-06-15", "H5", "20,0", 20.0),
        _pt("2026-07-15", "H6", "38,0", 38.0, atual=True),
    ]
    st = calcular_estatistica_historica(
        pts,
        valor_atual=38.0,
        operador="MENOR_IGUAL",
        status_conformidade="Conforme",
    )
    assert st.n_anteriores == 5
    assert st.alerta_desvio is True
    assert st.motivo == "ACIMA_LIMIAR"

    # Verifica na amostra real 63450/2026 (ensaio 111 OGT = 14 mg/L <= VMP 100 mg/L, histórico ~6,7)
    am63450 = db_repo.obter_amostra("63450/2026")
    assert am63450 is not None
    e111 = next(e for e in am63450.ensaios if e.codigo == 111)
    assert e111.status == "Conforme"
    assert e111.estatistica is not None and e111.estatistica.alerta_desvio is True
    assert e111.sinalizacao == "DESVIO > μ+0,20σ"


def test_ct14_serie_lq_misturado_e_aviso_condicional(db_repo: PostgresRepository) -> None:
    """CT-14: Série com <LQ misturado (4 × <0,50, 1 × 0,65, atual <4,00 vs VMP 3,00) + supressão em <LQ conforme."""
    pts = [
        _pt("2026-02-10", "L1", "<0,50", 0.50, "<"),
        _pt("2026-03-10", "L2", "<0,50", 0.50, "<"),
        _pt("2026-04-10", "L3", "0,65", 0.65, None),
        _pt("2026-05-10", "L4", "<0,50", 0.50, "<"),
        _pt("2026-06-10", "L5", "<0,50", 0.50, "<"),
        _pt("2026-07-10", "L6", "<4,00", 4.00, "<", atual=True),
    ]
    st_pend = calcular_estatistica_historica(
        pts,
        valor_atual=4.00,
        qualificador_atual="<",
        operador="MENOR_IGUAL",
        status_conformidade="Pendente",
    )
    assert st_pend.alerta_desvio is True
    assert st_pend.aviso_lq_ls is not None

    # <LQ claramente conforme e dentro do histórico NÃO deve emitir falso aviso de sensibilidade
    st_ok = calcular_estatistica_historica(
        pts[:-1] + [_pt("2026-07-10", "L6B", "<0,50", 0.50, "<", atual=True)],
        valor_atual=0.50,
        qualificador_atual="<",
        operador="MENOR_IGUAL",
        status_conformidade="Conforme",
    )
    assert st_ok.alerta_desvio is False
    assert st_ok.aviso_lq_ls is None

    # Verifica marcador losango vazado ('diamond-open') na amostra real 65462/2026 (DBO 19)
    am65462 = db_repo.obter_amostra("65462/2026")
    assert am65462 is not None
    dbo = next(e for e in am65462.ensaios if e.codigo == 19)
    fig, meta = construir_figura_historico(dbo)
    trace_lq = next(t for t in fig.data if t.name == "Abaixo do LQ (<LQ)")
    assert trace_lq.marker.symbol == "diamond-open"
    assert meta["aviso_historico"] is not None


def test_ct15_recorte_janela_6_meses_e_teto_6_resultados(db_repo: PostgresRepository) -> None:
    """CT-15: Local com 10 coletas (2 > 6 meses + 7 anteriores dentro de 6 meses + 1 atual) usa só as últimas 6."""
    am68010 = db_repo.obter_amostra("68010/2026")
    assert am68010 is not None
    e48 = next(e for e in am68010.ensaios if e.codigo == 48)
    assert e48.estatistica is not None
    assert e48.estatistica.n_anteriores == 6
    # As 6 últimas anteriores (53104..58109) têm valores [1.10, 1.25, 1.15, 1.30, 1.20, 1.28] -> média ~ 1.2133
    assert e48.estatistica.media == pytest.approx((1.10 + 1.25 + 1.15 + 1.30 + 1.20 + 1.28) / 6, abs=1e-3)
