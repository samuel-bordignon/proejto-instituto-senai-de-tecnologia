"""
Dados cadastrais, catálogo analítico e bases legais mockadas para o LaudoTech.
"""

from datetime import date

LEGISLACOES = {
    "GM888": {
        "nome": "Portaria GM/MS nº 888/2021",
        "sigla": "GM/MS 888",
        "tipo": "Portaria Federal",
        "escopo": "Padrão de Potabilidade de Água para Consumo Humano",
    },
    "SES1468": {
        "nome": "Portaria SES-SC nº 1.468/2022",
        "sigla": "SES-SC 1468",
        "tipo": "Portaria Estadual",
        "escopo": "Vigilância e Qualidade da Água para Consumo Humano em SC",
    },
    "CONAMA357": {
        "nome": "Resolução CONAMA nº 357/2005",
        "sigla": "CONAMA 357 (C2)",
        "tipo": "Resolução Federal",
        "escopo": "Classificação e Padrões para Corpos de Água Superficiais — Classe 2",
    },
}

ENSAIOS = {
    48: {"nome": "Turbidez", "unidade": "uT", "tipo": "AUTOMATICA"},
    102: {"nome": "pH", "unidade": "—", "tipo": "AUTOMATICA"},
    310: {"nome": "Cloro residual livre", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    877: {"nome": "Glifosato + AMPA", "unidade": "µg/L", "tipo": "AUTOMATICA"},
    12: {"nome": "Coliformes totais", "unidade": "P/A", "tipo": "AUTOMATICA"},
    13: {"nome": "Escherichia coli", "unidade": "P/A", "tipo": "AUTOMATICA"},
    99: {"nome": "Gosto e odor", "unidade": "Intensidade", "tipo": "MANUAL_TECNICA"},
    512: {"nome": "Fluoreto", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    205: {"nome": "Chumbo", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    206: {"nome": "Alumínio", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    52: {"nome": "Nitrato (como N)", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    139: {"nome": "Ferro total", "unidade": "mg/L", "tipo": "AUTOMATICA"},
    41: {"nome": "Oxigênio dissolvido", "unidade": "mg/L", "tipo": "AUTOMATICA"},
}


def _param(op, vmin=None, vmax=None, esperado=None, texto=None):
    return {"op": op, "vmin": vmin, "vmax": vmax, "esperado": esperado, "texto": texto}


PARAMETROS = {
    (48, "GM888"): _param("MENOR_IGUAL", vmax=5.0),
    (48, "SES1468"): _param("MENOR_IGUAL", vmax=5.0),
    (48, "CONAMA357"): _param("MENOR_IGUAL", vmax=100.0),
    (102, "GM888"): _param("FAIXA", 6.0, 9.5),
    (102, "SES1468"): _param("FAIXA", 6.0, 9.5),
    (102, "CONAMA357"): _param("FAIXA", 6.0, 9.0),
    (310, "GM888"): _param("FAIXA", 0.2, 5.0),
    (310, "SES1468"): _param("FAIXA", 0.2, 2.0),
    (877, "GM888"): _param("MENOR_IGUAL", vmax=500.0),
    (877, "SES1468"): _param("MENOR_IGUAL", vmax=30.0),
    (877, "CONAMA357"): _param("MENOR_IGUAL", vmax=65.0),
    (12, "GM888"): _param("AUSENCIA", esperado="Ausente"),
    (12, "SES1468"): _param("AUSENCIA", esperado="Ausente"),
    (13, "GM888"): _param("AUSENCIA", esperado="Ausente"),
    (13, "SES1468"): _param("AUSENCIA", esperado="Ausente"),
    (99, "GM888"): _param("MANUAL", texto="Intensidade ≤ 6"),
    (99, "SES1468"): _param("MANUAL", texto="Não objetável"),
    (512, "GM888"): _param("MENOR_IGUAL", vmax=1.5),
    (512, "SES1468"): _param("MENOR_IGUAL", vmax=1.5),
    (512, "CONAMA357"): _param("MENOR_IGUAL", vmax=1.4),
    (205, "GM888"): _param("MENOR_IGUAL", vmax=0.01),
    (205, "SES1468"): _param("MENOR_IGUAL", vmax=0.01),
    (205, "CONAMA357"): _param("MENOR_IGUAL", vmax=0.01),
    (206, "GM888"): _param("MENOR_IGUAL", vmax=0.2),
    (206, "SES1468"): _param("MENOR_IGUAL", vmax=0.2),
    (206, "CONAMA357"): _param("MENOR_IGUAL", vmax=0.1),
    (52, "GM888"): _param("MENOR_IGUAL", vmax=10.0),
    (52, "SES1468"): _param("MENOR_IGUAL", vmax=10.0),
    (52, "CONAMA357"): _param("MENOR_IGUAL", vmax=10.0),
    (139, "GM888"): _param("MENOR_IGUAL", vmax=0.3),
    (139, "SES1468"): _param("MENOR_IGUAL", vmax=0.3),
    (139, "CONAMA357"): _param("MENOR_IGUAL", vmax=0.3),
    (41, "CONAMA357"): _param("MAIOR_IGUAL", vmin=5.0),
}

CLIENTES = {
    "Cervejaria Vale do Itajaí Ltda": {
        "PROP-2026/088": {
            "descricao": "Monitoramento de potabilidade",
            "legislacoes": ["GM888", "SES1468"],
            "locais": [
                "Ponto 02 — Saída do tratamento",
                "Ponto 01 — Reservatório principal",
                "Ponto 03 — Torneira do envase",
            ],
        },
        "PROP-2026/115": {
            "descricao": "Vigilância sanitária estadual",
            "legislacoes": ["SES1468"],
            "locais": ["Poço artesiano 01"],
        },
    },
    "Águas de Blumenau S/A": {
        "PROP-2026/041": {
            "descricao": "Controle operacional",
            "legislacoes": ["GM888"],
            "locais": ["ETA Central — Filtro 03", "Rede de distribuição — Bairro Velha"],
        },
        "PROP-2026/052": {
            "descricao": "Captação de água bruta",
            "legislacoes": ["CONAMA357"],
            "locais": ["Captação — Rio Itajaí-Açu"],
        },
    },
}

V_REGULAR = {
    48: "0,62", 102: "7,1", 310: "1,10", 877: "<0,060", 12: "Ausente", 13: "Ausente",
    99: "Não objetável", 512: "0,71", 205: "<0,005", 206: "0,08", 52: "1,92", 139: "<0,10"
}
V_ATENCAO = {
    48: "1,40", 102: "6,8", 310: "2,40", 877: "42,0", 12: "Ausente", 13: "Ausente",
    99: "Não objetável", 512: "0,95", 205: "<0,020", 206: "0,15", 52: "8,70", 139: "0,21"
}
V_CRITICO = {
    48: "5,80", 102: "5,60", 310: "0,15", 877: "<0,060", 12: "Presente", 13: "Ausente",
    99: "Levemente terroso", 512: "________", 205: "<0,005", 206: ">0,20", 52: "4,61", 139: "0,34"
}
V_SUPERFICIAL = {
    48: "38,0", 102: "6,9", 877: "<0,060", 512: "0,30", 205: "<0,005", 206: "0,14",
    52: "1,10", 139: "0,25", 41: "4,6"
}

ODOR_OK = {99: ("Conforme", "Sem odor perceptível na conferência")}

SEMENTES = [
    ("Cervejaria Vale do Itajaí Ltda", "PROP-2026/088", "Ponto 02 — Saída do tratamento",
     "4731/2026", date(2026, 8, 4), V_REGULAR, ODOR_OK, True,
     "Amostra analisada em conformidade integral com os parâmetros de potabilidade das Portarias GM/MS 888 e SES-SC 1468."),
    ("Cervejaria Vale do Itajaí Ltda", "PROP-2026/088", "Ponto 02 — Saída do tratamento",
     "4766/2026", date(2026, 9, 1), V_ATENCAO, {}, False,
     "Amostra apresentou elevação de Glifosato+AMPA (42 µg/L), ultrapassando o VMP de 30 µg/L estipulado pela Portaria SES-SC 1468. Necessária apuração operacional."),
    ("Cervejaria Vale do Itajaí Ltda", "PROP-2026/088", "Ponto 02 — Saída do tratamento",
     "4799/2026", date(2026, 9, 15), V_CRITICO, {}, False,
     "Constatadas múltiplas não-conformidades críticas: Turbidez elevada (5,8 uT), pH ácido (5,60), Cloro residual livre deficiente (0,15 mg/L), presença de Coliformes Totais e Alumínio excedente (>0,20 mg/L). Recomendado descarte e nova desinfecção da rede."),
    ("Cervejaria Vale do Itajaí Ltda", "PROP-2026/088", "Ponto 01 — Reservatório principal",
     "4767/2026", date(2026, 9, 1), V_REGULAR, {}, False,
     "Monitoramento de rotina do reservatório principal. Resultados preliminares compatíveis com a norma vigente."),
    ("Cervejaria Vale do Itajaí Ltda", "PROP-2026/115", "Poço artesiano 01",
     "4780/2026", date(2026, 9, 8), V_ATENCAO, {}, False,
     "Monitoramento estadual de captação subterrânea."),
    ("Águas de Blumenau S/A", "PROP-2026/041", "ETA Central — Filtro 03",
     "4702/2026", date(2026, 7, 21), V_REGULAR, ODOR_OK, True,
     "Filtro rápido 03 operando dentro da faixa de turbidez e desinfecção recomendada."),
    ("Águas de Blumenau S/A", "PROP-2026/041", "ETA Central — Filtro 03",
     "4790/2026", date(2026, 9, 10), V_CRITICO, {}, False,
     "Amostra com turbidez e alumínio residual excedentes. Filtro direcionado para retrolavagem emergencial."),
    ("Águas de Blumenau S/A", "PROP-2026/041", "Rede de distribuição — Bairro Velha",
     "4791/2026", date(2026, 9, 10), V_ATENCAO, {}, False,
     "Ponto de ponta de rede com cloro residual no limite inferior."),
    ("Águas de Blumenau S/A", "PROP-2026/052", "Captação — Rio Itajaí-Açu",
     "4795/2026", date(2026, 9, 12), V_SUPERFICIAL, {}, False,
     "Água superficial bruta monitorada conforme CONAMA 357 Classe 2."),
]

STATUS_OPCOES = ["Conforme", "Não conforme", "Pendente"]


def nova_amostra(cliente, proposta, local, codigo, coleta, valores, revisao=None, revisada=False, minuta=""):
    return {
        "cliente": cliente,
        "proposta": proposta,
        "local": local,
        "codigo": codigo,
        "coleta": coleta,
        "valores": dict(valores),
        "revisao": dict(revisao or {}),
        "revisada": revisada,
        "minuta": minuta,
    }
