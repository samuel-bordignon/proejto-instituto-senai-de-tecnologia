"""
Motor de avaliação e conformidade analítica contra VMPs legislativos.
"""

from data.mock_data import ENSAIOS, PARAMETROS, STATUS_OPCOES


def interpretar(bruto: str):
    b = (bruto or "").strip()
    if not b or set(b) == {"_"}:
        return "nao_analisado", None, None
    q = b[0] if b[0] in "<>" else None
    corpo = b[1:].strip() if q else b
    if "," in corpo:
        corpo = corpo.replace(".", "").replace(",", ".")
    elif corpo.count(".") > 1:
        corpo = corpo.replace(".", "")
    try:
        return "numerico", q, float(corpo)
    except ValueError:
        return "qualitativo", None, None


def avaliar(bruto: str, p: dict, tipo_avaliacao: str):
    if tipo_avaliacao == "MANUAL_TECNICA" or p["op"] == "MANUAL":
        return None
    if p["op"] == "AUSENCIA":
        return bruto.strip().lower() == p["esperado"].lower()

    _, q, v = interpretar(bruto)
    if v is None:
        return None
    vmin, vmax = p.get("vmin"), p.get("vmax")

    if p["op"] == "MENOR_IGUAL":
        if q == "<":
            return True if v <= vmax else None
        if q == ">":
            return False if v >= vmax else None
        return v <= vmax

    if p["op"] == "MAIOR_IGUAL":
        if q == ">":
            return True if v >= vmin else None
        if q == "<":
            return False if v <= vmin else None
        return v >= vmin

    if p["op"] == "FAIXA":
        if q == "<":
            return False if v <= vmin else None
        if q == ">":
            return False if v >= vmax else None
        return vmin <= v <= vmax

    return None


def formatar_numero(n: float) -> str:
    return f"{n:.3f}".rstrip("0").rstrip(".").replace(".", ",")


def texto_vmp(p: dict) -> str:
    if p["op"] == "MENOR_IGUAL":
        return f"≤ {formatar_numero(p['vmax'])}"
    if p["op"] == "MAIOR_IGUAL":
        return f"≥ {formatar_numero(p['vmin'])}"
    if p["op"] == "FAIXA":
        return f"{formatar_numero(p['vmin'])} a {formatar_numero(p['vmax'])}"
    if p["op"] == "AUSENCIA":
        return p["esperado"]
    return p.get("texto") or "Avaliação técnica"


def consolidar(vereditos: list) -> str:
    if any(v is False for v in vereditos):
        return "Não conforme"
    if any(v is None for v in vereditos):
        return "Pendente"
    return "Conforme"


def linhas_resultado(amostra: dict, legislacoes: list) -> list:
    linhas = []
    for codigo, bruto in amostra.get("valores", {}).items():
        if interpretar(bruto)[0] == "nao_analisado":
            continue
        ensaio = ENSAIOS.get(codigo)
        if not ensaio:
            continue
        por_leg = {}
        for leg in legislacoes:
            p = PARAMETROS.get((codigo, leg))
            if p:
                por_leg[leg] = (texto_vmp(p), avaliar(bruto, p, ensaio["tipo"]))
        if not por_leg:
            continue
        auto = consolidar([v for _, v in por_leg.values()])
        status, obs = amostra.get("revisao", {}).get(codigo, (auto, ""))
        linhas.append({
            "codigo": codigo,
            "ensaio": ensaio["nome"],
            "resultado": f"{bruto} {ensaio['unidade']}".strip(),
            "valor_bruto": bruto,
            "unidade": ensaio["unidade"],
            "por_leg": por_leg,
            "status": status,
            "observacao": obs,
        })
    return linhas


def resumo(linhas: list) -> dict:
    return {s: sum(1 for l in linhas if l["status"] == s) for s in STATUS_OPCOES}
