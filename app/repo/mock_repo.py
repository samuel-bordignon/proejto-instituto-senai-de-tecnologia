"""Repositório mockado em memória para a POC NiceGUI do LaudoTech."""

from __future__ import annotations

import copy
import uuid
from datetime import date, datetime
from typing import Optional

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    GERAL_PENDENTE,
)
from app.core.estatistica_historica import calcular_estatistica_historica
from app.core.models import (
    Amostra,
    AvaliacaoNorma,
    ColetaEnsaioLocal,
    EnsaioResultado,
    GrupoEnsaioLocal,
    LogAlteracao,
    MesConformidadeLocal,
    NormaAplicada,
    ParametroNorma,
    PontoHistorico,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
    Usuario,
)
from app.core.motor_conformidade import (
    avaliar_parametro,
    calcular_status_geral,
    consolidar_status_ensaio,
    definir_sinalizacao_ensaio,
    formatar_numero_br,
    formatar_vmp_texto,
    gerar_parecer_automatico,
    interpretar_valor_bruto,
)

# ---------------------------------------------------------------------------
# 1. Usuários mockados (RF-01 / RNF-05)
# ---------------------------------------------------------------------------
USUARIOS_MOCK: dict[str, Usuario] = {
    "samuel.wiegand": Usuario(id="u-1", nome_usuario="samuel.wiegand", senha_hash="123456"),
    "maria.cardoso": Usuario(id="u-2", nome_usuario="maria.cardoso", senha_hash="123456"),
    "bruno.dombroski": Usuario(id="u-3", nome_usuario="bruno.dombroski", senha_hash="123456"),
    "conferente": Usuario(id="u-4", nome_usuario="conferente", senha_hash="123456"),
}

# ---------------------------------------------------------------------------
# 2. Catálogo de Ensaios UltraLIMS (código id_num + unidade de trabalho acreditada)
# ---------------------------------------------------------------------------
CATALOGO_ENSAIOS: dict[int, dict[str, str]] = {
    800: {"nome": "Temperatura - Água", "unidade": "°C", "tipo": "AUTOMATICA"},
    106: {"nome": "Nitrogênio Amoniacal", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    268: {"nome": "Mercúrio", "unidade": "µg/L", "tipo": "AUTOMATICA"},
    794: {"nome": "pH", "unidade": "", "tipo": "AUTOMATICA"},
    119: {"nome": "Sólidos Sedimentáveis", "unidade": "mL/L", "tipo": "AUTOMATICA"},
    784: {"nome": "Materiais Flutuantes", "unidade": "", "tipo": "AUTOMATICA"},
    19: {"nome": "DBO (5 dias)", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    59: {"nome": "Coliformes Termotolerantes", "unidade": "UFC/100mL", "tipo": "AUTOMATICA"},
    48: {"nome": "Turbidez", "unidade": "NTU", "tipo": "AUTOMATICA"},
    157: {"nome": "Cobre Dissolvido", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    877: {"nome": "Glifosato + AMPA", "unidade": "µg/L", "tipo": "AUTOMATICA"},
    259: {"nome": "Chumbo Total", "unidade": "mg/L", "tipo": "AUTOMATICA"},
}

# ---------------------------------------------------------------------------
# 3. Contexto Comercial (Cliente -> Proposta -> Locais) e Origens
# ---------------------------------------------------------------------------
CLIENTES_PROPOSTAS_LOCAIS: dict[str, dict[str, list[str]]] = {
    "Cervejaria Vale do Itajaí Ltda": {
        "PROP-2026/088 — Monitoramento ETE": [
            "Saída — Efluente Sanitário (ETE 01)",
            "ETE — Linha B (Lagoa)",
        ],
        "PROP-2026/091 — Potabilidade Água Tratada": [
            "Ponto 02 — Saída Tratamento",
            "Reservatório Principal",
        ],
    },
    "SAMAE Blumenau": {
        "PROP-2026/042 — Monitoramento Águas Superficiais": [
            "Captação — Rio Itajaí-Açu",
            "Montante ETA Central",
        ],
    },
    "Têxtil Garcia S/A": {
        "PROP-2026/105 — Efluente Industrial": [
            "Saída Efluente Industrial 02",
            "Caixa de Equalização 01",
        ],
    },
}

ORIGENS_AMOSTRA: list[str] = [
    "Efluente Tratado",
    "Água Superficial",
    "Água Tratada",
    "Água Consumo Humano",
]

# Legislações compatíveis por Origem e suas Classes (vazio = Portaria sem classe)
LEGISLACOES_CATALOGO: dict[str, dict] = {
    "CONAMA 430": {
        "sigla": "CONAMA 430",
        "nome_completo": "Resolução CONAMA 430/2011",
        "origens": ["Efluente Tratado"],
        "classes": ["Sanitário (Art. 21)", "Sem Classe (Art. 16)"],
    },
    "CONAMA 357": {
        "sigla": "CONAMA 357",
        "nome_completo": "Resolução CONAMA 357/2005",
        "origens": ["Água Superficial", "Efluente Tratado"],
        "classes": ["Classe 1", "Classe 2", "Classe 3"],
    },
    "GM/MS 888": {
        "sigla": "GM/MS 888",
        "nome_completo": "Portaria GM/MS 888/2021",
        "origens": ["Água Tratada", "Água Consumo Humano"],
        "classes": [],
    },
    "SES-SC 1468": {
        "sigla": "SES-SC 1468",
        "nome_completo": "Portaria SES/SC 1468/2022",
        "origens": ["Água Tratada", "Água Consumo Humano", "Água Superficial"],
        "classes": [],
    },
}


def _norma_key(sigla: str, classe: Optional[str]) -> str:
    if classe:
        c_short = (
            classe.replace(" (Art. 21)", "")
            .replace(" (Art. 16)", "")
            .replace("Águas Doces — ", "")
            .strip()
        )
        return f"{sigla}|{c_short}"
    return f"{sigla}|"


def construir_norma_aplicada(sigla: str, origem: str, classe: Optional[str] = None) -> NormaAplicada:
    meta = LEGISLACOES_CATALOGO[sigla]
    c_clean = (
        classe.replace(" (Art. 21)", "").replace(" (Art. 16)", "").strip()
        if classe
        else None
    )
    return NormaAplicada(
        id=_norma_key(sigla, c_clean),
        sigla=meta["sigla"],
        nome_completo=meta["nome_completo"],
        origem=origem,
        classe=c_clean,
    )


# ---------------------------------------------------------------------------
# 4. Tabela de Parâmetros / VMPs por (id_num, norma_id)
# ---------------------------------------------------------------------------
def _p(
    norma_id: str,
    sigla: str,
    nome_completo: str,
    classe: Optional[str],
    operador: str,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    esperado: Optional[str] = None,
    unidade: str = "",
) -> ParametroNorma:
    return ParametroNorma(
        norma_id=norma_id,
        norma_sigla=sigla,
        norma_nome_completo=nome_completo,
        classe_nome=classe,
        operador=operador,  # type: ignore[arg-type]
        valor_min=vmin,
        valor_max=vmax,
        valor_esperado=esperado,
        unidade=unidade,
    )


PARAMETROS_VMP: dict[tuple[int, str], ParametroNorma] = {
    # CONAMA 430 — Sanitário (Art. 21)
    (800, "CONAMA 430|Sanitário"): _p("CONAMA 430|Sanitário", "CONAMA 430", "Resolução CONAMA 430/2011", "Sanitário", "MENOR_ESTRITO", vmax=40.0, unidade="°C"),
    (794, "CONAMA 430|Sanitário"): _p("CONAMA 430|Sanitário", "CONAMA 430", "Resolução CONAMA 430/2011", "Sanitário", "FAIXA", vmin=5.0, vmax=9.0, unidade=""),
    (119, "CONAMA 430|Sanitário"): _p("CONAMA 430|Sanitário", "CONAMA 430", "Resolução CONAMA 430/2011", "Sanitário", "MENOR_IGUAL", vmax=1.0, unidade="mL/L"),
    (784, "CONAMA 430|Sanitário"): _p("CONAMA 430|Sanitário", "CONAMA 430", "Resolução CONAMA 430/2011", "Sanitário", "AUSENCIA", esperado="Ausente", unidade=""),
    (19, "CONAMA 430|Sanitário"): _p("CONAMA 430|Sanitário", "CONAMA 430", "Resolução CONAMA 430/2011", "Sanitário", "MENOR_IGUAL", vmax=120.0, unidade="mg/L"),

    # CONAMA 430 — Sem Classe (Art. 16)
    (800, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_ESTRITO", vmax=40.0, unidade="°C"),
    (106, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_IGUAL", vmax=20.0, unidade="mg/L"),
    (268, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_IGUAL", vmax=0.01, unidade="mg/L"),  # diverge de µg/L (RN-05!)
    (794, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "FAIXA", vmin=5.0, vmax=9.0, unidade=""),
    (119, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_IGUAL", vmax=1.0, unidade="mL/L"),
    (784, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "AUSENCIA", esperado="Ausente", unidade=""),
    (259, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_IGUAL", vmax=0.5, unidade="mg/L"),

    # CONAMA 357 — Classe 1
    (19, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=3.0, unidade="mg/L"),
    (59, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=200.0, unidade="UFC/100mL"),
    (48, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=40.0, unidade="NTU"),
    (157, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=0.009, unidade="mg/L"),
    (794, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "FAIXA", vmin=6.0, vmax=9.0, unidade=""),
    (106, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=3.7, unidade="mg/L"),
    (268, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "MENOR_IGUAL", vmax=0.0002, unidade="mg/L"),
    (784, "CONAMA 357|Classe 1"): _p("CONAMA 357|Classe 1", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 1", "AUSENCIA", esperado="Ausente", unidade=""),

    # CONAMA 357 — Classe 2
    (19, "CONAMA 357|Classe 2"): _p("CONAMA 357|Classe 2", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 2", "MENOR_IGUAL", vmax=5.0, unidade="mg/L"),
    (59, "CONAMA 357|Classe 2"): _p("CONAMA 357|Classe 2", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 2", "MENOR_IGUAL", vmax=1000.0, unidade="UFC/100mL"),
    (48, "CONAMA 357|Classe 2"): _p("CONAMA 357|Classe 2", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 2", "MENOR_IGUAL", vmax=100.0, unidade="NTU"),
    (157, "CONAMA 357|Classe 2"): _p("CONAMA 357|Classe 2", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 2", "MENOR_IGUAL", vmax=0.009, unidade="mg/L"),
    (794, "CONAMA 357|Classe 2"): _p("CONAMA 357|Classe 2", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 2", "FAIXA", vmin=6.0, vmax=9.0, unidade=""),

    # CONAMA 357 — Classe 3
    (19, "CONAMA 357|Classe 3"): _p("CONAMA 357|Classe 3", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 3", "MENOR_IGUAL", vmax=10.0, unidade="mg/L"),
    (59, "CONAMA 357|Classe 3"): _p("CONAMA 357|Classe 3", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 3", "MENOR_IGUAL", vmax=4000.0, unidade="UFC/100mL"),
    (48, "CONAMA 357|Classe 3"): _p("CONAMA 357|Classe 3", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 3", "MENOR_IGUAL", vmax=100.0, unidade="NTU"),
    (157, "CONAMA 357|Classe 3"): _p("CONAMA 357|Classe 3", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 3", "MENOR_IGUAL", vmax=0.013, unidade="mg/L"),
    (794, "CONAMA 357|Classe 3"): _p("CONAMA 357|Classe 3", "CONAMA 357", "Resolução CONAMA 357/2005", "Classe 3", "FAIXA", vmin=6.0, vmax=9.0, unidade=""),

    # Portaria GM/MS 888/2021
    (877, "GM/MS 888|"): _p("GM/MS 888|", "GM/MS 888", "Portaria GM/MS 888/2021", None, "MENOR_IGUAL", vmax=500.0, unidade="µg/L"),
    (48, "GM/MS 888|"): _p("GM/MS 888|", "GM/MS 888", "Portaria GM/MS 888/2021", None, "MENOR_IGUAL", vmax=5.0, unidade="NTU"),
    (794, "GM/MS 888|"): _p("GM/MS 888|", "GM/MS 888", "Portaria GM/MS 888/2021", None, "FAIXA", vmin=6.0, vmax=9.5, unidade=""),
    (268, "GM/MS 888|"): _p("GM/MS 888|", "GM/MS 888", "Portaria GM/MS 888/2021", None, "MENOR_IGUAL", vmax=1.0, unidade="µg/L"),

    # Portaria SES-SC 1468/2022
    (877, "SES-SC 1468|"): _p("SES-SC 1468|", "SES-SC 1468", "Portaria SES/SC 1468/2022", None, "MENOR_IGUAL", vmax=30.0, unidade="µg/L"),
    (48, "SES-SC 1468|"): _p("SES-SC 1468|", "SES-SC 1468", "Portaria SES/SC 1468/2022", None, "MENOR_IGUAL", vmax=5.0, unidade="NTU"),
    (794, "SES-SC 1468|"): _p("SES-SC 1468|", "SES-SC 1468", "Portaria SES/SC 1468/2022", None, "FAIXA", vmin=6.0, vmax=9.5, unidade=""),
    (268, "SES-SC 1468|"): _p("SES-SC 1468|", "SES-SC 1468", "Portaria SES/SC 1468/2022", None, "MENOR_IGUAL", vmax=1.0, unidade="µg/L"),
}


# ---------------------------------------------------------------------------
# 5. Auxiliar para montar EnsaioResultado completo + histórico
# ---------------------------------------------------------------------------
def _hist(pontos_spec: list[tuple[str, date, str, str, bool]]) -> list[PontoHistorico]:
    """pontos_spec: lista de (rotulo_mes, data_coleta, codigo_amostra, valor_bruto, is_atual)."""
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


def _montar_ensaio(
    codigo: int,
    valor_bruto: str,
    normas: list[NormaAplicada],
    historico: list[PontoHistorico],
    observacao: str = "",
) -> EnsaioResultado:
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
        _montar_ensaio(cod, bruto, normas, hist, obs)
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


def _construir_sementes_mock() -> list[Amostra]:
    # 1) Amostra 63450/2026 — Caso principal do Figma B2/B4/B4b/OV3
    a1 = _criar_amostra_inicial(
        codigo="63450/2026",
        data_coleta=date(2026, 7, 15),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/088 — Monitoramento ETE",
        local_coleta="Saída — Efluente Sanitário (ETE 01)",
        origem="Efluente Tratado",
        normas_spec=[("CONAMA 430", "Sanitário (Art. 21)"), ("CONAMA 430", "Sem Classe (Art. 16)")],
        ensaios_spec=[
            (
                800,
                "40,0",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "27,4", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "28,9", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "30,5", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "32,1", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "34,8", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "40,0", True),
                ]),
                "",
            ),
            (
                106,
                "71,00",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,20", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "28,4", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "34,1", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "41,8", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "46,5", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "71,00", True),
                ]),
                "Em análise",
            ),
            (
                268,
                "<0,200",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,200", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "<0,200", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "<0,200", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "<0,200", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "<0,200", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "<0,200", True),
                ]),
                "Revisar unid.",
            ),
            (
                794,
                "7,91",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "7,85", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "7,94", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "7,88", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "7,96", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "7,89", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "7,91", True),
                ]),
                "",
            ),
            (
                119,
                "<0,3",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "<0,3", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "0,4", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "<0,3", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "0,5", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "<0,3", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "<0,3", True),
                ]),
                "",
            ),
            (
                784,
                "Ausente",
                _hist([
                    ("Jan/26", date(2026, 1, 15), "58110/2026", "Ausente", False),
                    ("Fev/26", date(2026, 2, 16), "59201/2026", "Ausente", False),
                    ("Mar/26", date(2026, 3, 14), "60144/2026", "Ausente", False),
                    ("Abr/26", date(2026, 4, 15), "61210/2026", "Ausente", False),
                    ("Mai/26", date(2026, 5, 16), "62308/2026", "Ausente", False),
                    ("Jul/26 Atual", date(2026, 7, 15), "63450/2026", "Ausente", True),
                ]),
                "",
            ),
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

    # 2) Amostra 65462/2026 — SAMAE Blumenau (CONAMA 357 Classe 1 — <LQ Pendente + >LS no gráfico)
    a2 = _criar_amostra_inicial(
        codigo="65462/2026",
        data_coleta=date(2026, 7, 18),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Captação — Rio Itajaí-Açu",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 1")],
        ensaios_spec=[
            (
                48,
                ">45,0",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "18,5", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "21,0", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "24,2", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "26,8", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "31,4", False),
                    ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", ">45,0", True),
                ]),
                "Chuva intensa na bacia",
            ),
            (
                19,
                "<5,00",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "1,80", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "2,10", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "2,25", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "2,40", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "2,90", False),
                    ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "<5,00", True),
                ]),
                "LQ acima do VMP Cl.1",
            ),
            (
                157,
                "<0,01",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "<0,005", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "<0,005", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "0,006", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "0,007", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "<0,005", False),
                    ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "<0,01", True),
                ]),
                "Validar sensibilidade",
            ),
            (
                794,
                "7,15",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "7,08", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "7,12", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "7,04", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "7,10", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "7,18", False),
                    ("Jul/26 Atual", date(2026, 7, 18), "65462/2026", "7,15", True),
                ]),
                "",
            ),
        ],
    )

    # 3) Amostra 67019/2026 — Têxtil Garcia S/A (VERSÃO COM 3 NORMAS SIMULTÂNEAS — Seção 6.5!)
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
            (
                106,
                "54,2",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "14,2", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "16,8", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "18,1", False),
                    ("Mai/26", date(2026, 5, 22), "63510/2026", "19,5", False),
                    ("Jun/26", date(2026, 6, 20), "64899/2026", "21,0", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "54,2", True),
                ]),
                "Pico de carga orgânica",
            ),
            (
                19,
                "18,5",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "12,0", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "13,4", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "11,8", False),
                    ("Mai/26", date(2026, 5, 22), "63510/2026", "14,1", False),
                    ("Jun/26", date(2026, 6, 20), "64899/2026", "15,0", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "18,5", True),
                ]),
                "",
            ),
            (
                268,
                "<0,200",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "<0,200", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "<0,200", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "<0,200", False),
                    ("Mai/26", date(2026, 5, 22), "63510/2026", "<0,200", False),
                    ("Jun/26", date(2026, 6, 20), "64899/2026", "<0,200", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "<0,200", True),
                ]),
                "µg/L vs mg/L",
            ),
            (
                800,
                "36,4",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "32,0", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "33,5", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "34,2", False),
                    ("Mai/26", date(2026, 5, 22), "63510/2026", "35,1", False),
                    ("Jun/26", date(2026, 6, 20), "64899/2026", "35,8", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "36,4", True),
                ]),
                "",
            ),
            (
                794,
                "7,45",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "7,30", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "7,35", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "7,40", False),
                    ("Mai/26", date(2026, 5, 22), "63510/2026", "7,38", False),
                    ("Jun/26", date(2026, 6, 20), "64899/2026", "7,42", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "7,45", True),
                ]),
                "",
            ),
            (
                784,
                "Ausente",
                _hist([
                    ("Fev/26", date(2026, 2, 20), "60441/2026", "Ausente", False),
                    ("Mar/26", date(2026, 3, 21), "61412/2026", "Ausente", False),
                    ("Abr/26", date(2026, 4, 20), "62505/2026", "Ausente", False),
                    ("Jul/26 Atual", date(2026, 7, 21), "67019/2026", "Ausente", True),
                ]),
                "",
            ),
        ],
    )

    # 4) Amostra 64283/2026 — SAMAE Blumenau (CONAMA 357 Classe 2 — 100% FAVORÁVEL)
    a4 = _criar_amostra_inicial(
        codigo="64283/2026",
        data_coleta=date(2026, 7, 16),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Montante ETA Central",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 2")],
        ensaios_spec=[
            (
                59,
                "270",
                _hist([
                    ("Fev/26", date(2026, 2, 16), "60012/2026", "240", False),
                    ("Mar/26", date(2026, 3, 16), "61045/2026", "285", False),
                    ("Abr/26", date(2026, 4, 16), "62018/2026", "260", False),
                    ("Mai/26", date(2026, 5, 16), "63004/2026", "310", False),
                    ("Jun/26", date(2026, 6, 16), "63912/2026", "290", False),
                    ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "270", True),
                ]),
                "",
            ),
            (
                19,
                "2,8",
                _hist([
                    ("Fev/26", date(2026, 2, 16), "60012/2026", "2,4", False),
                    ("Mar/26", date(2026, 3, 16), "61045/2026", "2,9", False),
                    ("Abr/26", date(2026, 4, 16), "62018/2026", "2,6", False),
                    ("Mai/26", date(2026, 5, 16), "63004/2026", "3,0", False),
                    ("Jun/26", date(2026, 6, 16), "63912/2026", "2,7", False),
                    ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "2,8", True),
                ]),
                "",
            ),
            (
                48,
                "18,4",
                _hist([
                    ("Fev/26", date(2026, 2, 16), "60012/2026", "17,0", False),
                    ("Mar/26", date(2026, 3, 16), "61045/2026", "19,2", False),
                    ("Abr/26", date(2026, 4, 16), "62018/2026", "20,5", False),
                    ("Mai/26", date(2026, 5, 16), "63004/2026", "18,8", False),
                    ("Jun/26", date(2026, 6, 16), "63912/2026", "19,0", False),
                    ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "18,4", True),
                ]),
                "",
            ),
            (
                794,
                "7,12",
                _hist([
                    ("Fev/26", date(2026, 2, 16), "60012/2026", "7,05", False),
                    ("Mar/26", date(2026, 3, 16), "61045/2026", "7,15", False),
                    ("Abr/26", date(2026, 4, 16), "62018/2026", "7,10", False),
                    ("Mai/26", date(2026, 5, 16), "63004/2026", "7,20", False),
                    ("Jun/26", date(2026, 6, 16), "63912/2026", "7,14", False),
                    ("Jul/26 Atual", date(2026, 7, 16), "64283/2026", "7,12", True),
                ]),
                "",
            ),
        ],
    )

    # 5) Amostra 63413/2026 — Cervejaria Vale do Itajaí (Qualitativo Presente + Histórico n<3)
    a5 = _criar_amostra_inicial(
        codigo="63413/2026",
        data_coleta=date(2026, 7, 14),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/088 — Monitoramento ETE",
        local_coleta="ETE — Linha B (Lagoa)",
        origem="Efluente Tratado",
        normas_spec=[("CONAMA 430", "Sanitário (Art. 21)")],
        ensaios_spec=[
            (
                784,
                "Presente",
                _hist([
                    ("Mai/26", date(2026, 5, 14), "61990/2026", "Ausente", False),
                    ("Jun/26", date(2026, 6, 14), "62780/2026", "Ausente", False),
                    ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "Presente", True),
                ]),
                "Espuma superficial",
            ),
            (
                119,
                "1,4",
                _hist([
                    ("Mai/26", date(2026, 5, 14), "61990/2026", "0,5", False),
                    ("Jun/26", date(2026, 6, 14), "62780/2026", "0,7", False),
                    ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "1,4", True),
                ]),
                "Histórico < 3 coletas",
            ),
            (
                794,
                "7,30",
                _hist([
                    ("Mai/26", date(2026, 5, 14), "61990/2026", "7,10", False),
                    ("Jun/26", date(2026, 6, 14), "62780/2026", "7,25", False),
                    ("Jul/26 Atual", date(2026, 7, 14), "63413/2026", "7,30", True),
                ]),
                "",
            ),
        ],
    )

    # 6) Amostra 4766/2026 — Potabilidade (Conflito GM/MS 888 vs SES-SC 1468 — CT-02)
    a6 = _criar_amostra_inicial(
        codigo="4766/2026",
        data_coleta=date(2026, 9, 1),
        cliente="Cervejaria Vale do Itajaí Ltda",
        proposta="PROP-2026/091 — Potabilidade Água Tratada",
        local_coleta="Ponto 02 — Saída Tratamento",
        origem="Água Tratada",
        normas_spec=[("GM/MS 888", None), ("SES-SC 1468", None)],
        ensaios_spec=[
            (
                877,
                "42,0",
                _hist([
                    ("Abr/26", date(2026, 4, 1), "4112/2026", "<10,0", False),
                    ("Mai/26", date(2026, 5, 2), "4255/2026", "14,5", False),
                    ("Jun/26", date(2026, 6, 1), "4390/2026", "18,0", False),
                    ("Jul/26", date(2026, 7, 2), "4510/2026", "21,5", False),
                    ("Ago/26", date(2026, 8, 1), "4633/2026", "24,0", False),
                    ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "42,0", True),
                ]),
                "Atende 888, viola 1468",
            ),
            (
                48,
                "1,2",
                _hist([
                    ("Abr/26", date(2026, 4, 1), "4112/2026", "0,9", False),
                    ("Mai/26", date(2026, 5, 2), "4255/2026", "1,1", False),
                    ("Jun/26", date(2026, 6, 1), "4390/2026", "1,0", False),
                    ("Jul/26", date(2026, 7, 2), "4510/2026", "1,3", False),
                    ("Ago/26", date(2026, 8, 1), "4633/2026", "1,1", False),
                    ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "1,2", True),
                ]),
                "",
            ),
            (
                794,
                "7,25",
                _hist([
                    ("Abr/26", date(2026, 4, 1), "4112/2026", "7,15", False),
                    ("Mai/26", date(2026, 5, 2), "4255/2026", "7,20", False),
                    ("Jun/26", date(2026, 6, 1), "4390/2026", "7,18", False),
                    ("Jul/26", date(2026, 7, 2), "4510/2026", "7,22", False),
                    ("Ago/26", date(2026, 8, 1), "4633/2026", "7,24", False),
                    ("Set/26 Atual", date(2026, 9, 1), "4766/2026", "7,25", True),
                ]),
                "",
            ),
        ],
    )

    # 7) Amostra 65890/2026 — Pendente puro (para testar filtro "Pendente" no Painel!)
    a7 = _criar_amostra_inicial(
        codigo="65890/2026",
        data_coleta=date(2026, 7, 22),
        cliente="SAMAE Blumenau",
        proposta="PROP-2026/042 — Monitoramento Águas Superficiais",
        local_coleta="Captação — Rio Itajaí-Açu",
        origem="Água Superficial",
        normas_spec=[("CONAMA 357", "Classe 1")],
        ensaios_spec=[
            (
                19,
                "<5,00",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "1,80", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "2,10", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "2,25", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "2,40", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "2,90", False),
                    ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "<5,00", True),
                ]),
                "Aguardando revisão LQ",
            ),
            (
                48,
                "19,2",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "18,5", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "21,0", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "24,2", False),
                    ("Mai/26", date(2026, 5, 18), "62890/2026", "26,8", False),
                    ("Jun/26", date(2026, 6, 19), "64112/2026", "31,4", False),
                    ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "19,2", True),
                ]),
                "",
            ),
            (
                794,
                "7,20",
                _hist([
                    ("Fev/26", date(2026, 2, 18), "60110/2026", "7,08", False),
                    ("Mar/26", date(2026, 3, 19), "61190/2026", "7,12", False),
                    ("Abr/26", date(2026, 4, 18), "62100/2026", "7,04", False),
                    ("Jul/26 Atual", date(2026, 7, 22), "65890/2026", "7,20", True),
                ]),
                "",
            ),
        ],
    )

    return [a1, a2, a3, a4, a5, a6, a7]


class MockRepository:
    """Repositório em memória (singleton da POC) com contrato limpo para futura migração SQLAlchemy."""

    def __init__(self) -> None:
        self._amostras: dict[str, Amostra] = {a.codigo: a for a in _construir_sementes_mock()}
        self._ordem: list[str] = list(self._amostras.keys())
        self._seq_codigo: int = 68410

    # --- Autenticação (RF-01) ---
    def autenticar(self, nome_usuario: str, senha: str) -> Optional[Usuario]:
        u = USUARIOS_MOCK.get(nome_usuario.strip().lower())
        if u and u.senha_hash == senha:
            return u
        return None

    # --- Contexto & Normas (RF-02) ---
    def listar_clientes(self) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.keys())

    def listar_propostas(self, cliente: str) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).keys())

    def listar_locais(self, cliente: str, proposta: str) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).get(proposta, []))

    def listar_locais_por_cliente(self, cliente: str) -> list[str]:
        locais: list[str] = []
        for lista in CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).values():
            for loc in lista:
                if loc not in locais:
                    locais.append(loc)
        return locais

    def listar_origens(self) -> list[str]:
        return list(ORIGENS_AMOSTRA)

    def listar_legislacoes_por_origem(self, origem: str) -> list[dict]:
        return [
            meta
            for meta in LEGISLACOES_CATALOGO.values()
            if origem in meta["origens"]
        ]

    def listar_classes_legislacao(self, sigla: str) -> list[str]:
        return list(LEGISLACOES_CATALOGO.get(sigla, {}).get("classes", []))

    # --- Painel (B2) ---
    def listar_amostras(
        self,
        status_filtro: str = "Todos",
        busca: str = "",
    ) -> list[Amostra]:
        termo = busca.strip().lower()
        resultado: list[Amostra] = []
        for cod in self._ordem:
            a = self._amostras[cod]
            if status_filtro in (GERAL_FAVORAVEL, GERAL_NAO_FAVORAVEL, GERAL_PENDENTE):
                if a.status_geral != status_filtro:
                    continue
            if termo:
                haystack = f"{a.codigo} {a.cliente} {a.local_coleta} {a.normas_resumo}".lower()
                if termo not in haystack:
                    continue
            resultado.append(copy.deepcopy(a))
        return resultado

    def obter_amostra(self, codigo: str) -> Optional[Amostra]:
        a = self._amostras.get(codigo)
        if a:
            return copy.deepcopy(a)
        # Se for uma amostra histórica aberta a partir da tela B5, gera sob demanda com os dados da coleta
        hist_a = self._materializar_amostra_historica(codigo)
        if hist_a:
            return copy.deepcopy(hist_a)
        return None

    # --- Conferência & Auditoria (RF-05 / RN-10 / CT-16 / CT-17 / CT-18) ---
    def salvar_conferencia(
        self,
        codigo: str,
        edicoes_status: dict[int, str],
        edicoes_obs: dict[int, str],
        novo_parecer: str,
        usuario: str,
    ) -> tuple[Amostra, int]:
        """
        Persiste alterações em memória e registra linhas imutáveis em log_alteracao:
          - 1 linha por ensaio com conformidade alterada (campo_alterado = 'conformidade')
          - 1 linha extra se o status geral derivado mudou (campo_alterado = 'parecer_geral')
          - 1 linha se o texto do parecer foi alterado (campo_alterado = 'minuta')
        """
        amostra = self._amostras[codigo]
        agora = datetime.now()
        novos_logs: list[LogAlteracao] = []
        status_geral_anterior = amostra.status_geral
        parecer_anterior = amostra.parecer

        for ensaio in amostra.ensaios:
            novo_st = edicoes_status.get(ensaio.codigo, ensaio.status)
            nova_obs = edicoes_obs.get(ensaio.codigo, ensaio.observacao).strip()
            obs_mudou = nova_obs != ensaio.observacao

            if novo_st != ensaio.status:
                novos_logs.append(
                    LogAlteracao(
                        id=str(uuid.uuid4()),
                        data_alteracao=agora,
                        usuario=usuario,
                        campo_alterado="conformidade",
                        ensaio_codigo=ensaio.codigo,
                        ensaio_nome=ensaio.nome,
                        valor_anterior=ensaio.status,
                        valor_novo=novo_st,
                        observacao=nova_obs or None,
                    )
                )
                ensaio.status = novo_st  # type: ignore[assignment]
            elif obs_mudou:
                novos_logs.append(
                    LogAlteracao(
                        id=str(uuid.uuid4()),
                        data_alteracao=agora,
                        usuario=usuario,
                        campo_alterado="conformidade",
                        ensaio_codigo=ensaio.codigo,
                        ensaio_nome=ensaio.nome,
                        valor_anterior=ensaio.status,
                        valor_novo=ensaio.status,
                        observacao=nova_obs or "(observação removida)",
                    )
                )

            ensaio.observacao = nova_obs
            sinal, sinal_tipo = definir_sinalizacao_ensaio(ensaio)
            ensaio.sinalizacao = sinal
            ensaio.sinalizacao_tipo = sinal_tipo  # type: ignore[arg-type]

        # Recalcula status geral derivado (Seção 5.1 / CT-16 / CT-17)
        novo_status_geral = calcular_status_geral(amostra.ensaios)
        if novo_status_geral != status_geral_anterior:
            amostra.status_geral = novo_status_geral  # type: ignore[assignment]
            novos_logs.append(
                LogAlteracao(
                    id=str(uuid.uuid4()),
                    data_alteracao=agora,
                    usuario=usuario,
                    campo_alterado="parecer_geral",
                    valor_anterior=status_geral_anterior,
                    valor_novo=novo_status_geral,
                )
            )

        # Minuta / Parecer editável (CT-18)
        parecer_limpo = novo_parecer.strip()
        if parecer_limpo != parecer_anterior.strip():
            amostra.parecer = parecer_limpo
            novos_logs.append(
                LogAlteracao(
                    id=str(uuid.uuid4()),
                    data_alteracao=agora,
                    usuario=usuario,
                    campo_alterado="minuta",
                    valor_anterior=parecer_anterior,
                    valor_novo=parecer_limpo,
                )
            )

        if novos_logs:
            amostra.logs = list(reversed(novos_logs)) + amostra.logs

        return copy.deepcopy(amostra), len(novos_logs)

    # --- Importação (B3 -> cria amostra avaliada e abre B4) ---
    def criar_amostra_importada(
        self,
        pre_leitura: ResultadoPreLeitura,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> Amostra:
        codigo = pre_leitura.codigo_amostra_principal
        if codigo in self._amostras:
            self._seq_codigo += 1
            codigo = f"{self._seq_codigo}/2026"

        normas = [construir_norma_aplicada(sigla, origem, cl) for sigla, cl in normas_selecionadas]

        # Reaproveita histórico mockado coerente do local ou gera série sintética plausível
        valores = pre_leitura.valores_brutos or {
            800: "40,0",
            106: "71,00",
            268: "<0,200",
            794: "7,91",
            119: "<0,3",
            784: "Ausente",
        }

        ensaios: list[EnsaioResultado] = []
        for cod_ensaio, bruto in valores.items():
            if cod_ensaio not in CATALOGO_ENSAIOS:
                continue
            # Verifica se esse ensaio tem VMP em ao menos uma norma escolhida
            tem_vmp = any((cod_ensaio, n.id) in PARAMETROS_VMP for n in normas)
            if not tem_vmp:
                continue
            hist = self._obter_historico_base_ensaio(cod_ensaio, bruto, codigo, pre_leitura.data_coleta)
            ensaios.append(_montar_ensaio(cod_ensaio, bruto, normas, hist))

        # Se nenhum ensaio da planilha casou com as normas escolhidas (ex.: planilha de efluente aplicada a potabilidade),
        # inclui os ensaios padrão daquelas normas com valores mockados realistas para a POC não abrir vazia.
        if not ensaios:
            cods_normas = []
            for (c_id, n_id) in PARAMETROS_VMP:
                if any(n.id == n_id for n in normas) and c_id not in cods_normas:
                    cods_normas.append(c_id)
            defaults = {800: "34,5", 106: "16,2", 268: "<0,200", 794: "7,40", 119: "<0,3", 784: "Ausente", 19: "2,4", 59: "180", 48: "2,1", 157: "<0,005", 877: "42,0", 259: "0,04"}
            for cod_ensaio in cods_normas[:6]:
                bruto = defaults.get(cod_ensaio, "1,0")
                hist = self._obter_historico_base_ensaio(cod_ensaio, bruto, codigo, pre_leitura.data_coleta)
                ensaios.append(_montar_ensaio(cod_ensaio, bruto, normas, hist))

        amostra = Amostra(
            codigo=codigo,
            data_coleta=pre_leitura.data_coleta,
            data_conclusao=pre_leitura.data_conclusao,
            cliente=cliente,
            proposta=proposta,
            local_coleta=local_coleta,
            origem=origem,
            normas=normas,
            ensaios=ensaios,
            logs=[],
        )
        amostra.status_geral = calcular_status_geral(amostra.ensaios)  # type: ignore[assignment]
        amostra.parecer = gerar_parecer_automatico(amostra)

        self._amostras[codigo] = amostra
        self._ordem.insert(0, codigo)
        return copy.deepcopy(amostra)

    def criar_lote_importado(
        self,
        lote: ResultadoPreLeituraLote,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> list[Amostra]:
        """Importa todas as amostras do arquivo UltraLIMS aplicando o contexto único (D3)."""
        criadas: list[Amostra] = []
        for pre in reversed(lote.amostras):
            am = self.criar_amostra_importada(
                pre_leitura=pre,
                cliente=cliente,
                proposta=proposta,
                local_coleta=local_coleta,
                origem=origem,
                normas_selecionadas=normas_selecionadas,
            )
            criadas.insert(0, am)
        return criadas

    # ------------------------------------------------------------------
    # Tela B5 — Análise por Local de Coleta (Gráfico + Tabela Dinâmica)
    # ------------------------------------------------------------------
    def listar_normas_do_local(self, cliente: str, local_coleta: str) -> list[str]:
        normas_encontradas: list[str] = []
        for a in self._amostras.values():
            if a.cliente == cliente and a.local_coleta == local_coleta:
                for n in a.normas:
                    rotulo = f"{n.sigla} — {n.classe}" if n.classe else n.sigla
                    if rotulo not in normas_encontradas:
                        normas_encontradas.append(rotulo)
        if normas_encontradas:
            return normas_encontradas
        # Fallback por tipo de local
        if "ETE" in local_coleta or "Efluente" in local_coleta:
            return ["CONAMA 430 — Sem Classe", "CONAMA 430 — Sanitário"]
        if "Tratamento" in local_coleta or "Reservatório" in local_coleta:
            return ["GM/MS 888", "SES-SC 1468"]
        return ["CONAMA 357 — Classe 1", "CONAMA 357 — Classe 2"]

    def _localizar_amostra_referencia(
        self, cliente: str, local_coleta: str, norma_label: str
    ) -> Amostra:
        # 1. Busca correspondência exata de cliente + local + norma
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente and a.local_coleta == local_coleta:
                for n in a.normas:
                    lbl = f"{n.sigla} — {n.classe}" if n.classe else n.sigla
                    if lbl == norma_label:
                        return a
        # 2. Correspondência por cliente + local
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente and a.local_coleta == local_coleta:
                return a
        # 3. Fallback para primeira amostra do cliente ou 65462/2026
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente:
                return a
        return self._amostras["65462/2026"]

    def obter_evolucao_mensal_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[MesConformidadeLocal]:
        """
        Retorna contagem mensal de amostras Favoráveis, Pendentes e Não favoráveis
        para o gráfico de barras empilhadas da B5.
        """
        # Séries ricas por ponto de coleta (6 a 12 meses de amostras acumuladas no local)
        series_base: dict[str, list[tuple[str, int, int, int]]] = {
            "Captação — Rio Itajaí-Açu": [
                ("Ago/25", 5, 0, 1),
                ("Set/25", 6, 0, 0),
                ("Out/25", 5, 1, 0),
                ("Nov/25", 4, 1, 1),
                ("Dez/25", 6, 0, 0),
                ("Jan/26", 5, 1, 0),
                ("Fev/26", 5, 1, 0),
                ("Mar/26", 6, 0, 0),
                ("Abr/26", 4, 1, 1),
                ("Mai/26", 5, 0, 1),
                ("Jun/26", 4, 2, 0),
                ("Jul/26", 4, 1, 1),
            ],
            "Saída — Efluente Sanitário (ETE 01)": [
                ("Ago/25", 4, 1, 1),
                ("Set/25", 5, 0, 1),
                ("Out/25", 5, 1, 0),
                ("Nov/25", 6, 0, 0),
                ("Dez/25", 4, 1, 1),
                ("Jan/26", 5, 0, 1),
                ("Fev/26", 4, 1, 1),
                ("Mar/26", 5, 1, 0),
                ("Abr/26", 4, 0, 2),
                ("Mai/26", 3, 1, 2),
                ("Jun/26", 4, 1, 1),
                ("Jul/26", 3, 1, 2),
            ],
            "Saída Efluente Industrial 02": [
                ("Ago/25", 3, 1, 1),
                ("Set/25", 4, 1, 0),
                ("Out/25", 3, 2, 0),
                ("Nov/25", 4, 0, 1),
                ("Dez/25", 4, 1, 0),
                ("Jan/26", 3, 1, 1),
                ("Fev/26", 4, 1, 0),
                ("Mar/26", 3, 1, 1),
                ("Abr/26", 3, 2, 1),
                ("Mai/26", 4, 1, 0),
                ("Jun/26", 2, 1, 2),
                ("Jul/26", 2, 1, 2),
            ],
            "Montante ETA Central": [
                ("Ago/25", 6, 0, 0),
                ("Set/25", 6, 0, 0),
                ("Out/25", 5, 1, 0),
                ("Nov/25", 6, 0, 0),
                ("Dez/25", 6, 0, 0),
                ("Jan/26", 6, 0, 0),
                ("Fev/26", 6, 0, 0),
                ("Mar/26", 6, 0, 0),
                ("Abr/26", 5, 1, 0),
                ("Mai/26", 6, 0, 0),
                ("Jun/26", 6, 0, 0),
                ("Jul/26", 6, 0, 0),
            ],
        }

        dados = series_base.get(
            local_coleta,
            [
                ("Fev/26", 4, 1, 0),
                ("Mar/26", 5, 0, 0),
                ("Abr/26", 4, 0, 1),
                ("Mai/26", 4, 1, 1),
                ("Jun/26", 5, 0, 0),
                ("Jul/26", 3, 1, 1),
            ],
        )

        recorte = dados[-periodo_meses:] if periodo_meses > 0 else dados
        meses_out = [
            MesConformidadeLocal(
                rotulo_mes=rot,
                favoraveis=fav,
                pendentes=pend,
                nao_favoraveis=nfav,
                is_atual=(idx == len(recorte) - 1),
            )
            for idx, (rot, fav, pend, nfav) in enumerate(recorte)
        ]

        # Incorpora amostras recém-importadas na sessão para este local no mês mais recente
        if meses_out:
            ultimo = meses_out[-1]
            for a in self._amostras.values():
                if a.codigo.startswith("684") and a.cliente == cliente and a.local_coleta == local_coleta:
                    if a.status_geral == GERAL_FAVORAVEL:
                        ultimo.favoraveis += 1
                    elif a.status_geral == GERAL_PENDENTE:
                        ultimo.pendentes += 1
                    else:
                        ultimo.nao_favoraveis += 1

        return meses_out

    def obter_tabela_dinamica_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[GrupoEnsaioLocal]:
        """
        Retorna os grupos por ensaio da Tabela Dinâmica da tela B5 com todas as coletas
        do período (ordenadas da mais recente para a mais antiga).
        """
        # Caso referência fiel ao print B5: SAMAE Blumenau -> Captação — Rio Itajaí-Açu -> CONAMA 357 — Classe 1
        if local_coleta == "Captação — Rio Itajaí-Açu" and "Classe 1" in norma_label:
            grupos_samae = [
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
            if periodo_meses == 3:
                for g in grupos_samae:
                    g.coletas = g.coletas[:3]
                    g.total_coletas = len(g.coletas)
            return grupos_samae

        # Construção dinâmica a partir da amostra referência para qualquer outro local/cliente/norma
        ref = self._localizar_amostra_referencia(cliente, local_coleta, norma_label)
        # Descobre qual norma_id corresponde ao filtro norma_label
        norma_alvo = None
        for n in ref.normas:
            lbl = f"{n.sigla} — {n.classe}" if n.classe else n.sigla
            if lbl == norma_label:
                norma_alvo = n
                break
        if norma_alvo is None and ref.normas:
            norma_alvo = ref.normas[0]

        grupos: list[GrupoEnsaioLocal] = []
        for e in ref.ensaios:
            pontos_rec = list(reversed(e.historico))
            if periodo_meses == 3:
                pontos_rec = pontos_rec[:3]

            av = e.avaliacoes.get(norma_alvo.id) if norma_alvo else None
            vmp_txt = av.vmp_texto if av else "—"
            vmp_pref = f"VMP {norma_alvo.classe or norma_alvo.sigla}" if norma_alvo else "VMP"
            param = PARAMETROS_VMP.get((e.codigo, norma_alvo.id)) if norma_alvo else None

            coletas_out: list[ColetaEnsaioLocal] = []
            nums: list[float] = []
            qtd_ok = 0
            qtd_nc = 0
            qtd_pend = 0
            qtd_desv = 0

            for idx_p, p in enumerate(pontos_rec):
                if p.valor_numerico is not None and not p.is_lq:
                    nums.append(p.valor_numerico)

                if param:
                    ok, motivo = avaliar_parametro(p.valor_bruto, e.tipo_avaliacao, e.unidade_trabalho, param)
                else:
                    ok, motivo = True, "AVALIADO"

                if ok is False:
                    qtd_nc += 1
                    b_txt, b_var = "NÃO CONFORME", "solid-red"
                elif ok is None:
                    qtd_pend += 1
                    if motivo == "UNIDADE_DIVERGENTE":
                        b_txt, b_var = "UNID. DIVERGENTE", "outline-gray"
                    else:
                        b_txt, b_var = "PENDENTE (<LQ)", "outline-gray"
                else:
                    qtd_ok += 1
                    if idx_p == 0 and e.estatistica and e.estatistica.alerta_desvio:
                        qtd_desv += 1
                        b_txt, b_var = "DESVIO > μ+0,20σ", "outline-amber"
                    else:
                        b_txt, b_var = "CONFORME", "outline-green"

                coletas_out.append(
                    ColetaEnsaioLocal(
                        codigo_amostra=p.codigo_amostra,
                        data_coleta=p.data_coleta,
                        valor_bruto=p.valor_bruto,
                        unidade=e.unidade_trabalho,
                        vmp_prefixo=vmp_pref,
                        vmp_texto=vmp_txt,
                        badge_texto=b_txt,
                        badge_variant=b_var,  # type: ignore[arg-type]
                    )
                )

            total = len(coletas_out)
            pct = f"{(qtd_ok / total * 100):.1f}%".replace(".", ",") if total else "—"
            media_str = (
                f"{formatar_numero_br(sum(nums) / len(nums), 2)} {e.unidade_trabalho}".strip()
                if nums
                else "Qualitativo"
            )
            notas = []
            if qtd_pend:
                notas.append(f"{qtd_pend} Pendente" + ("s" if qtd_pend > 1 else ""))
            if qtd_desv:
                notas.append(f"{qtd_desv} Desvio (> μ+0,20σ)")
            pend_desv_txt = " · ".join(notas) if notas else "0"

            grupos.append(
                GrupoEnsaioLocal(
                    codigo_ensaio=e.codigo,
                    nome_ensaio=e.nome,
                    unidade=e.unidade_trabalho,
                    total_coletas=total,
                    media_texto=media_str,
                    conformidade_pct=pct,
                    nao_conformes=qtd_nc,
                    pendentes_desvios_texto=pend_desv_txt,
                    coletas=coletas_out,
                )
            )
        return grupos

    def _materializar_amostra_historica(self, codigo: str) -> Optional[Amostra]:
        """Materializa uma amostra histórica clicada na tela B5 usando os pontos do histórico."""
        for a in self._amostras.values():
            valores_hist: dict[int, tuple[date, str]] = {}
            for e in a.ensaios:
                for p in e.historico:
                    if p.codigo_amostra == codigo:
                        valores_hist[e.codigo] = (p.data_coleta, p.valor_bruto)
            if valores_hist:
                dt_coleta = next(iter(valores_hist.values()))[0]
                ensaios_mat: list[EnsaioResultado] = []
                for e in a.ensaios:
                    bruto = valores_hist.get(e.codigo, (dt_coleta, e.valor_bruto))[1]
                    hist_clone = [copy.deepcopy(p) for p in e.historico if p.data_coleta <= dt_coleta]
                    for hp in hist_clone:
                        hp.is_atual = hp.codigo_amostra == codigo
                    ensaios_mat.append(_montar_ensaio(e.codigo, bruto, a.normas, hist_clone))
                nova = Amostra(
                    codigo=codigo,
                    data_coleta=dt_coleta,
                    data_conclusao=dt_coleta,
                    cliente=a.cliente,
                    proposta=a.proposta,
                    local_coleta=a.local_coleta,
                    origem=a.origem,
                    normas=copy.deepcopy(a.normas),
                    ensaios=ensaios_mat,
                    logs=[],
                )
                nova.status_geral = calcular_status_geral(nova.ensaios)  # type: ignore[assignment]
                nova.parecer = gerar_parecer_automatico(nova)
                self._amostras[codigo] = nova
                return nova
        return None

    def _obter_historico_base_ensaio(
        self,
        cod_ensaio: int,
        bruto_atual: str,
        codigo_atual: str,
        data_atual: date,
    ) -> list[PontoHistorico]:
        # Busca histórico existente do mesmo ensaio em alguma semente para manter consistência visual
        for a in self._amostras.values():
            for e in a.ensaios:
                if e.codigo == cod_ensaio and len(e.historico) >= 3:
                    anteriores = [copy.deepcopy(p) for p in e.historico if not p.is_atual][-5:]
                    _, q, v = interpretar_valor_bruto(bruto_atual)
                    if v is None and bruto_atual.strip().lower() == "ausente":
                        v = 0.0
                    anteriores.append(
                        PontoHistorico(
                            data_coleta=data_atual,
                            rotulo_mes=f"{data_atual.strftime('%b/%y')} Atual",
                            codigo_amostra=codigo_atual,
                            valor_bruto=bruto_atual,
                            valor_numerico=v,
                            qualificador=q,  # type: ignore[arg-type]
                            is_atual=True,
                        )
                    )
                    return anteriores
        return _hist([(f"{data_atual.strftime('%b/%y')} Atual", data_atual, codigo_atual, bruto_atual, True)])


# Instância singleton da POC
repo = MockRepository()
