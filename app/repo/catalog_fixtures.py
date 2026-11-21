"""Dados mestres mockados da POC (usuários, catálogo de ensaios, clientes, origens, normas e VMPs)."""

from __future__ import annotations

from typing import Optional

from app.core.models import NormaAplicada, ParametroNorma, Usuario

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
    (268, "CONAMA 430|Sem Classe"): _p("CONAMA 430|Sem Classe", "CONAMA 430", "Resolução CONAMA 430/2011", "Sem Classe", "MENOR_IGUAL", vmax=0.01, unidade="mg/L"),
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
