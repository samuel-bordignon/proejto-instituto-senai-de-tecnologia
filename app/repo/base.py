"""Contrato formal (Protocol) do repositório de dados do LaudoTech (DEV-14)."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.core.models import (
    Amostra,
    GrupoEnsaioLocal,
    MesConformidadeLocal,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
    Usuario,
)


@runtime_checkable
class RepositorioLaudoTech(Protocol):
    """Interface desacoplada consumida pelas telas NiceGUI e serviços."""

    def recarregar_catalogo(self) -> None: ...

    # --- Autenticação (RF-01) ---
    def autenticar(self, nome_usuario: str, senha: str) -> Optional[Usuario]: ...

    # --- Contexto Comercial e Base Legal (RF-02 / RNF-01) ---
    def listar_clientes(self) -> list[str]: ...

    def listar_propostas(self, cliente: str) -> list[str]: ...

    def listar_locais(self, cliente: str, proposta: str) -> list[str]: ...

    def listar_locais_por_cliente(self, cliente: str) -> list[str]: ...

    def obter_contexto_padrao_proposta(self, cliente: str, proposta: str) -> dict: ...

    def listar_origens(self) -> list[str]: ...

    def listar_legislacoes_por_origem(self, origem: str) -> list[dict]: ...

    def listar_classes_legislacao(self, sigla: str, origem: Optional[str] = None) -> list[str]: ...

    # --- Pré-leitura e Importação UltraLIMS (RF-03 / RF-04 / CT-10 / CT-11) ---
    def analisar_planilha(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        origem: Optional[str] = None,
        normas_selecionadas: Optional[list[tuple[str, Optional[str]]]] = None,
    ) -> ResultadoPreLeituraLote: ...

    def recalcular_lote(
        self,
        lote: ResultadoPreLeituraLote,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> ResultadoPreLeituraLote: ...

    def criar_amostra_importada(
        self,
        pre_leitura: ResultadoPreLeitura,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
        usuario: Optional[str] = None,
    ) -> Amostra: ...

    def criar_lote_importado(
        self,
        lote: ResultadoPreLeituraLote,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
        usuario: Optional[str] = None,
    ) -> list[Amostra]: ...

    def excluir_amostra(self, codigo: str) -> int: ...

    # --- Painel & Conferência (RF-05 / RN-10 / CT-16) ---
    def listar_amostras(
        self,
        status_filtro: str = "Todos",
        busca: str = "",
    ) -> list[Amostra]: ...

    def obter_amostra(self, codigo: str) -> Optional[Amostra]: ...

    def salvar_conferencia(
        self,
        codigo: str,
        edicoes_status: dict[int, str],
        edicoes_obs: dict[int, str],
        novo_parecer: str,
        usuario: str,
    ) -> tuple[Amostra, int]: ...

    # --- Análise por Local de Coleta (RF-06) ---
    def listar_normas_do_local(self, cliente: str, local_coleta: str) -> list[str]: ...

    def obter_evolucao_mensal_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[MesConformidadeLocal]: ...

    def obter_tabela_dinamica_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[GrupoEnsaioLocal]: ...
