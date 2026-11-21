"""Sementes de amostras mockadas e séries históricas de referência da POC."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from app.core.estatistica_historica import calcular_estatistica_historica
from app.core.models import (
    Amostra,
    AvaliacaoNorma,
    ColetaEnsaioLocal,
    EnsaioResultado,
    GrupoEnsaioLocal,
    LogAlteracao,
    NormaAplicada,
    PontoHistorico,
)
from app.core.motor_conformidade import (
    avaliar_parametro,
    calcular_status_geral,
    consolidar_status_ensaio,
    definir_sinalizacao_ensaio,
    formatar_vmp_texto,
    gerar_parecer_automatico,
    interpretar_valor_bruto,
)
from app.repo.catalog_fixtures import (
    CATALOGO_ENSAIOS,
    PARAMETROS_VMP,
    construir_norma_aplicada,
)


def construir_pontos_historicos(
    pontos_spec: list[tuple[str, date, str, str, bool]],
) -> list[PontoHistorico]:
    """Converte tuplas (rotulo_mes, data_coleta, codigo_amostra, valor_bruto, is_atual)."""
    res = []
    for rotulo, dt, cod, bruto, is_atual in pontos_spec:
        _, q, v = interpretar_valor_bruto(bruto)
        if v is None and bruto.strip().lower() == "ausente":
            v = 0.0
        res.append(
            PontoHistorico(
                data_coleta=dt,
                rotulo_mes=rotulo,
                codigo_amostra=cod,
                valor_bruto=bruto,
                valor_numerico=v,
                qualificador=q,  # type: ignore[arg-type]
                is_atual=is_atual,
            )
        )
    return res


def montar_ensaio(
    codigo: int,
    valor_bruto: str,
    normas: list[NormaAplicada],
    historico: list[PontoHistorico],
    observacao: str = "",
) -> EnsaioResultado:
    """Avalia um ensaio contra 1–3 normas, calcula estatística histórica e define sinalização."""
    meta = CATALOGO_ENSAIOS[codigo]
    _, q, v = interpretar_valor_bruto(valor_bruto)
    if v is None and valor_bruto.strip().lower() == "ausente":
        v = 0.0

    avaliacoes: dict[str, AvaliacaoNorma] = {}
    operador_principal = "MENOR_IGUAL"
    for n in normas:
        param = PARAMETROS_VMP.get((codigo, n.id))
        if not param:
            continue
        ok, motivo = avaliar_parametro(valor_bruto, meta["tipo"], meta["unidade"], param)
        vmp_ref = param.valor_max if param.valor_max is not None else param.valor_min
        operador_principal = param.operador
        avaliacoes[n.id] = AvaliacaoNorma(
            norma_id=n.id,
            norma_titulo=n.titulo_coluna,
            norma_nome_parecer=n.nome_parecer,
            vmp_texto=formatar_vmp_texto(param),
            vmp_numerico_ref=vmp_ref,
            operador=param.operador,
            conformidade=ok,
            motivo=motivo,
        )

    status = consolidar_status_ensaio(list(avaliacoes.values()))
    stats = calcular_estatistica_historica(
        pontos=historico,
        valor_atual=v,
        qualificador_atual=q,
        operador=operador_principal,
    )

    ensaio = EnsaioResultado(
        codigo=codigo,
        nome=meta["nome"],
        valor_bruto=valor_bruto,
        valor_numerico=v,
        qualificador=q,  # type: ignore[arg-type]
        unidade_trabalho=meta["unidade"],
        tipo_avaliacao=meta["tipo"],  # type: ignore[arg-type]
        avaliacoes=avaliacoes,
        status=status,  # type: ignore[arg-type]
        observacao=observacao,
        historico=historico,
        estatistica=stats,
    )
    sinal, sinal_tipo = definir_sinalizacao_ensaio(ensaio)
    ensaio.sinalizacao = sinal
    ensaio.sinalizacao_tipo = sinal_tipo  # type: ignore[arg-type]
    return ensaio


def _criar_amostra_inicial(
    codigo: str,
    data_coleta: date,
    cliente: str,
    proposta: str,
    local_coleta: str,
    origem: str,
    normas_spec: list[tuple[str, Optional[str]]],
    ensaios_spec: list[tuple[int, str, list[PontoHistorico], str]],
    logs: Optional[list[LogAlteracao]] = None,
    parecer_custom: Optional[str] = None,
) -> Amostra:
    normas = [construir_norma_aplicada(sigla, origem, cl) for sigla, cl in normas_spec]
    ensaios = [
        montar_ensaio(cod, bruto, normas, hist, obs)
        for cod, bruto, hist, obs in ensaios_spec
    ]
    amostra = Amostra(
        codigo=codigo,
        data_coleta=data_coleta,
        data_conclusao=data_coleta,
        cliente=cliente,
        proposta=proposta,
        local_coleta=local_coleta,
        origem=origem,
        normas=normas,
        ensaios=ensaios,
        logs=logs or [],
    )
    amostra.status_geral = calcular_status_geral(amostra.ensaios)  # type: ignore[assignment]
    amostra.parecer = parecer_custom or gerar_parecer_automatico(amostra)
    return amostra


def construir_sementes_mock() -> list[Amostra]:
    """Retorna as 7 amostras semente da POC cobrindo 1–3 normas, <LQ, >LS, RN-05 e RN-08."""
    _h = construir_pontos_historicos

    a1 = _criar_amostra_inicial(
        codigo="63450/2026",
        data_coleta=date(2026, 7, 15),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/088 — Monitoramento ETE",
        local_coleta="Saída — Efluente Sanitário (ETE 01)",
        origem="Efluente Tratado",
        normas_spec=[("CONAMA 430", "Sanitário (Art. 21)"), ("CONAMA 430", "Sem Classe (Art. 16)")],
        ensaios_spec=[
            (800, "40,0", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "27,4", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "28,9", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "30,5", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "32,1", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "34,8", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "40,0", True),
            ]), ""),
            (106, "71,00", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,20", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "28,4", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "34,1", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "41,8", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "46,5", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "71,00", True),
            ]), "Em análise"),
            (268, "<0,200", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,200", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "<0,200", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "<0,200", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "<0,200", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "<0,200", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "<0,200", True),
            ]), "Revisar unid."),
            (794, "7,91", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "7,85", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "7,94", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "7,88", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "7,96", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "7,89", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "7,91", True),
            ]), ""),
            (119, "<0,3", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,3", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "0,4", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "<0,3", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "0,5", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "<0,3", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "<0,3", True),
            ]), ""),
            (784, "Ausente", _h([
                ("Jan/26", date(2026, 1, 15), "58110/2026", "Ausente", False),
                ("Fev/26", date(2026, 2, 16), "59201/2026", "Ausente", False),
                ("Mar/26", date(2026, 3, 14), "60144/2026", "Ausente", False),
                ("Abr/26", date(2026, 4, 15), "61210/2026", "Ausente", False),
                ("Mai/26", date(2026, 5, 16), "62308/2026", "Ausente", False),
                ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "Ausente", True),
            ]), ""),
        ],
        logs=[
            LogAlteracao(
                id="log-1",
                data_alteracao=datetime(2026, 11, 18, 14, 35),
                usuario="samuel.wiegand",
                campo_alterado="conformidade",
                ensaio_codigo=268,
                ensaio_nome="Mercúrio",
                valor_anterior="Pendente",
                valor_novo="Pendente",
                observacao="Resultado em µg/L versus VMP em mg/L — confirmar conversão com laboratório antes do PRL.",
            ),
            LogAlteracao(
                id="log-2",
                data_alteracao=datetime(2026, 11, 18, 14, 28),
                usuario="samuel.wiegand",
                campo_alterado="minuta",
                valor_anterior="Parecer automático inicial",
                valor_novo="Detalhada violação de Nitrogênio Amoniacal (71,0 mg/L) e Temperatura no limite estrito (40,0 °C).",
            ),
        ],
    )

    a2 = _criar_amostra_inicial(
        codigo="65462/2026",
        data_coleta=date(2026, 7, 18),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Captação — Rio Itajaí-Açu",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 1")],
        ensaios_spec=[
            (48, ">45,0", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "18,5", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "21,0", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "24,2", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "26,8", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "31,4", False),
                ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", ">45,0", True),
            ]), "Chuva intensa na bacia"),
            (19, "<5,00", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "1,80", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "2,10", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "2,25", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "2,40", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "2,90", False),
                ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "<5,00", True),
            ]), "LQ acima do VMP Cl.1"),
            (157, "<0,01", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "<0,005", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "<0,005", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "0,006", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "0,007", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "<0,005", False),
                ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "<0,01", True),
            ]), "Validar sensibilidade"),
            (794, "7,15", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "7,08", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "7,12", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "7,04", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "7,10", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "7,18", False),
                ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "7,15", True),
            ]), ""),
        ],
    )

    a3 = _criar_amostra_inicial(
        codigo="67019/2026",
        data_coleta=date(2026, 7, 21),
        cliente="Têxtil Garcia S/A",
        proposta="PROP-2026/105 — Efluente Industrial",
        local_coleta="Saída Efluente Industrial 02",
        origem="Efluente Tratado",
        normas_spec=[
            ("CONAMA 430", "Sanitário (Art. 21)"),
            ("CONAMA 430", "Sem Classe (Art. 16)"),
            ("CONAMA 357", "Classe 1"),
        ],
        ensaios_spec=[
            (106, "54,2", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "14,2", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "16,8", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "18,1", False),
                ("Mai/26", date(2026, 5, 22), "63510/2026", "19,5", False),
                ("Jun/26", date(2026, 6, 20), "64899/2026", "21,0", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "54,2", True),
            ]), "Pico de carga orgânica"),
            (19, "18,5", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "12,0", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "13,4", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "11,8", False),
                ("Mai/26", date(2026, 5, 22), "63510/2026", "14,1", False),
                ("Jun/26", date(2026, 6, 20), "64899/2026", "15,0", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "18,5", True),
            ]), ""),
            (268, "<0,200", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "<0,200", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "<0,200", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "<0,200", False),
                ("Mai/26", date(2026, 5, 22), "63510/2026", "<0,200", False),
                ("Jun/26", date(2026, 6, 20), "64899/2026", "<0,200", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "<0,200", True),
            ]), "µg/L vs mg/L"),
            (800, "36,4", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "32,0", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "33,5", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "34,2", False),
                ("Mai/26", date(2026, 5, 22), "63510/2026", "35,1", False),
                ("Jun/26", date(2026, 6, 20), "64899/2026", "35,8", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "36,4", True),
            ]), ""),
            (794, "7,45", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "7,30", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "7,35", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "7,40", False),
                ("Mai/26", date(2026, 5, 22), "63510/2026", "7,38", False),
                ("Jun/26", date(2026, 6, 20), "64899/2026", "7,42", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "7,45", True),
            ]), ""),
            (784, "Ausente", _h([
                ("Fev/26", date(2026, 2, 20), "60441/2026", "Ausente", False),
                ("Mar/26", date(2026, 3, 21), "61412/2026", "Ausente", False),
                ("Abr/26", date(2026, 4, 20), "62505/2026", "Ausente", False),
                ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "Ausente", True),
            ]), ""),
        ],
    )

    a4 = _criar_amostra_inicial(
        codigo="64283/2026",
        data_coleta=date(2026, 7, 16),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Montante ETA Central",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 2")],
        ensaios_spec=[
            (59, "270", _h([
                ("Fev/26", date(2026, 2, 16), "60012/2026", "240", False),
                ("Mar/26", date(2026, 3, 16), "61045/2026", "285", False),
                ("Abr/26", date(2026, 4, 16), "62018/2026", "260", False),
                ("Mai/26", date(2026, 5, 16), "63004/2026", "310", False),
                ("Jun/26", date(2026, 6, 16), "63912/2026", "290", False),
                ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "270", True),
            ]), ""),
            (19, "2,8", _h([
                ("Fev/26", date(2026, 2, 16), "60012/2026", "2,4", False),
                ("Mar/26", date(2026, 3, 16), "61045/2026", "2,9", False),
                ("Abr/26", date(2026, 4, 16), "62018/2026", "2,6", False),
                ("Mai/26", date(2026, 5, 16), "63004/2026", "3,0", False),
                ("Jun/26", date(2026, 6, 16), "63912/2026", "2,7", False),
                ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "2,8", True),
            ]), ""),
            (48, "18,4", _h([
                ("Fev/26", date(2026, 2, 16), "60012/2026", "17,0", False),
                ("Mar/26", date(2026, 3, 16), "61045/2026", "19,2", False),
                ("Abr/26", date(2026, 4, 16), "62018/2026", "20,5", False),
                ("Mai/26", date(2026, 5, 16), "63004/2026", "18,8", False),
                ("Jun/26", date(2026, 6, 16), "63912/2026", "19,0", False),
                ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "18,4", True),
            ]), ""),
            (794, "7,12", _h([
                ("Fev/26", date(2026, 2, 16), "60012/2026", "7,05", False),
                ("Mar/26", date(2026, 3, 16), "61045/2026", "7,15", False),
                ("Abr/26", date(2026, 4, 16), "62018/2026", "7,10", False),
                ("Mai/26", date(2026, 5, 16), "63004/2026", "7,20", False),
                ("Jun/26", date(2026, 6, 16), "63912/2026", "7,14", False),
                ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "7,12", True),
            ]), ""),
        ],
    )

    a5 = _criar_amostra_inicial(
        codigo="63413/2026",
        data_coleta=date(2026, 7, 14),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/088 — Monitoramento ETE",
        local_coleta="ETE — Linha B (Lagoa)",
        origem="Efluente Tratado",
        normas_spec=[("CONAMA 430", "Sanitário (Art. 21)")],
        ensaios_spec=[
            (784, "Presente", _h([
                ("Mai/26", date(2026, 5, 14), "61990/2026", "Ausente", False),
                ("Jun/26", date(2026, 6, 14), "62780/2026", "Ausente", False),
                ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "Presente", True),
            ]), "Espuma superficial"),
            (119, "1,4", _h([
                ("Mai/26", date(2026, 5, 14), "61990/2026", "0,5", False),
                ("Jun/26", date(2026, 6, 14), "62780/2026", "0,7", False),
                ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "1,4", True),
            ]), "Histórico < 3 coletas"),
            (794, "7,30", _h([
                ("Mai/26", date(2026, 5, 14), "61990/2026", "7,10", False),
                ("Jun/26", date(2026, 6, 14), "62780/2026", "7,25", False),
                ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "7,30", True),
            ]), ""),
        ],
    )

    a6 = _criar_amostra_inicial(
        codigo="4766/2026",
        data_coleta=date(2026, 9, 1),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/091 — Potabilidade Água Tratada",
        local_coleta="Ponto 02 — Saída Tratamento",
        origem="Água Tratada",
        normas_spec=[("GM/MS 888", None), ("SES-SC 1468", None)],
        ensaios_spec=[
            (877, "42,0", _h([
                ("Abr/26", date(2026, 4, 1), "4112/2026", "<10,0", False),
                ("Mai/26", date(2026, 5, 2), "4255/2026", "14,5", False),
                ("Jun/26", date(2026, 6, 1), "4390/2026", "18,0", False),
                ("Jul/26", date(2026, 7, 2), "4510/2026", "21,5", False),
                ("Ago/26", date(2026, 8, 1), "4633/2026", "24,0", False),
                ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "42,0", True),
            ]), "Atende 888, viola 1468"),
            (48, "1,2", _h([
                ("Abr/26", date(2026, 4, 1), "4112/2026", "0,9", False),
                ("Mai/26", date(2026, 5, 2), "4255/2026", "1,1", False),
                ("Jun/26", date(2026, 6, 1), "4390/2026", "1,0", False),
                ("Jul/26", date(2026, 7, 2), "4510/2026", "1,3", False),
                ("Ago/26", date(2026, 8, 1), "4633/2026", "1,1", False),
                ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "1,2", True),
            ]), ""),
            (794, "7,25", _h([
                ("Abr/26", date(2026, 4, 1), "4112/2026", "7,15", False),
                ("Mai/26", date(2026, 5, 2), "4255/2026", "7,20", False),
                ("Jun/26", date(2026, 6, 1), "4390/2026", "7,18", False),
                ("Jul/26", date(2026, 7, 2), "4510/2026", "7,22", False),
                ("Ago/26", date(2026, 8, 1), "4633/2026", "7,24", False),
                ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "7,25", True),
            ]), ""),
        ],
    )

    a7 = _criar_amostra_inicial(
        codigo="65890/2026",
        data_coleta=date(2026, 7, 22),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Captação — Rio Itajaí-Açu",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 1")],
        ensaios_spec=[
            (19, "<5,00", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "1,80", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "2,10", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "2,25", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "2,40", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "2,90", False),
                ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "<5,00", True),
            ]), "Aguardando revisão LQ"),
            (48, "19,2", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "18,5", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "21,0", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "24,2", False),
                ("Mai/26", date(2026, 5, 18), "62890/2026", "26,8", False),
                ("Jun/26", date(2026, 6, 19), "64112/2026", "31,4", False),
                ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "19,2", True),
            ]), ""),
            (794, "7,20", _h([
                ("Fev/26", date(2026, 2, 18), "60110/2026", "7,08", False),
                ("Mar/26", date(2026, 3, 19), "61190/2026", "7,12", False),
                ("Abr/26", date(2026, 4, 18), "62100/2026", "7,04", False),
                ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "7,20", True),
            ]), ""),
        ],
    )

    return [a1, a2, a3, a4, a5, a6, a7]


# Séries mensais base da tela B5 (rotulo_mes, favoraveis, pendentes, nao_favoraveis)
SERIES_MENSAIS_BASE: dict[str, list[tuple[str, int, int, int]]] = {
    "Captação — Rio Itajaí-Açu": [
        ("Ago/25", 5, 0, 1), ("Set/25", 6, 0, 0), ("Out/25", 5, 1, 0),
        ("Nov/25", 4, 1, 1), ("Dez/25", 6, 0, 0), ("Jan/26", 5, 1, 0),
        ("Fev/26", 5, 1, 0), ("Mar/26", 6, 0, 0), ("Abr/26", 4, 1, 1),
        ("Mai/26", 5, 0, 1), ("Jun/26", 4, 2, 0), ("Jul/26", 4, 1, 1),
    ],
    "Saída — Efluente Sanitário (ETE 01)": [
        ("Ago/25", 4, 1, 1), ("Set/25", 5, 0, 1), ("Out/25", 5, 1, 0),
        ("Nov/25", 6, 0, 0), ("Dez/25", 4, 1, 1), ("Jan/26", 5, 0, 1),
        ("Fev/26", 4, 1, 1), ("Mar/26", 5, 1, 0), ("Abr/26", 4, 0, 2),
        ("Mai/26", 3, 1, 2), ("Jun/26", 4, 1, 1), ("Jul/26", 3, 1, 2),
    ],
    "Saída Efluente Industrial 02": [
        ("Ago/25", 3, 1, 1), ("Set/25", 4, 1, 0), ("Out/25", 3, 2, 0),
        ("Nov/25", 4, 0, 1), ("Dez/25", 4, 1, 0), ("Jan/26", 3, 1, 1),
        ("Fev/26", 4, 1, 0), ("Mar/26", 3, 1, 1), ("Abr/26", 3, 2, 1),
        ("Mai/26", 4, 1, 0), ("Jun/26", 2, 1, 2), ("Jul/26", 2, 1, 2),
    ],
    "Montante ETA Central": [
        ("Ago/25", 6, 0, 0), ("Set/25", 6, 0, 0), ("Out/25", 5, 1, 0),
        ("Nov/25", 6, 0, 0), ("Dez/25", 6, 0, 0), ("Jan/26", 6, 0, 0),
        ("Fev/26", 6, 0, 0), ("Mar/26", 6, 0, 0), ("Abr/26", 5, 1, 0),
        ("Mai/26", 6, 0, 0), ("Jun/26", 6, 0, 0), ("Jul/26", 6, 0, 0),
    ],
}

SERIE_MENSAL_FALLBACK: list[tuple[str, int, int, int]] = [
    ("Fev/26", 4, 1, 0), ("Mar/26", 5, 0, 0), ("Abr/26", 4, 0, 1),
    ("Mai/26", 4, 1, 1), ("Jun/26", 5, 0, 0), ("Jul/26", 3, 1, 1),
]


def construir_grupos_referencia_samae_cl1() -> list[GrupoEnsaioLocal]:
    """Fixture de referência da tela B5 (SAMAE Blumenau · Captação Rio Itajaí-Açu · CONAMA 357 Cl. 1)."""
    return [
        GrupoEnsaioLocal(
            codigo_ensaio=19,
            nome_ensaio="DBO (5 dias)",
            unidade="mg/L",
            total_coletas=6,
            media_texto="2,22 mg/L",
            conformidade_pct="83,3%",
            nao_conformes=0,
            pendentes_desvios_texto="1 Pendente (<LQ)",
            coletas=[
                ColetaEnsaioLocal(codigo_amostra="65462/2026", data_coleta=date(2026, 7, 18), valor_bruto="<5,00", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="PENDENTE (<LQ)", badge_variant="outline-gray"),
                ColetaEnsaioLocal(codigo_amostra="64112/2026", data_coleta=date(2026, 6, 19), valor_bruto="2,90", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="DESVIO > μ+0,20σ", badge_variant="outline-amber"),
                ColetaEnsaioLocal(codigo_amostra="62890/2026", data_coleta=date(2026, 5, 18), valor_bruto="2,40", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="62100/2026", data_coleta=date(2026, 4, 18), valor_bruto="2,25", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="61190/2026", data_coleta=date(2026, 3, 19), valor_bruto="2,10", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="60110/2026", data_coleta=date(2026, 2, 18), valor_bruto="1,80", unidade="mg/L", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 3,0 mg/L", badge_texto="CONFORME", badge_variant="outline-green"),
            ],
        ),
        GrupoEnsaioLocal(
            codigo_ensaio=59,
            nome_ensaio="Coliformes Termotolerantes",
            unidade="UFC/100mL",
            total_coletas=6,
            media_texto="168 UFC/100mL",
            conformidade_pct="83,3%",
            nao_conformes=1,
            pendentes_desvios_texto="0",
            coletas=[
                ColetaEnsaioLocal(codigo_amostra="65462/2026", data_coleta=date(2026, 7, 18), valor_bruto="145", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="64112/2026", data_coleta=date(2026, 6, 19), valor_bruto="162", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="62890/2026", data_coleta=date(2026, 5, 18), valor_bruto="270", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="NÃO CONFORME", badge_variant="solid-red"),
                ColetaEnsaioLocal(codigo_amostra="62100/2026", data_coleta=date(2026, 4, 18), valor_bruto="158", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="61190/2026", data_coleta=date(2026, 3, 19), valor_bruto="140", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="60110/2026", data_coleta=date(2026, 2, 18), valor_bruto="133", unidade="UFC/100mL", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 200 UFC/100mL", badge_texto="CONFORME", badge_variant="outline-green"),
            ],
        ),
        GrupoEnsaioLocal(
            codigo_ensaio=48,
            nome_ensaio="Turbidez",
            unidade="NTU",
            total_coletas=6,
            media_texto="24,8 NTU",
            conformidade_pct="100,0%",
            nao_conformes=0,
            pendentes_desvios_texto="1 Desvio (> μ+0,20σ)",
            coletas=[
                ColetaEnsaioLocal(codigo_amostra="65462/2026", data_coleta=date(2026, 7, 18), valor_bruto="34,2", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="DESVIO > μ+0,20σ", badge_variant="outline-amber"),
                ColetaEnsaioLocal(codigo_amostra="64112/2026", data_coleta=date(2026, 6, 19), valor_bruto="28,4", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="62890/2026", data_coleta=date(2026, 5, 18), valor_bruto="25,1", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="62100/2026", data_coleta=date(2026, 4, 18), valor_bruto="22,6", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="61190/2026", data_coleta=date(2026, 3, 19), valor_bruto="20,0", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="CONFORME", badge_variant="outline-green"),
                ColetaEnsaioLocal(codigo_amostra="60110/2026", data_coleta=date(2026, 2, 18), valor_bruto="18,5", unidade="NTU", vmp_prefixo="VMP Cl. 1", vmp_texto="≤ 40,0 NTU", badge_texto="CONFORME", badge_variant="outline-green"),
            ],
        ),
    ]
