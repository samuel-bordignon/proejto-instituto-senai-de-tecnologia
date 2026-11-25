"""Modelos Pydantic da camada core do LaudoTech (POC)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Usuario(BaseModel):
    id: str
    nome_usuario: str
    senha_hash: str

    @property
    def iniciais(self) -> str:
        partes = [p for p in self.nome_usuario.replace("_", ".").replace(" ", ".").split(".") if p]
        if len(partes) >= 2:
            return (partes[0][0] + partes[-1][0]).upper()
        return self.nome_usuario[:2].upper()


class ParametroNorma(BaseModel):
    norma_id: str
    norma_sigla: str
    norma_nome_completo: str
    classe_nome: Optional[str] = None
    operador: Literal["MENOR_IGUAL", "MENOR_ESTRITO", "MAIOR_IGUAL", "FAIXA", "AUSENCIA", "MANUAL"]
    valor_min: Optional[float] = None
    valor_max: Optional[float] = None
    valor_esperado: Optional[str] = None
    unidade: str = ""


class NormaAplicada(BaseModel):
    id: str
    sigla: str
    nome_completo: str
    origem: str
    classe: Optional[str] = None

    @property
    def titulo_coluna(self) -> str:
        if self.classe:
            return f"{self.sigla} {self.classe}"
        return self.sigla

    @property
    def nome_parecer(self) -> str:
        if self.classe:
            return f"{self.nome_completo} ({self.classe})"
        return self.nome_completo


class PontoHistorico(BaseModel):
    data_coleta: date
    rotulo_mes: str
    codigo_amostra: str
    valor_bruto: str
    valor_numerico: Optional[float] = None
    qualificador: Optional[Literal["<", ">"]] = None
    is_atual: bool = False

    @property
    def is_lq(self) -> bool:
        return self.qualificador == "<"

    @property
    def is_ls(self) -> bool:
        return self.qualificador == ">"


class EstatisticaHistorica(BaseModel):
    media: Optional[float] = None
    desvio_padrao: Optional[float] = None
    limiar_superior: Optional[float] = None
    limiar_inferior: Optional[float] = None
    alerta_desvio: bool = False
    motivo: str = "SEM_ALERTA"
    aviso_lq_ls: Optional[str] = None
    n_anteriores: int = 0


class AvaliacaoNorma(BaseModel):
    norma_id: str
    norma_titulo: str
    norma_nome_parecer: str
    vmp_texto: str
    vmp_numerico_ref: Optional[float] = None
    operador: str
    conformidade: Optional[bool] = None  # True=Conforme, False=Não conforme, None=Pendente
    motivo: str = "AVALIADO"  # AVALIADO | UNIDADE_DIVERGENTE | MANUAL_TECNICA | NAO_NUMERICO


class EnsaioResultado(BaseModel):
    codigo: int
    nome: str
    valor_bruto: str
    valor_numerico: Optional[float] = None
    qualificador: Optional[Literal["<", ">"]] = None
    unidade_trabalho: str = ""
    tipo_avaliacao: Literal["AUTOMATICA", "MANUAL_TECNICA"] = "AUTOMATICA"
    avaliacoes: dict[str, AvaliacaoNorma] = Field(default_factory=dict)  # norma_id -> AvaliacaoNorma
    status: Literal["Conforme", "Não conforme", "Pendente"] = "Pendente"
    sinalizacao: Optional[str] = None
    sinalizacao_tipo: Optional[Literal["red", "amber", "gray"]] = None
    observacao: str = ""
    historico: list[PontoHistorico] = Field(default_factory=list)
    estatistica: Optional[EstatisticaHistorica] = None

    @property
    def resultado_formatado(self) -> str:
        if self.unidade_trabalho and self.valor_bruto.lower() not in ("ausente", "presente"):
            if self.unidade_trabalho not in self.valor_bruto:
                return f"{self.valor_bruto} {self.unidade_trabalho}".strip()
        return self.valor_bruto


class LogAlteracao(BaseModel):
    id: str
    data_alteracao: datetime
    usuario: str
    campo_alterado: Literal["conformidade", "parecer_geral", "minuta"]
    ensaio_codigo: Optional[int] = None
    ensaio_nome: Optional[str] = None
    valor_anterior: str
    valor_novo: str
    observacao: Optional[str] = None


class Amostra(BaseModel):
    codigo: str
    data_coleta: date
    data_conclusao: Optional[date] = None
    cliente: str
    proposta: str
    local_coleta: str
    origem: str
    normas: list[NormaAplicada] = Field(default_factory=list)
    ensaios: list[EnsaioResultado] = Field(default_factory=list)
    status_geral: Literal["Favorável", "Não favorável", "Pendente"] = "Pendente"
    parecer: str = ""
    logs: list[LogAlteracao] = Field(default_factory=list)

    @property
    def normas_resumo(self) -> str:
        agrupadas: dict[str, list[str]] = {}
        for n in self.normas:
            agrupadas.setdefault(n.sigla, [])
            if n.classe:
                agrupadas[n.sigla].append(n.classe)
        partes = []
        for sigla, classes in agrupadas.items():
            if classes:
                partes.append(f"{sigla} ({' + '.join(classes)})")
            else:
                partes.append(sigla)
        return " + ".join(partes)


class OcorrenciaPreLeitura(BaseModel):
    classificacao: str
    tipo_pill: Literal["green", "amber", "gray", "red"] = "amber"
    ensaio_coluna: str
    valor_bruto: str
    acao_motor: str


class ResultadoPreLeitura(BaseModel):
    nome_arquivo: str
    amostras_detectadas: int = 1
    codigo_amostra_principal: str
    codigo_externo: Optional[str] = None
    data_coleta: date
    data_conclusao: Optional[date] = None
    duplicada: bool = False
    total_mapeados: int = 0
    total_sem_vmp: int = 0
    total_ignorados: int = 0
    total_avisos: int = 0
    ocorrencias: list[OcorrenciaPreLeitura] = Field(default_factory=list)
    itens_por_kpi: dict[str, list[OcorrenciaPreLeitura]] = Field(default_factory=dict)
    valores_brutos: dict[int, str] = Field(default_factory=dict)  # id_num -> valor_bruto


class ResultadoPreLeituraLote(BaseModel):
    nome_arquivo: str
    amostras: list[ResultadoPreLeitura] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Modelos da Tela B5 — Análise por Local de Coleta
# ---------------------------------------------------------------------------
class MesConformidadeLocal(BaseModel):
    rotulo_mes: str
    favoraveis: int = 0
    pendentes: int = 0
    nao_favoraveis: int = 0
    is_atual: bool = False


class ColetaEnsaioLocal(BaseModel):
    codigo_amostra: str
    data_coleta: date
    valor_bruto: str
    unidade: str = ""
    vmp_prefixo: str = "VMP"
    vmp_texto: str = "—"
    badge_texto: str = "CONFORME"
    badge_variant: Literal["solid-green", "solid-red", "solid-amber", "outline-gray", "outline-amber", "outline-green", "outline-red"] = "outline-green"

    @property
    def resultado_texto(self) -> str:
        if self.unidade and self.valor_bruto.lower() not in ("ausente", "presente"):
            if self.unidade not in self.valor_bruto:
                return f"{self.valor_bruto} {self.unidade}".strip()
        return self.valor_bruto


class GrupoEnsaioLocal(BaseModel):
    codigo_ensaio: int
    nome_ensaio: str
    unidade: str = ""
    total_coletas: int = 0
    media_texto: str = "—"
    conformidade_pct: str = "100,0%"
    nao_conformes: int = 0
    pendentes_desvios_texto: str = "0"
    coletas: list[ColetaEnsaioLocal] = Field(default_factory=list)
