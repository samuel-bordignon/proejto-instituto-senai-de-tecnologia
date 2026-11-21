"""Repositório em memória da POC (interface limpa para futura migração SQLAlchemy/PostgreSQL)."""

from __future__ import annotations

import copy
import uuid
from datetime import date, datetime
from typing import Optional

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    GERAL_PENDENTE,
)
from app.core.models import (
    Amostra,
    ColetaEnsaioLocal,
    EnsaioResultado,
    GrupoEnsaioLocal,
    LogAlteracao,
    MesConformidadeLocal,
    PontoHistorico,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
    Usuario,
)
from app.core.motor_conformidade import (
    avaliar_parametro,
    calcular_status_geral,
    definir_sinalizacao_ensaio,
    formatar_numero_br,
    gerar_parecer_automatico,
    interpretar_valor_bruto,
)
from app.core.parser_ultralims import analisar_lote_ultralims
from app.repo.catalog_fixtures import (
    CATALOGO_ENSAIOS,
    CLIENTES_PROPOSTAS_LOCAIS,
    LEGISLACOES_CATALOGO,
    ORIGENS_AMOSTRA,
    PARAMETROS_VMP,
    USUARIOS_MOCK,
    construir_norma_aplicada,
)
from app.repo.sample_fixtures import (
    SERIE_MENSAL_FALLBACK,
    SERIES_MENSAIS_BASE,
    construir_grupos_referencia_samae_cl1,
    construir_pontos_historicos,
    construir_sementes_mock,
    montar_ensaio,
)


class MockRepository:
    """Repositório em memória (singleton da POC) com contrato desacoplado da UI."""

    def __init__(self) -> None:
        self._amostras: dict[str, Amostra] = {a.codigo: a for a in construir_sementes_mock()}
        self._ordem: list[str] = list(self._amostras.keys())
        self._codigos_importados_sessao: set[str] = set()
        self._seq_codigo: int = 68410

    # --- Autenticação (RF-01) ---
    def autenticar(self, nome_usuario: str, senha: str) -> Optional[Usuario]:
        u = USUARIOS_MOCK.get(nome_usuario.strip().lower())
        if u and u.senha_hash == senha:
            return u
        return None

    # --- Contexto & Normas (RF-02) ---
    def listar_clientes(self) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.keys())

    def listar_propostas(self, cliente: str) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).keys())

    def listar_locais(self, cliente: str, proposta: str) -> list[str]:
        return list(CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).get(proposta, []))

    def listar_locais_por_cliente(self, cliente: str) -> list[str]:
        locais: list[str] = []
        for lista in CLIENTES_PROPOSTAS_LOCAIS.get(cliente, {}).values():
            for loc in lista:
                if loc not in locais:
                    locais.append(loc)
        return locais

    def listar_origens(self) -> list[str]:
        return list(ORIGENS_AMOSTRA)

    def listar_legislacoes_por_origem(self, origem: str) -> list[dict]:
        return [meta for meta in LEGISLACOES_CATALOGO.values() if origem in meta["origens"]]

    def listar_classes_legislacao(self, sigla: str) -> list[str]:
        return list(LEGISLACOES_CATALOGO.get(sigla, {}).get("classes", []))

    # --- Pré-leitura de Planilha UltraLIMS (RF-03) ---
    def analisar_planilha(self, arquivo_bytes: bytes, nome_arquivo: str) -> ResultadoPreLeituraLote:
        """Executa o parser UltraLIMS usando o catálogo e unidades de referência do repositório."""
        unidades_vmp_ref = {
            cod: p.unidade for (cod, _), p in PARAMETROS_VMP.items() if p.unidade
        }
        codigos_com_vmp = {cod for (cod, _) in PARAMETROS_VMP.keys()}
        return analisar_lote_ultralims(
            arquivo_bytes=arquivo_bytes,
            nome_arquivo=nome_arquivo,
            catalogo_ensaios=CATALOGO_ENSAIOS,
            unidades_vmp_referencia=unidades_vmp_ref,
            codigos_com_vmp=codigos_com_vmp,
        )

    # --- Painel (B2) ---
    def listar_amostras(
        self,
        status_filtro: str = "Todos",
        busca: str = "",
    ) -> list[Amostra]:
        termo = busca.strip().lower()
        resultado: list[Amostra] = []
        for cod in self._ordem:
            a = self._amostras[cod]
            if status_filtro in (GERAL_FAVORAVEL, GERAL_NAO_FAVORAVEL, GERAL_PENDENTE):
                if a.status_geral != status_filtro:
                    continue
            if termo:
                haystack = f"{a.codigo} {a.cliente} {a.local_coleta} {a.normas_resumo}".lower()
                if termo not in haystack:
                    continue
            resultado.append(copy.deepcopy(a))
        return resultado

    def obter_amostra(self, codigo: str) -> Optional[Amostra]:
        a = self._amostras.get(codigo)
        if a:
            return copy.deepcopy(a)
        hist_a = self._materializar_amostra_historica(codigo)
        return copy.deepcopy(hist_a) if hist_a else None

    # --- Conferência & Auditoria (RF-05 / RN-10 / CT-16..18) ---
    def salvar_conferencia(
        self,
        codigo: str,
        edicoes_status: dict[int, str],
        edicoes_obs: dict[int, str],
        novo_parecer: str,
        usuario: str,
    ) -> tuple[Amostra, int]:
        amostra = self._amostras[codigo]
        agora = datetime.now()
        novos_logs: list[LogAlteracao] = []
        status_geral_anterior = amostra.status_geral
        parecer_anterior = amostra.parecer

        for ensaio in amostra.ensaios:
            novo_st = edicoes_status.get(ensaio.codigo, ensaio.status)
            nova_obs = edicoes_obs.get(ensaio.codigo, ensaio.observacao).strip()
            obs_mudou = nova_obs != ensaio.observacao

            if novo_st != ensaio.status:
                novos_logs.append(
                    LogAlteracao(
                        id=str(uuid.uuid4()),
                        data_alteracao=agora,
                        usuario=usuario,
                        campo_alterado="conformidade",
                        ensaio_codigo=ensaio.codigo,
                        ensaio_nome=ensaio.nome,
                        valor_anterior=ensaio.status,
                        valor_novo=novo_st,
                        observacao=nova_obs or None,
                    )
                )
                ensaio.status = novo_st  # type: ignore[assignment]
            elif obs_mudou:
                novos_logs.append(
                    LogAlteracao(
                        id=str(uuid.uuid4()),
                        data_alteracao=agora,
                        usuario=usuario,
                        campo_alterado="conformidade",
                        ensaio_codigo=ensaio.codigo,
                        ensaio_nome=ensaio.nome,
                        valor_anterior=ensaio.status,
                        valor_novo=ensaio.status,
                        observacao=nova_obs or "(observação removida)",
                    )
                )

            ensaio.observacao = nova_obs
            sinal, sinal_tipo = definir_sinalizacao_ensaio(ensaio)
            ensaio.sinalizacao = sinal
            ensaio.sinalizacao_tipo = sinal_tipo  # type: ignore[arg-type]

        novo_status_geral = calcular_status_geral(amostra.ensaios)
        if novo_status_geral != status_geral_anterior:
            amostra.status_geral = novo_status_geral  # type: ignore[assignment]
            novos_logs.append(
                LogAlteracao(
                    id=str(uuid.uuid4()),
                    data_alteracao=agora,
                    usuario=usuario,
                    campo_alterado="parecer_geral",
                    valor_anterior=status_geral_anterior,
                    valor_novo=novo_status_geral,
                )
            )

        parecer_limpo = novo_parecer.strip()
        if parecer_limpo != parecer_anterior.strip():
            amostra.parecer = parecer_limpo
            novos_logs.append(
                LogAlteracao(
                    id=str(uuid.uuid4()),
                    data_alteracao=agora,
                    usuario=usuario,
                    campo_alterado="minuta",
                    valor_anterior=parecer_anterior,
                    valor_novo=parecer_limpo,
                )
            )

        if novos_logs:
            amostra.logs = list(reversed(novos_logs)) + amostra.logs

        return copy.deepcopy(amostra), len(novos_logs)

    # --- Importação (B3 -> B4) ---
    def criar_amostra_importada(
        self,
        pre_leitura: ResultadoPreLeitura,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> Amostra:
        codigo = pre_leitura.codigo_amostra_principal
        while codigo in self._amostras:
            self._seq_codigo += 1
            codigo = f"{self._seq_codigo}/2026"

        normas = [construir_norma_aplicada(sigla, origem, cl) for sigla, cl in normas_selecionadas]
        valores = pre_leitura.valores_brutos or {
            800: "40,0", 106: "71,00", 268: "<0,200", 794: "7,91", 119: "<0,3", 784: "Ausente",
        }

        ensaios: list[EnsaioResultado] = []
        for cod_ensaio, bruto in valores.items():
            if cod_ensaio not in CATALOGO_ENSAIOS:
                continue
            if not any((cod_ensaio, n.id) in PARAMETROS_VMP for n in normas):
                continue
            hist = self._obter_historico_base_ensaio(cod_ensaio, bruto, codigo, pre_leitura.data_coleta)
            ensaios.append(montar_ensaio(cod_ensaio, bruto, normas, hist))

        if not ensaios:
            cods_normas: list[int] = []
            for c_id, n_id in PARAMETROS_VMP:
                if any(n.id == n_id for n in normas) and c_id not in cods_normas:
                    cods_normas.append(c_id)
            defaults = {
                800: "34,5", 106: "16,2", 268: "<0,200", 794: "7,40", 119: "<0,3",
                784: "Ausente", 19: "2,4", 59: "180", 48: "2,1", 157: "<0,005",
                877: "42,0", 259: "0,04",
            }
            for cod_ensaio in cods_normas[:6]:
                bruto = defaults.get(cod_ensaio, "1,0")
                hist = self._obter_historico_base_ensaio(cod_ensaio, bruto, codigo, pre_leitura.data_coleta)
                ensaios.append(montar_ensaio(cod_ensaio, bruto, normas, hist))

        amostra = Amostra(
            codigo=codigo,
            data_coleta=pre_leitura.data_coleta,
            data_conclusao=pre_leitura.data_conclusao,
            cliente=cliente,
            proposta=proposta,
            local_coleta=local_coleta,
            origem=origem,
            normas=normas,
            ensaios=ensaios,
            logs=[],
        )
        amostra.status_geral = calcular_status_geral(amostra.ensaios)  # type: ignore[assignment]
        amostra.parecer = gerar_parecer_automatico(amostra)

        self._amostras[codigo] = amostra
        self._ordem.insert(0, codigo)
        self._codigos_importados_sessao.add(codigo)
        return copy.deepcopy(amostra)

    def criar_lote_importado(
        self,
        lote: ResultadoPreLeituraLote,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> list[Amostra]:
        criadas: list[Amostra] = []
        for pre in reversed(lote.amostras):
            am = self.criar_amostra_importada(
                pre_leitura=pre,
                cliente=cliente,
                proposta=proposta,
                local_coleta=local_coleta,
                origem=origem,
                normas_selecionadas=normas_selecionadas,
            )
            criadas.insert(0, am)
        return criadas

    # --- Tela B5 — Análise por Local de Coleta ---
    def listar_normas_do_local(self, cliente: str, local_coleta: str) -> list[str]:
        normas_encontradas: list[str] = []
        for a in self._amostras.values():
            if a.cliente == cliente and a.local_coleta == local_coleta:
                for n in a.normas:
                    rotulo = f"{n.sigla} — {n.classe}" if n.classe else n.sigla
                    if rotulo not in normas_encontradas:
                        normas_encontradas.append(rotulo)
        if normas_encontradas:
            return normas_encontradas
        if "ETE" in local_coleta or "Efluente" in local_coleta:
            return ["CONAMA 430 — Sem Classe", "CONAMA 430 — Sanitário"]
        if "Tratamento" in local_coleta or "Reservatório" in local_coleta:
            return ["GM/MS 888", "SES-SC 1468"]
        return ["CONAMA 357 — Classe 1", "CONAMA 357 — Classe 2"]

    def _localizar_amostra_referencia(
        self, cliente: str, local_coleta: str, norma_label: str
    ) -> Amostra:
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente and a.local_coleta == local_coleta:
                if any((f"{n.sigla} — {n.classe}" if n.classe else n.sigla) == norma_label for n in a.normas):
                    return a
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente and a.local_coleta == local_coleta:
                return a
        for cod in self._ordem:
            a = self._amostras[cod]
            if a.cliente == cliente:
                return a
        return self._amostras["65462/2026"]

    def obter_evolucao_mensal_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[MesConformidadeLocal]:
        dados = SERIES_MENSAIS_BASE.get(local_coleta, SERIE_MENSAL_FALLBACK)
        recorte = dados[-periodo_meses:] if periodo_meses > 0 else dados
        meses_out = [
            MesConformidadeLocal(
                rotulo_mes=rot,
                favoraveis=fav,
                pendentes=pend,
                nao_favoraveis=nfav,
                is_atual=(idx == len(recorte) - 1),
            )
            for idx, (rot, fav, pend, nfav) in enumerate(recorte)
        ]

        # Soma ao mês mais recente apenas amostras importadas durante esta sessão (sem heurística de prefixo)
        if meses_out:
            ultimo = meses_out[-1]
            for cod in self._codigos_importados_sessao:
                a = self._amostras.get(cod)
                if a and a.cliente == cliente and a.local_coleta == local_coleta:
                    if a.status_geral == GERAL_FAVORAVEL:
                        ultimo.favoraveis += 1
                    elif a.status_geral == GERAL_PENDENTE:
                        ultimo.pendentes += 1
                    else:
                        ultimo.nao_favoraveis += 1

        return meses_out

    def obter_tabela_dinamica_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[GrupoEnsaioLocal]:
        if local_coleta == "Captação — Rio Itajaí-Açu" and "Classe 1" in norma_label:
            grupos_ref = construir_grupos_referencia_samae_cl1()
            if periodo_meses == 3:
                for g in grupos_ref:
                    g.coletas = g.coletas[:3]
                    g.total_coletas = len(g.coletas)
            return grupos_ref

        ref = self._localizar_amostra_referencia(cliente, local_coleta, norma_label)
        norma_alvo = next(
            (n for n in ref.normas if (f"{n.sigla} — {n.classe}" if n.classe else n.sigla) == norma_label),
            ref.normas[0] if ref.normas else None,
        )

        grupos: list[GrupoEnsaioLocal] = []
        for e in ref.ensaios:
            pontos_rec = list(reversed(e.historico))[: (3 if periodo_meses == 3 else None)]
            av = e.avaliacoes.get(norma_alvo.id) if norma_alvo else None
            vmp_txt = av.vmp_texto if av else "—"
            vmp_pref = f"VMP {norma_alvo.classe or norma_alvo.sigla}" if norma_alvo else "VMP"
            param = PARAMETROS_VMP.get((e.codigo, norma_alvo.id)) if norma_alvo else None

            coletas_out: list[ColetaEnsaioLocal] = []
            nums: list[float] = []
            qtd_ok = qtd_nc = qtd_pend = qtd_desv = 0

            for idx_p, p in enumerate(pontos_rec):
                if p.valor_numerico is not None and not p.is_lq:
                    nums.append(p.valor_numerico)

                if param:
                    ok, motivo = avaliar_parametro(p.valor_bruto, e.tipo_avaliacao, e.unidade_trabalho, param)
                else:
                    ok, motivo = True, "AVALIADO"

                if ok is False:
                    qtd_nc += 1
                    b_txt, b_var = "NÃO CONFORME", "solid-red"
                elif ok is None:
                    qtd_pend += 1
                    b_txt = "UNID. DIVERGENTE" if motivo == "UNIDADE_DIVERGENTE" else "PENDENTE (<LQ)"
                    b_var = "outline-gray"
                else:
                    qtd_ok += 1
                    if idx_p == 0 and e.estatistica and e.estatistica.alerta_desvio:
                        qtd_desv += 1
                        b_txt, b_var = "DESVIO > μ+0,20σ", "outline-amber"
                    else:
                        b_txt, b_var = "CONFORME", "outline-green"

                coletas_out.append(
                    ColetaEnsaioLocal(
                        codigo_amostra=p.codigo_amostra,
                        data_coleta=p.data_coleta,
                        valor_bruto=p.valor_bruto,
                        unidade=e.unidade_trabalho,
                        vmp_prefixo=vmp_pref,
                        vmp_texto=vmp_txt,
                        badge_texto=b_txt,
                        badge_variant=b_var,  # type: ignore[arg-type]
                    )
                )

            total = len(coletas_out)
            pct = f"{(qtd_ok / total * 100):.1f}%".replace(".", ",") if total else "—"
            media_str = (
                f"{formatar_numero_br(sum(nums) / len(nums), 2)} {e.unidade_trabalho}".strip()
                if nums
                else "Qualitativo"
            )
            notas = []
            if qtd_pend:
                notas.append(f"{qtd_pend} Pendente" + ("s" if qtd_pend > 1 else ""))
            if qtd_desv:
                notas.append(f"{qtd_desv} Desvio (> μ+0,20σ)")

            grupos.append(
                GrupoEnsaioLocal(
                    codigo_ensaio=e.codigo,
                    nome_ensaio=e.nome,
                    unidade=e.unidade_trabalho,
                    total_coletas=total,
                    media_texto=media_str,
                    conformidade_pct=pct,
                    nao_conformes=qtd_nc,
                    pendentes_desvios_texto=" · ".join(notas) if notas else "0",
                    coletas=coletas_out,
                )
            )
        return grupos

    def _materializar_amostra_historica(self, codigo: str) -> Optional[Amostra]:
        for a in self._amostras.values():
            valores_hist: dict[int, tuple[date, str]] = {}
            for e in a.ensaios:
                for p in e.historico:
                    if p.codigo_amostra == codigo:
                        valores_hist[e.codigo] = (p.data_coleta, p.valor_bruto)
            if valores_hist:
                dt_coleta = next(iter(valores_hist.values()))[0]
                ensaios_mat: list[EnsaioResultado] = []
                for e in a.ensaios:
                    bruto = valores_hist.get(e.codigo, (dt_coleta, e.valor_bruto))[1]
                    hist_clone = [copy.deepcopy(p) for p in e.historico if p.data_coleta <= dt_coleta]
                    for hp in hist_clone:
                        hp.is_atual = hp.codigo_amostra == codigo
                    ensaios_mat.append(montar_ensaio(e.codigo, bruto, a.normas, hist_clone))
                nova = Amostra(
                    codigo=codigo,
                    data_coleta=dt_coleta,
                    data_conclusao=dt_coleta,
                    cliente=a.cliente,
                    proposta=a.proposta,
                    local_coleta=a.local_coleta,
                    origem=a.origem,
                    normas=copy.deepcopy(a.normas),
                    ensaios=ensaios_mat,
                    logs=[],
                )
                nova.status_geral = calcular_status_geral(nova.ensaios)  # type: ignore[assignment]
                nova.parecer = gerar_parecer_automatico(nova)
                self._amostras[codigo] = nova
                return nova
        return None

    def _obter_historico_base_ensaio(
        self,
        cod_ensaio: int,
        bruto_atual: str,
        codigo_atual: str,
        data_atual: date,
    ) -> list[PontoHistorico]:
        for a in self._amostras.values():
            for e in a.ensaios:
                if e.codigo == cod_ensaio and len(e.historico) >= 3:
                    anteriores = [copy.deepcopy(p) for p in e.historico if not p.is_atual][-5:]
                    _, q, v = interpretar_valor_bruto(bruto_atual)
                    if v is None and bruto_atual.strip().lower() == "ausente":
                        v = 0.0
                    anteriores.append(
                        PontoHistorico(
                            data_coleta=data_atual,
                            rotulo_mes=f"{data_atual.strftime('%b/%y')} Atual",
                            codigo_amostra=codigo_atual,
                            valor_bruto=bruto_atual,
                            valor_numerico=v,
                            qualificador=q,  # type: ignore[arg-type]
                            is_atual=True,
                        )
                    )
                    return anteriores
        return construir_pontos_historicos(
            [(f"{data_atual.strftime('%b/%y')} Atual", data_atual, codigo_atual, bruto_atual, True)]
        )


# Instância singleton da POC
repo = MockRepository()
