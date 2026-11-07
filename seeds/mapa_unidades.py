"""Mapas de normalização do staging (planilhas_base) para o banco (DEV-3, DEV-4 e DEV-6)."""
from __future__ import annotations

import csv
import glob
from pathlib import Path

MAPA_LEGISLACAO: dict[str, str] = {
    "Portaria GM/MS Nº888 5/21": "Portaria GM/MS 888/2021",
    "Portaria GM/MS 888/2021": "Portaria GM/MS 888/2021",
    "Portaria SES nº1468/2022": "Portaria SES/SC 1468/2022",
    "Portaria SES/SC 1468/2022": "Portaria SES/SC 1468/2022",
}

MAPA_ORIGEM_AMOSTRA: dict[str, str] = {
    "Água Consumo Humano": "Água Consumo Humano",
    "Agua Tratada": "Água Tratada",
    "Água Tratada": "Água Tratada",
    "Água Superficial (Água doce)": "Água Superficial (Água doce)",
    "Água Subterrânea": "Água Subterrânea",
}

# bruto -> padronizado. None = grandeza adimensional (fk_unidade_medida = NULL).
MAPA_UNIDADES: dict[str, str | None] = {
    "µg/L": "µg/L",
    "ug/L": "µg/L",
    "ppb": "µg/L",             # Decisão definida: ppb unificado em µg/L
    "mg/L": "mg/L",
    "Bq/L": "Bq/L",
    "UFC/100mL": "UFC/100mL",
    "NMP/100 mL": "NMP/100mL",
    "NMP/100mL": "NMP/100mL",
    "NTU": "NTU",
    "Pt/Co": "Pt/Co",
    "Intensidade": "Intensidade",
    "células/mL": "células/mL",
    "Aus/Pres em 100mL": None,
    "": None,                  # Adimensionais: pH (793, 1190) e Razão de Nitrito e Nitrato (7865)
}

# Exceções por id_num quando o PDF omitiu a unidade mas o ensaio possui unidade física/sensorial
UNIDADE_POR_ENSAIO: dict[int, str] = {
    7138: "Intensidade",       # SUB - Gosto e Odor -> vinculado a Intensidade (igual ao 29 - Gosto e Odor)
}

UNIDADES_PADRONIZADAS: list[str] = sorted({v for v in MAPA_UNIDADES.values() if v is not None})


def normalizar_unidade(bruto: str | None, id_num: int | str | None = None) -> str | None:
    """Retorna a descrição padronizada da unidade, ou None quando adimensional."""
    if id_num is not None and int(id_num) in UNIDADE_POR_ENSAIO:
        return UNIDADE_POR_ENSAIO[int(id_num)]
    return MAPA_UNIDADES[(bruto or "").strip()]


def normalizar_legislacao(bruto: str) -> str:
    """Retorna o nome padronizado da legislação."""
    return MAPA_LEGISLACAO[bruto.strip()]


def normalizar_origem(bruto: str) -> str:
    """Retorna o nome padronizado da origem da amostra."""
    return MAPA_ORIGEM_AMOSTRA[bruto.strip()]


if __name__ == "__main__":
    pasta_base = Path(__file__).resolve().parent / "planilhas_base"
    arquivos = sorted(glob.glob(str(pasta_base / "*.csv")))
    brutas: set[str] = set()
    for arq in arquivos:
        with open(arq, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                col_un = r.get("unidade_medida") if "unidade_medida" in r else r.get("unidade", "")
                brutas.add(col_un or "")

    desconhecidas = sorted(u for u in brutas if u.strip() not in MAPA_UNIDADES)
    if desconhecidas:
        raise SystemExit(f"Unidades sem mapeamento: {desconhecidas}")

    usadas = sorted({normalizar_unidade(u) for u in brutas} - {None})
    print(f"{len(arquivos)} planilhas lidas | {len(brutas)} unidades brutas -> {len(usadas)} padronizadas:")
    for u in usadas:
        print(f"  - {u}")
