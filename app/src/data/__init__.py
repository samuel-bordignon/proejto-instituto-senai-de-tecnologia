"""
Pacote de dados e regras do LaudoTech.
"""
from data.mock_data import (
    CLIENTES,
    ENSAIOS,
    LEGISLACOES,
    PARAMETROS,
    SEMENTES,
    STATUS_OPCOES,
    V_ATENCAO,
    V_CRITICO,
    V_REGULAR,
    V_SUPERFICIAL,
    nova_amostra,
)
from data.motor_conformidade import (
    avaliar,
    consolidar,
    interpretar,
    linhas_resultado,
    resumo,
    texto_vmp,
)
