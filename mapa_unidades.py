"""Mapa de normalização de unidades de medida (staging -> unidade_medida).

Espelha o mapa do seed `seed_unidade_medida.sql`. Uso na carga de
parametros (DEV-6):

    from mapa_unidades import normalizar_unidade
    descricao = normalizar_unidade(linha["unidade_medida"])  # str ou None
    # None => parametros.fk_unidade_medida = NULL (sem unidade cadastrada)

Conferência contra o CSV de staging:

    python3 mapa_unidades.py staging_vmps_validos.csv
"""
import csv
import sys

# bruto -> padronizado. None = não cadastrar (fk_unidade_medida = NULL).
MAPA_UNIDADES = {
    "µg/L": "µg/L",
    "ug/L": "µg/L",
    "ppb": "µg/L",            # 1 ppb = 1 µg/L; pendente de alinhamento do time
    "mg/L": "mg/L",
    "Bq/L": "Bq/L",
    "UFC/100mL": "UFC/100mL",
    "NMP/100 mL": "NMP/100mL",
    "NMP/100mL": "NMP/100mL",
    "NTU": "NTU",
    "Pt/Co": "Pt/Co",
    "Intensidade": "Intensidade",
    "células/mL": "células/mL",
    "Aus/Pres em 100mL": None,   # nao e unidade cadastravel
    "": None,                    # adimensional (pH, razao de nitrito/nitrato, etc.)
}

# Unidades a cadastrar em unidade_medida (padronizadas, sem duplicatas).
UNIDADES_PADRONIZADAS = sorted({v for v in MAPA_UNIDADES.values() if v is not None})


def normalizar_unidade(bruto):
    """Retorna a descricao padronizada, ou None se nao deve ser cadastrada.

    Levanta KeyError para unidade desconhecida (evita carga silenciosa errada).
    """
    return MAPA_UNIDADES[(bruto or "").strip()]


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "staging_vmps_validos.csv"
    with open(caminho, newline="", encoding="utf-8") as f:
        brutas = {r["unidade_medida"] for r in csv.DictReader(f)}
    desconhecidas = sorted(u for u in brutas if u.strip() not in MAPA_UNIDADES)
    if desconhecidas:
        raise SystemExit(f"Unidades sem mapeamento: {desconhecidas}")
    usadas = sorted({normalizar_unidade(u) for u in brutas} - {None})
    print(f"{len(brutas)} unidades distintas no CSV -> {len(usadas)} cadastradas:")
    for u in usadas:
        print("  ", u)
