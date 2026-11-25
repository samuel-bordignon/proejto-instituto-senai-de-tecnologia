"""Motor de Conformidade Regulatória e Parecer Automático (RN-03, RN-04, RN-05, RN-07, Seção 5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    GERAL_PENDENTE,
    STATUS_CONFORME,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.models import Amostra, AvaliacaoNorma, EnsaioResultado, ParametroNorma


def normalizar_unidade(unidade: Optional[str]) -> str:
    """Normaliza sinônimos 1:1 de unidades sem converter escalas (RN-05), alinhado a seeds/mapa_unidades.py."""
    u = (unidade or "").strip()
    mapa = {
        "µg/L": "µg/L",
        "μg/L": "µg/L",
        "ug/L": "µg/L",
        "ppb": "µg/L",
        "mg/L": "mg/L",
        "mL/L": "mL/L",
        "°C": "°C",
        "ºC": "°C",
        "oC": "°C",
        "FT": "FT",
        "Bq/L": "Bq/L",
        "UFC/100mL": "UFC/100mL",
        "UFC/100 mL": "UFC/100mL",
        "NMP/100 mL": "NMP/100mL",
        "NMP/100mL": "NMP/100mL",
        "NTU": "NTU",
        "UNT": "NTU",
        "Pt/Co": "Pt/Co",
        "mg Pt/L": "Pt/Co",
        "uH": "Pt/Co",
        "Intensidade": "Intensidade",
        "células/mL": "células/mL",
        "Aus/Pres em 100mL": "",
        "": "",
    }
    return mapa.get(u, u)


def tem_sujeira_numerica(bruto: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Detecta sujeira real de formatação numérica no export UltraLIMS (RN-01 / CT-10).
    Retorna (True, motivo) apenas para espaços extras nas extremidades ou separadores de milhar
    (' 1.408,00', '>2.500.000.000'). Vírgula decimal PT-BR padrão ('7,91', '<0,060') NÃO gera aviso.
    """
    if bruto is None:
        return False, None
    texto = str(bruto)
    limpo = texto.strip()
    if not limpo:
        return False, None

    motivos: list[str] = []
    if texto != limpo:
        motivos.append("espaços extras")

    corpo = limpo[1:].strip() if limpo[0] in ("<", ">") else limpo
    token_num = corpo.split()[0] if corpo else ""

    if "," in token_num and "." in token_num:
        motivos.append("separador de milhar '.' com vírgula decimal")
    elif token_num.count(".") > 1:
        motivos.append("múltiplos separadores de milhar '.'")

    if not motivos:
        return False, None
    return True, " + ".join(motivos)


def interpretar_valor_bruto(bruto: Optional[str]) -> tuple[str, Optional[str], Optional[float]]:
    """
    Pipeline de parsing e limpeza de células UltraLIMS (Seção 5.1 / RN-02 / RN-03).
    Retorna (tipo, qualificador, valor_numerico):
      tipo ∈ {'ignorado', 'numerico', 'qualitativo'}
    """

    # Casos de ensaios ignorados
    if bruto is None:
        return "ignorado", None, None
    texto = str(bruto).strip()
    if not texto or set(texto) == {"_"}:
        return "ignorado", None, None
    if texto.lower() == "resultado na carta controle de svoc":
        return "ignorado", None, None

    q: Optional[str] = texto[0] if texto[0] in ("<", ">") else None
    corpo = texto[1:].strip() if q else texto

    # Remove sufixos eventuais de unidade caso venham colados
    token_num = corpo.split()[0] if corpo else ""
    if "," in token_num:
        token_num = token_num.replace(".", "").replace(",", ".")
    elif token_num.count(".") > 1:
        token_num = token_num.replace(".", "")

    try:
        return "numerico", q, float(token_num)
    except ValueError:
        return "qualitativo", None, None


def formatar_numero_br(n: Optional[float], casas_max: int = 3) -> str:
    if n is None:
        return "—"
    if abs(n) >= 100 and n == int(n):
        return f"{int(n):,}".replace(",", ".")
    fmt = f"{n:.{casas_max}f}".rstrip("0")
    if fmt.endswith("."):
        fmt += "0"
    return fmt.replace(".", ",")


def formatar_vmp_texto(p: ParametroNorma) -> str:
    un = f" {p.unidade}" if p.unidade else ""
    if p.operador == "MENOR_IGUAL":
        return f"≤ {formatar_numero_br(p.valor_max)}{un}"
    if p.operador == "MENOR_ESTRITO":
        return f"< {formatar_numero_br(p.valor_max)}{un}"
    if p.operador == "MAIOR_IGUAL":
        return f"≥ {formatar_numero_br(p.valor_min)}{un}"
    if p.operador == "FAIXA":
        return f"{formatar_numero_br(p.valor_min)} a {formatar_numero_br(p.valor_max)}{un}"
    if p.operador == "AUSENCIA":
        return p.valor_esperado or "Ausente"
    return "Avaliação técnica"


def avaliar_parametro(
    valor_bruto: str,
    tipo_avaliacao: str,
    unidade_ensaio: str,
    parametro: ParametroNorma,
) -> tuple[Optional[bool], str]:
    """
    Aplica RN-03, RN-04 e RN-05.
    Retorna (conformidade: True|False|None, motivo).
    """
    if tipo_avaliacao == "MANUAL_TECNICA" or parametro.operador == "MANUAL":
        return None, "MANUAL_TECNICA"

    if parametro.operador == "AUSENCIA":
        esperado = (parametro.valor_esperado or "Ausente").strip().lower()
        ok = (valor_bruto or "").strip().lower() == esperado
        return ok, "AVALIADO"

    u_ensaio = normalizar_unidade(unidade_ensaio)
    u_param = normalizar_unidade(parametro.unidade)
    if u_ensaio != u_param:
        return None, "UNIDADE_DIVERGENTE"

    _, q, v = interpretar_valor_bruto(valor_bruto)

    # RN-03: 'Ausente' em parâmetro numérico equivale a 0.0
    if v is None and (valor_bruto or "").strip().lower() == "ausente":
        v, q = 0.0, None

    if v is None:
        return None, "NAO_NUMERICO"

    vmin, vmax = parametro.valor_min, parametro.valor_max

    if parametro.operador == "MENOR_IGUAL" and vmax is not None:
        if q == "<":
            return (True if v <= vmax else None), "AVALIADO"
        if q == ">":
            return (False if v >= vmax else None), "AVALIADO"
        return (v <= vmax), "AVALIADO"

    if parametro.operador == "MENOR_ESTRITO" and vmax is not None:
        if q == "<":
            return (True if v <= vmax else None), "AVALIADO"
        if q == ">":
            return (False if v >= vmax else None), "AVALIADO"
        return (v < vmax), "AVALIADO"

    if parametro.operador == "MAIOR_IGUAL" and vmin is not None:
        if q == ">":
            return (True if v >= vmin else None), "AVALIADO"
        if q == "<":
            return (False if v <= vmin else None), "AVALIADO"
        return (v >= vmin), "AVALIADO"

    if parametro.operador == "FAIXA" and vmin is not None and vmax is not None:
        if q == "<":
            return (False if v <= vmin else None), "AVALIADO"
        if q == ">":
            return (False if v >= vmax else None), "AVALIADO"
        return (vmin <= v <= vmax), "AVALIADO"

    return None, "OPERADOR_DESCONHECIDO"


def consolidar_status_ensaio(avaliacoes: list[AvaliacaoNorma]) -> str:
    """Consolida o status de um ensaio avaliado contra 1 a 3 normas."""
    if not avaliacoes:
        return STATUS_CONFORME
    vereditos = [a.conformidade for a in avaliacoes]
    if any(v is False for v in vereditos):
        return STATUS_NAO_CONFORME
    if any(v is None for v in vereditos):
        return STATUS_PENDENTE
    return STATUS_CONFORME


def calcular_status_geral(ensaios: list[EnsaioResultado]) -> str:
    """
    Seção 5.1 — Status geral derivado exclusivamente dos status dos ensaios:
      1. Qualquer ensaio Não conforme -> Não favorável
      2. Nenhum Não conforme e >= 1 Pendente -> Pendente
      3. Todos Conforme -> Favorável
    """
    if any(e.status == STATUS_NAO_CONFORME for e in ensaios):
        return GERAL_NAO_FAVORAVEL
    if any(e.status == STATUS_PENDENTE for e in ensaios):
        return GERAL_PENDENTE
    return GERAL_FAVORAVEL


def gerar_parecer_automatico(amostra: Amostra) -> str:
    """
    RN-07 — Geração determinística do texto do parecer no padrão único do IST.
    Usa os status atuais dos ensaios (respeitando alterações manuais).
    """
    excecoes: list[str] = []
    for ensaio in amostra.ensaios:
        if ensaio.status != STATUS_NAO_CONFORME:
            continue

        normas_violadas = [
            av.norma_nome_parecer
            for av in ensaio.avaliacoes.values()
            if av.conformidade is False
        ]
        # Caso o conferente tenha marcado manualmente como Não conforme sem violação automática
        if not normas_violadas:
            normas_violadas = [n.nome_parecer for n in amostra.normas]

        # Se todas as classes de uma mesma norma violaram, simplifica o nome da norma
        normas_unicas: list[str] = []
        for nm in normas_violadas:
            if nm not in normas_unicas:
                normas_unicas.append(nm)

        if len(normas_unicas) == 1:
            alvo = normas_unicas[0]
        else:
            # Verifica se todas pertencem à mesma legislação base (ex: CONAMA 430 Sanitário + Sem Classe)
            bases = {n.nome_completo for n in amostra.normas if n.nome_parecer in normas_unicas}
            if len(bases) == 1:
                alvo = next(iter(bases))
            else:
                alvo = ", ".join(normas_unicas[:-1]) + f" e {normas_unicas[-1]}"

        excecoes.append(f"o ensaio de {ensaio.nome} para a {alvo}")

    if not excecoes:
        pendentes = [e.nome for e in amostra.ensaios if e.status == STATUS_PENDENTE]
        if pendentes:
            lista = ", ".join(pendentes)
            return (
                "Análise em conferência técnica. Os resultados avaliados atendem às especificações "
                f"aplicadas, restando pendência de verificação em: {lista}."
            )
        return "Os resultados de ensaio atendem às especificações aplicadas neste documento."

    if len(excecoes) == 1:
        corpo = excecoes[0]
    else:
        corpo = ", ".join(excecoes[:-1]) + f" e {excecoes[-1]}"

    return f"Os ensaios atendem às especificações aplicadas neste documento, exceto {corpo}."


def definir_sinalizacao_ensaio(ensaio: EnsaioResultado) -> tuple[Optional[str], Optional[str]]:
    """Define a principal pill de sinalização complementar exibida na tabela B4."""
    for av in ensaio.avaliacoes.values():
        if av.motivo == "UNIDADE_DIVERGENTE":
            return "UNID. DIVERGENTE", "gray"

    for av in ensaio.avaliacoes.values():
        if av.operador == "MENOR_ESTRITO" and av.conformidade is False:
            return "LIMITE ESTRITO", "red"

    if ensaio.estatistica and ensaio.estatistica.alerta_desvio:
        return "DESVIO > μ+0,20σ", "amber"

    if ensaio.qualificador == "<" and ensaio.status == STATUS_PENDENTE:
        return "PENDENTE (<LQ)", "amber"

    if ensaio.qualificador == ">":
        return "LIMITE SUPERIOR (>LS)", "amber"

    return None, None


@dataclass(frozen=True)
class ResumoDiagnosticoAmostra:
    """Resumo agregado de domínio para exibição de diagnósticos no Painel (B2)."""

    qtd_nao_conformes: int
    qtd_pendentes: int
    favoravel: bool
    tem_unidade_divergente: bool
    tem_desvio_historico: bool


def resumir_diagnostico_amostra(amostra: Amostra) -> ResumoDiagnosticoAmostra:
    """Calcula os contadores e sinalizações agregadas de conformidade de uma amostra."""
    qtd_nc = sum(1 for e in amostra.ensaios if e.status == STATUS_NAO_CONFORME)
    qtd_pend = sum(1 for e in amostra.ensaios if e.status == STATUS_PENDENTE)
    tem_desvio = any(e.estatistica and e.estatistica.alerta_desvio for e in amostra.ensaios)
    tem_unid_div = any(
        any(av.motivo == "UNIDADE_DIVERGENTE" for av in e.avaliacoes.values())
        for e in amostra.ensaios
    )
    return ResumoDiagnosticoAmostra(
        qtd_nao_conformes=qtd_nc,
        qtd_pendentes=qtd_pend,
        favoravel=(qtd_nc == 0 and qtd_pend == 0),
        tem_unidade_divergente=tem_unid_div,
        tem_desvio_historico=tem_desvio,
    )
