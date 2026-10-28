import sys
from pathlib import Path

# Garante que a raiz do projeto e app/src estejam no sys.path
PASTA_SRC = Path(__file__).resolve().parent
RAIZ_PROJETO = PASTA_SRC.parent.parent
for _caminho in (str(RAIZ_PROJETO), str(PASTA_SRC)):
    if _caminho not in sys.path:
        sys.path.insert(0, _caminho)

import streamlit as st
from data.mock_data import CLIENTES, SEMENTES, nova_amostra
from app.src.components.sidebar import renderizar_sidebar
from app.src.components.tela_amostras import renderizar_tela_amostras
from app.src.components.ensaios.tela_ensaios import renderizar_tela_ensaios
from app.src.components.dialog_upload import abrir_dialogo_upload

# -----------------------------------------------------------------------------
# Configuração Global da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LaudoTech — IST Ambiental",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização complementar limpa (tipografia técnica e espaçamento calm)
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.8rem; padding-bottom: 2.5rem; }
    .stApp, .stMarkdown, [data-testid="stDataFrame"], .stTabs { font-variant-numeric: tabular-nums; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Inicialização do Estado da Sessão
# -----------------------------------------------------------------------------
if "amostras" not in st.session_state:
    st.session_state.amostras = {s[3]: nova_amostra(*s[:8], minuta=s[8] if len(s) > 8 else "") for s in SEMENTES}
    st.session_state.tela = "amostras"
    st.session_state.lote = []
    st.session_state.arquivo_origem = None
    st.session_state.proximo_codigo = 4812
    st.session_state.abrir_dialogo = False

# Contexto padrão
if "ctx_cliente" not in st.session_state:
    st.session_state.ctx_cliente = list(CLIENTES.keys())[0]
if "ctx_proposta" not in st.session_state:
    st.session_state.ctx_proposta = list(CLIENTES[st.session_state.ctx_cliente].keys())[0]
if "ctx_local" not in st.session_state:
    st.session_state.ctx_local = CLIENTES[st.session_state.ctx_cliente][st.session_state.ctx_proposta]["locais"][0]


# -----------------------------------------------------------------------------
# Callbacks de Controle de Estado
# -----------------------------------------------------------------------------
def ao_trocar_cliente():
    novo_cli = st.session_state.sb_cliente
    st.session_state.ctx_cliente = novo_cli
    novas_props = list(CLIENTES[novo_cli].keys())
    st.session_state.ctx_proposta = novas_props[0]
    st.session_state.ctx_local = CLIENTES[novo_cli][novas_props[0]]["locais"][0]
    st.session_state.lote = []


def ao_trocar_proposta():
    nova_prop = st.session_state.sb_proposta
    st.session_state.ctx_proposta = nova_prop
    novos_locais = CLIENTES[st.session_state.ctx_cliente][nova_prop]["locais"]
    st.session_state.ctx_local = novos_locais[0]
    st.session_state.lote = []


def ao_trocar_local():
    st.session_state.ctx_local = st.session_state.sb_local
    st.session_state.lote = []


def navegar_para(tela_destino: str):
    st.session_state.tela = tela_destino


def abrir_dialogo():
    st.session_state.abrir_dialogo = True


def ao_processar_lote(novo_lote: list, nome_arquivo: str, prox_cod: int):
    st.session_state.proximo_codigo = prox_cod
    for a in novo_lote:
        st.session_state.amostras[a["codigo"]] = a
    st.session_state.lote = novo_lote
    st.session_state.arquivo_origem = nome_arquivo
    st.session_state.tela = "ensaios"
    st.session_state.abrir_dialogo = False


def ao_abrir_ensaios(amostra: dict):
    st.session_state.lote = [amostra]
    st.session_state.arquivo_origem = None
    st.session_state.tela = "ensaios"


def ao_salvar_ensaios(lote_atualizado: list):
    for a in lote_atualizado:
        st.session_state.amostras[a["codigo"]] = a
    st.session_state.lote = lote_atualizado


# -----------------------------------------------------------------------------
# Renderização da Barra Lateral
# -----------------------------------------------------------------------------
renderizar_sidebar(
    cliente_atual=st.session_state.ctx_cliente,
    proposta_atual=st.session_state.ctx_proposta,
    local_atual=st.session_state.ctx_local,
    tela_atual=st.session_state.tela,
    on_cliente_change=ao_trocar_cliente,
    on_proposta_change=ao_trocar_proposta,
    on_local_change=ao_trocar_local,
    on_navegar=navegar_para,
)

# Metadados do contexto ativo
cliente_info = CLIENTES[st.session_state.ctx_cliente]
proposta_info = cliente_info[st.session_state.ctx_proposta]
legislacoes_atuais = proposta_info["legislacoes"]
local_atual = st.session_state.ctx_local

# Filtra amostras cadastradas para o ponto de coleta selecionado
amostras_do_local = sorted(
    [
        amostra for amostra in st.session_state.amostras.values()
        if (amostra["cliente"], amostra["proposta"], amostra["local"]) == (st.session_state.ctx_cliente, st.session_state.ctx_proposta, local_atual)
    ],
    key=lambda x: str(x.get("coleta", "")),
    reverse=True,
)
# -----------------------------------------------------------------------------
# Roteamento Principal
# -----------------------------------------------------------------------------
if st.session_state.tela == "amostras":
    renderizar_tela_amostras(
        cliente=st.session_state.ctx_cliente,
        proposta=st.session_state.ctx_proposta,
        local=local_atual,
        legislacoes=legislacoes_atuais,
        amostras=amostras_do_local,
        on_nova_amostra_callback=abrir_dialogo,
        on_abrir_ensaios_callback=ao_abrir_ensaios,
    )

elif st.session_state.tela == "ensaios":
    print(amostras_do_local)
    # Se o lote estiver vazio, carrega até 3 amostras do local para montar as abas
    if not st.session_state.lote and amostras_do_local:
        st.session_state.lote = amostras_do_local

    renderizar_tela_ensaios(
        legislacoes=legislacoes_atuais,
        lote=st.session_state.lote,
        on_nova_amostra_callback=abrir_dialogo,
        on_voltar_callback=lambda: navegar_para("amostras"),
        on_salvar_callback=ao_salvar_ensaios,
    )

# Renderização do diálogo modal de upload quando acionado
if st.session_state.get("abrir_dialogo", False):
    abrir_dialogo_upload(
        cliente=st.session_state.ctx_cliente,
        proposta=st.session_state.ctx_proposta,
        local=local_atual,
        legislacoes=legislacoes_atuais,
        proximo_codigo=st.session_state.proximo_codigo,
        on_lote_processado_callback=ao_processar_lote,
    )