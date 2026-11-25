"""Testes automatizados do Motor de Conformidade e Regras Legais (CT-01 a CT-09)."""

from __future__ import annotations

from app.core.models import ParametroNorma
from app.core.motor_conformidade import avaliar_parametro, gerar_parecer_automatico
from app.repo import PostgresRepository


def _param(
    operador: str,
    vmin: float | None = None,
    vmax: float | None = None,
    esperado: str | None = None,
    unidade: str = "mg/L",
    sigla: str = "CONAMA 430",
    nome: str = "Resolução CONAMA 430/2011",
    classe: str | None = "Sem Classe",
) -> ParametroNorma:
    return ParametroNorma(
        norma_id=f"{sigla}|{classe or ''}",
        norma_sigla=sigla,
        norma_nome_completo=nome,
        classe_nome=classe,
        operador=operador,  # type: ignore[arg-type]
        valor_min=vmin,
        valor_max=vmax,
        valor_esperado=esperado,
        unidade=unidade,
    )


def test_ct01_amostra_100_conforme_portarias(db_repo: PostgresRepository) -> None:
    """CT-01: Amostra de potabilidade (GM/MS 888 + SES-SC 1468) 100% dentro do VMP."""
    am = db_repo.obter_amostra("4765/2026")
    assert am is not None
    assert am.status_geral == "Favorável"
    assert all(e.status == "Conforme" for e in am.ensaios)
    assert gerar_parecer_automatico(am) == (
        "Os resultados de ensaio atendem às especificações aplicadas neste documento."
    )


def test_ct02_conflito_entre_duas_legislacoes(db_repo: PostgresRepository) -> None:
    """CT-02: 877 - Glifosato+AMPA = 42,0 µg/L sob GM/MS 888 (<= 500) + SES-SC 1468 (<= 30)."""
    am = db_repo.obter_amostra("4766/2026")
    assert am is not None
    assert am.status_geral == "Não favorável"

    e877 = next(e for e in am.ensaios if e.codigo == 877)
    assert e877.status == "Não conforme"
    assert e877.avaliacoes["GM/MS 888|"].conformidade is True
    assert e877.avaliacoes["SES-SC 1468|"].conformidade is False

    parecer = gerar_parecer_automatico(am)
    assert "Portaria SES/SC 1468/2022" in parecer
    assert "Portaria GM/MS 888/2021" not in parecer


def test_ct03_conama_430_sanitario_vs_sem_classe(db_repo: PostgresRepository) -> None:
    """CT-03: Amostra real 63450/2026 — Sanitário (100% Conforme) vs Sem Classe (106 NA = 71 > 20,0)."""
    am = db_repo.obter_amostra("63450/2026")
    assert am is not None
    assert am.status_geral == "Não favorável"

    # Em Sanitário, todos os parâmetros avaliados são Conformes e 106 não possui VMP
    for e in am.ensaios:
        av_sanit = e.avaliacoes.get("CONAMA 430|Sanitário")
        if av_sanit is not None:
            assert av_sanit.conformidade is True

    e106 = next(e for e in am.ensaios if e.codigo == 106)
    assert "CONAMA 430|Sanitário" not in e106.avaliacoes
    assert e106.avaliacoes["CONAMA 430|Sem Classe"].conformidade is False
    assert e106.status == "Não conforme"

    e259 = next(e for e in am.ensaios if e.codigo == 259)
    assert e259.avaliacoes["CONAMA 430|Sem Classe"].conformidade is True


def test_ct04_conama_357_classes_1_2_3(db_repo: PostgresRepository) -> None:
    """CT-04: Amostra real 64283/2026 — 59 Coliformes = 270: NC na Cl. 1 (<=200), C na Cl. 2/3."""
    am = db_repo.obter_amostra("64283/2026")
    assert am is not None
    e59 = next(e for e in am.ensaios if e.codigo == 59)
    assert e59.avaliacoes["CONAMA 357|Classe 1"].conformidade is False
    assert e59.avaliacoes["CONAMA 357|Classe 2"].conformidade is True
    assert e59.avaliacoes["CONAMA 357|Classe 3"].conformidade is True
    assert e59.status == "Não conforme"


def test_ct05_fronteira_exata_menor_igual_vs_menor_estrito(db_repo: PostgresRepository) -> None:
    """CT-05: Fronteira exata — OGM 20,0 (<= 20,0 -> C) vs Temperatura 40,0 (< 40,0 -> NC) e 39,9 (C)."""
    p_ogm = _param("MENOR_IGUAL", vmax=20.0, unidade="mg/L")
    p_temp = _param("MENOR_ESTRITO", vmax=40.0, unidade="°C")

    assert avaliar_parametro("20,0", "AUTOMATICA", "mg/L", p_ogm) == (True, "AVALIADO")
    assert avaliar_parametro("40,0", "AUTOMATICA", "°C", p_temp) == (False, "AVALIADO")
    assert avaliar_parametro("39,9", "AUTOMATICA", "°C", p_temp) == (True, "AVALIADO")

    am_nc = db_repo.obter_amostra("68001/2026")
    am_ok = db_repo.obter_amostra("68002/2026")
    assert am_nc is not None and am_ok is not None

    e800_nc = next(e for e in am_nc.ensaios if e.codigo == 800)
    assert e800_nc.status == "Não conforme"
    assert e800_nc.sinalizacao == "LIMITE ESTRITO"

    e800_ok = next(e for e in am_ok.ensaios if e.codigo == 800)
    assert e800_ok.status == "Conforme"


def test_ct06_logica_intervalar_abaixo_lq(db_repo: PostgresRepository) -> None:
    """CT-06: <LQ — 65462/2026 (DBO <5,00: Cl.1 Pendente, Cl.2 Conforme) e 65335/2026 (Cu <0,01)."""
    am65462 = db_repo.obter_amostra("65462/2026")
    assert am65462 is not None
    dbo = next(e for e in am65462.ensaios if e.codigo == 19)
    assert dbo.avaliacoes["CONAMA 357|Classe 1"].conformidade is None
    assert dbo.avaliacoes["CONAMA 357|Classe 2"].conformidade is True
    assert dbo.status == "Pendente"

    am65335 = db_repo.obter_amostra("65335/2026")
    assert am65335 is not None
    cu = next(e for e in am65335.ensaios if e.codigo == 157)
    assert cu.avaliacoes["CONAMA 357|Classe 1"].conformidade is None
    assert cu.avaliacoes["CONAMA 357|Classe 2"].conformidade is None
    assert cu.avaliacoes["CONAMA 357|Classe 3"].conformidade is True
    assert cu.status == "Pendente"


def test_ct07_logica_intervalar_acima_ls(db_repo: PostgresRepository) -> None:
    """CT-07: >LS — Turbidez >5,0 (vs <= 5 -> Não conforme) e >2,0 (vs <= 5 -> Pendente)."""
    p_turb = _param("MENOR_IGUAL", vmax=5.0, unidade="NTU", sigla="GM/MS 888", classe=None)
    assert avaliar_parametro(">5,0", "AUTOMATICA", "NTU", p_turb) == (False, "AVALIADO")
    assert avaliar_parametro(">2,0", "AUTOMATICA", "NTU", p_turb) == (None, "AVALIADO")

    am68010 = db_repo.obter_amostra("68010/2026")
    assert am68010 is not None
    e48 = next(e for e in am68010.ensaios if e.codigo == 48)
    assert e48.status == "Não conforme"


def test_ct08_qualitativos_ausencia_e_ausente_em_numerico(db_repo: PostgresRepository) -> None:
    """CT-08: Qualitativos AUSENCIA (Presente -> NC, Ausente -> C) e 'Ausente' em numérico -> 0.0 (C)."""
    p_aus = _param("AUSENCIA", esperado="Ausente", unidade="")
    p_num = _param("MENOR_IGUAL", vmax=1.0, unidade="mL/L")

    assert avaliar_parametro("Presente", "AUTOMATICA", "", p_aus) == (False, "AVALIADO")
    assert avaliar_parametro("Ausente", "AUTOMATICA", "", p_aus) == (True, "AVALIADO")
    assert avaliar_parametro("Ausente", "AUTOMATICA", "mL/L", p_num) == (True, "AVALIADO")

    am63413 = db_repo.obter_amostra("63413/2026")
    assert am63413 is not None
    e784 = next(e for e in am63413.ensaios if e.codigo == 784)
    assert e784.status == "Não conforme"

    am68002 = db_repo.obter_amostra("68002/2026")
    assert am68002 is not None
    e119 = next(e for e in am68002.ensaios if e.codigo == 119)
    assert e119.valor_bruto == "Ausente"
    assert e119.status == "Conforme"


def test_ct09_divergencia_de_unidade_rn05_rnf02(db_repo: PostgresRepository) -> None:
    """CT-09: Divergência de unidade (268 Hg µg/L vs mg/L na 430; 672 Benzeno µg/L vs mg/L na 357)."""
    p_hg_430 = _param("MENOR_IGUAL", vmax=0.01, unidade="mg/L")
    conf, motivo = avaliar_parametro("<0,200", "AUTOMATICA", "µg/L", p_hg_430)
    assert conf is None and motivo == "UNIDADE_DIVERGENTE"

    p_benz_357 = _param(
        "MENOR_IGUAL",
        vmax=0.005,
        unidade="mg/L",
        sigla="CONAMA 357",
        nome="Resolução CONAMA 357/2005",
        classe="Classe 1",
    )
    conf_b, motivo_b = avaliar_parametro("<1,0", "AUTOMATICA", "µg/L", p_benz_357)
    assert conf_b is None and motivo_b == "UNIDADE_DIVERGENTE"

    am67019 = db_repo.obter_amostra("67019/2026")
    assert am67019 is not None
    e268 = next(e for e in am67019.ensaios if e.codigo == 268)
    assert e268.status == "Pendente"
    assert e268.sinalizacao == "UNID. DIVERGENTE"
    assert e268.unidade_trabalho == "µg/L"
    assert "mg/L" in e268.avaliacoes["CONAMA 430|Sem Classe"].vmp_texto
