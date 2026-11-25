"""Repositório de produção PostgreSQL/Supabase consumindo database/queries/*.sql (DEV-14)."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime
import re
import threading
from typing import Any, Optional

import psycopg

from app.core.config import (
    GERAL_FAVORAVEL,
    GERAL_NAO_FAVORAVEL,
    GERAL_PENDENTE,
    JANELA_MESES,
    MAX_RESULTADOS_HISTORICO,
    STATUS_CONFORME,
    STATUS_NAO_CONFORME,
    STATUS_PENDENTE,
)
from app.core.estatistica_historica import _subtrair_meses, calcular_estatistica_historica
from app.core.models import (
    Amostra,
    AvaliacaoNorma,
    ColetaEnsaioLocal,
    EnsaioResultado,
    GrupoEnsaioLocal,
    LogAlteracao,
    MesConformidadeLocal,
    NormaAplicada,
    ParametroNorma,
    PontoHistorico,
    ResultadoPreLeitura,
    ResultadoPreLeituraLote,
    Usuario,
)
from app.core.motor_conformidade import (
    avaliar_parametro,
    calcular_status_geral,
    consolidar_status_ensaio,
    definir_sinalizacao_ensaio,
    formatar_numero_br,
    formatar_vmp_texto,
    gerar_parecer_automatico,
    interpretar_valor_bruto,
    ordenar_lote_por_prioridade,
)
from app.core.parser_ultralims import analisar_lote_ultralims, recalcular_lote_por_normas
from database import consultar_lista, consultar_um, executar_sql, obter_query, transaction


_MESES_PT = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

_SIGLAS_CONHECIDAS = {
    "Portaria GM/MS 888/2021": "GM/MS 888",
    "Portaria SES/SC 1468/2022": "SES-SC 1468",
    "Resolução CONAMA 430/2011": "CONAMA 430",
    "Resolução CONAMA 357/2005": "CONAMA 357",
}


def _sigla_legislacao(nome_completo: str) -> str:
    if nome_completo in _SIGLAS_CONHECIDAS:
        return _SIGLAS_CONHECIDAS[nome_completo]
    limpo = re.sub(r"^(Portaria|Resolução)\s+", "", nome_completo.strip(), flags=re.IGNORECASE)
    limpo = re.sub(r"/\d{4}$", "", limpo).strip()
    return limpo or nome_completo


def _limpar_rotulo_classe(classe_ui: Optional[str]) -> Optional[str]:
    """Remove sufixos explicativos de UI (' (Art. 21)', ' (Art. 16)') mantendo 'Sanitário' / 'Sem Classe'."""
    if not classe_ui:
        return None
    limpa = (
        classe_ui.replace(" (Art. 21)", "")
        .replace(" (Art. 16)", "")
        .replace("Águas Doces — ", "")
        .strip()
    )
    return limpa or None


def _classe_ui_dropdown(sigla: str, classe_db: Optional[str], possui_classes: bool) -> Optional[str]:
    """Formata o rótulo exibido no seletor da Tela B3 (/importar)."""
    if not possui_classes:
        return None
    if classe_db is None:
        return "Sem Classe (Art. 16)" if sigla == "CONAMA 430" else "Sem Classe"
    if sigla == "CONAMA 430" and classe_db == "Sanitário":
        return "Sanitário (Art. 21)"
    return classe_db


def _classe_canonica_norma(classe_db: Optional[str], possui_classes: bool) -> Optional[str]:
    """Retorna o nome curto de classe usado em NormaAplicada (`None` p/ Portaria, `'Sem Classe'` p/ Art. 16)."""
    if not possui_classes:
        return None
    return classe_db if classe_db is not None else "Sem Classe"


def _classe_para_db(classe_ui: Optional[str], possui_classes: bool) -> Optional[str]:
    """Converte o rótulo de classe da UI de volta para `classe.nome` no banco (`None` p/ Sem Classe ou Portaria)."""
    if not possui_classes:
        return None
    limpa = _limpar_rotulo_classe(classe_ui)
    if not limpa or limpa.lower() == "sem classe":
        return None
    return limpa


def _norma_id(sigla: str, classe_canonica: Optional[str]) -> str:
    return f"{sigla}|{classe_canonica}" if classe_canonica else f"{sigla}|"


def _rotulo_mes(dt: date, incluir_dia: bool = False) -> str:
    mes = _MESES_PT.get(dt.month, dt.strftime("%b"))
    ano = str(dt.year)[-2:]
    if incluir_dia:
        return f"{dt.day:02d}/{mes}/{ano}"
    return f"{mes}/{ano}"


def _status_bool_para_ensaio(val: Optional[bool]) -> str:
    if val is True:
        return STATUS_CONFORME
    if val is False:
        return STATUS_NAO_CONFORME
    return STATUS_PENDENTE


def _status_ensaio_para_bool(status: str) -> Optional[bool]:
    if status == STATUS_CONFORME:
        return True
    if status == STATUS_NAO_CONFORME:
        return False
    return None


def _status_bool_para_geral(val: Optional[bool]) -> str:
    if val is True:
        return GERAL_FAVORAVEL
    if val is False:
        return GERAL_NAO_FAVORAVEL
    return GERAL_PENDENTE


def _status_geral_para_bool(status_geral: str) -> Optional[bool]:
    if status_geral == GERAL_FAVORAVEL:
        return True
    if status_geral == GERAL_NAO_FAVORAVEL:
        return False
    return None


def _vmp_ref_numerico(operador: str, vmin: Optional[float], vmax: Optional[float]) -> Optional[float]:
    if operador in ("MENOR_IGUAL", "MENOR_ESTRITO"):
        return vmax
    if operador == "MAIOR_IGUAL":
        return vmin
    if operador == "FAIXA":
        return vmax
    return None


def _construir_pilha_logs_auditoria(logs_rows: list[dict[str, Any]]) -> list[LogAlteracao]:
    """
    Modela o histórico de auditoria (RN-10) como uma Pilha (LIFO) usando collections.deque.
    Cada registro é empilhado no topo via `appendleft()` em tempo constante O(1),
    evitando deslocamento de memória O(n) causado por `list.insert(0, ...)`.
    Como `listar_logs_por_amostra` vem ordenado do mais recente para o mais antigo,
    percorremos em ordem cronológica (reversa) para empilhar o evento mais recente no topo.
    """
    pilha_logs: deque[LogAlteracao] = deque()

    for lr in reversed(logs_rows):
        campo_valido = (
            lr["campo_alterado"]
            if lr["campo_alterado"] in ("conformidade", "parecer_geral", "minuta")
            else "conformidade"
        )
        registro = LogAlteracao(
            id=lr["id"],
            data_alteracao=lr["data_alteracao"],
            usuario=lr["usuario"],
            campo_alterado=campo_valido,
            ensaio_codigo=int(lr["ensaio_codigo"]) if lr["ensaio_codigo"] is not None else None,
            ensaio_nome=lr["ensaio_nome"],
            valor_anterior=lr["valor_anterior"] or "",
            valor_novo=lr["valor_novo"] or "",
            observacao=lr["observacao"],
        )
        pilha_logs.appendleft(registro)

    return list(pilha_logs)


class PostgresRepository:
    """Repositório de produção conectado ao PostgreSQL/Supabase com cache de catálogo base."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._carregado = False

        # Estruturas de cache do catálogo mestre
        self._origens: list[str] = []
        self._origens_id_por_nome: dict[str, str] = {}
        self._ensaios_por_id_num: dict[int, dict[str, str]] = {}
        self._ensaios_uuid_por_id_num: dict[int, str] = {}
        self._leg_meta_por_sigla: dict[str, dict[str, Any]] = {}
        self._sigla_por_nome_leg: dict[str, str] = {}
        self._possui_classes_por_leg_origem: dict[tuple[str, str], bool] = {}
        # (origem_nome, sigla, classe_db) -> {id_num: (parametro_uuid, ParametroNorma)}
        self._parametros_por_contexto: dict[
            tuple[str, str, Optional[str]], dict[int, tuple[str, ParametroNorma]]
        ] = {}
        self._clientes: list[str] = []
        self._propostas_por_cliente: dict[str, dict[str, dict[str, Any]]] = {}
        self._rotulo_proposta_por_id: dict[str, str] = {}
        self._locais_id_por_nome: dict[str, str] = {}
        self._locais_por_cliente_proposta: dict[tuple[str, str], list[str]] = {}
        self._locais_por_cliente: dict[str, list[str]] = {}
        self._legs_por_proposta_id: dict[str, list[str]] = {}
        self._laboratorio_padrao_id: Optional[str] = None
        self._usuario_padrao_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Cache do Catálogo Mestre (ensaios, legislações, VMPs, cadastros)
    # ------------------------------------------------------------------
    def _garantir_catalogo(self) -> None:
        if not self._carregado:
            self.recarregar_catalogo()

    def recarregar_catalogo(self) -> None:
        """Recarrega em memória o catálogo base do Supabase usando database/queries/*.sql."""
        with self._lock:
            origens_rows = consultar_lista(obter_query("base_legal", "listar_origens"))
            leg_orig_rows = consultar_lista(obter_query("base_legal", "listar_legislacoes_origens_classes"))
            ensaios_rows = consultar_lista(obter_query("base_legal", "listar_ensaios"))
            params_rows = consultar_lista(obter_query("base_legal", "listar_parametros_vmp"))
            clientes_rows = consultar_lista(obter_query("cadastros", "listar_clientes"))
            propostas_rows = consultar_lista(obter_query("cadastros", "listar_propostas_com_cliente"))
            locais_rows = consultar_lista(obter_query("cadastros", "listar_locais_propostas"))
            prop_legs_rows = consultar_lista(obter_query("cadastros", "listar_proposta_legislacoes"))
            lab_row = consultar_um(obter_query("cadastros", "buscar_laboratorio_padrao"))
            usr_row = consultar_um(obter_query("auth", "buscar_usuario_padrao"))

            self._origens = [r["nome"] for r in origens_rows]
            self._origens_id_por_nome = {r["nome"]: r["id"] for r in origens_rows}

            self._ensaios_por_id_num = {}
            self._ensaios_uuid_por_id_num = {}
            for r in ensaios_rows:
                cod = int(r["id_num"])
                self._ensaios_uuid_por_id_num[cod] = r["id"]
                self._ensaios_por_id_num[cod] = {
                    "nome": r["descricao"],
                    "unidade": r["unidade"] or "",
                    "tipo": r["tipo_avaliacao"] or "AUTOMATICA",
                }

            leg_meta: dict[str, dict[str, Any]] = {}
            sigla_por_nome: dict[str, str] = {}
            possui_classes_map: dict[tuple[str, str], bool] = {}

            # Usamos dicionários como conjuntos ordenados (dict.fromkeys / chaves únicas em O(1))
            # para evitar verificações lineares 'if x not in lista' (O(n²)).
            for r in leg_orig_rows:
                nome_leg = r["legislacao_nome"]
                sigla = _sigla_legislacao(nome_leg)
                sigla_por_nome[nome_leg] = sigla
                origem_nome = r["origem_nome"]
                possui_cl = bool(r["possui_classes"])
                possui_sem_cl = bool(r["possui_sem_classe"])
                possui_classes_map[(nome_leg, origem_nome)] = possui_cl

                meta = leg_meta.setdefault(
                    sigla,
                    {
                        "sigla": sigla,
                        "nome_completo": nome_leg,
                        "legislacao_id": r["legislacao_id"],
                        "origens_set": {},
                        "classes_set": {},
                        "classes_por_origem_set": defaultdict(dict),
                        "possui_classes": possui_cl,
                    },
                )
                if possui_cl:
                    meta["possui_classes"] = True
                meta["origens_set"][origem_nome] = None

                if possui_cl:
                    if r["classe_nome"]:
                        lbl_cl = _classe_ui_dropdown(sigla, r["classe_nome"], True)
                        if lbl_cl:
                            meta["classes_set"][lbl_cl] = None
                            meta["classes_por_origem_set"][origem_nome][lbl_cl] = None
                    if possui_sem_cl:
                        lbl_sem = _classe_ui_dropdown(sigla, None, True)
                        if lbl_sem:
                            meta["classes_set"][lbl_sem] = None
                            meta["classes_por_origem_set"][origem_nome][lbl_sem] = None

            # Materializa as listas finais deduplicadas em O(n) mantendo a ordem de inserção
            for meta in leg_meta.values():
                meta["origens"] = list(meta.pop("origens_set").keys())
                meta["classes"] = list(meta.pop("classes_set").keys())
                meta["classes_por_origem"] = defaultdict(
                    list,
                    {
                        orig: list(classes_dict.keys())
                        for orig, classes_dict in meta.pop("classes_por_origem_set").items()
                    },
                )

            self._leg_meta_por_sigla = leg_meta
            self._sigla_por_nome_leg = sigla_por_nome
            self._possui_classes_por_leg_origem = possui_classes_map

            params_ctx: dict[
                tuple[str, str, Optional[str]], dict[int, tuple[str, ParametroNorma]]
            ] = defaultdict(dict)
            for r in params_rows:
                nome_leg = r["legislacao_nome"]
                sigla = sigla_por_nome.get(nome_leg, _sigla_legislacao(nome_leg))
                origem_nome = r["origem_nome"]
                classe_db: Optional[str] = r["classe_nome"]
                possui_cl = possui_classes_map.get((nome_leg, origem_nome), bool(classe_db))
                classe_can = _classe_canonica_norma(classe_db, possui_cl)
                nid = _norma_id(sigla, classe_can)
                cod_ensaio = int(r["id_num"])
                op_raw = (r["operador"] or "MANUAL").strip().upper()
                if op_raw not in ("MENOR_IGUAL", "MENOR_ESTRITO", "MAIOR_IGUAL", "FAIXA", "AUSENCIA", "MANUAL"):
                    op_raw = "MANUAL"

                p_obj = ParametroNorma(
                    norma_id=nid,
                    norma_sigla=sigla,
                    norma_nome_completo=nome_leg,
                    classe_nome=classe_can,
                    operador=op_raw,  # type: ignore[arg-type]
                    valor_min=float(r["valor_min"]) if r["valor_min"] is not None else None,
                    valor_max=float(r["valor_max"]) if r["valor_max"] is not None else None,
                    valor_esperado=r["valor_esperado"],
                    unidade=r["unidade"] or "",
                )
                params_ctx[(origem_nome, sigla, classe_db)][cod_ensaio] = (r["parametro_id"], p_obj)

            self._parametros_por_contexto = dict(params_ctx)

            # Clientes, Propostas (rótulo derivado sem coluna redundante) e Locais
            self._clientes = [r["razao_social"] for r in clientes_rows]
            legs_por_prop: dict[str, list[str]] = defaultdict(list)
            for r in prop_legs_rows:
                legs_por_prop[r["proposta_id"]].append(r["legislacao_nome"])
            self._legs_por_proposta_id = dict(legs_por_prop)

            props_por_cli: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
            rotulo_por_id: dict[str, str] = {}
            for r in propostas_rows:
                cli_nome = r["cliente_nome"]
                pid = r["proposta_id"]
                dt_ini = r["data_inicio"].strftime("%d/%m/%Y") if r["data_inicio"] else "—"
                dt_fim = r["data_fim"].strftime("%d/%m/%Y") if r["data_fim"] else "—"
                nomes_legs = legs_por_prop.get(pid, [])
                siglas_txt = (
                    " + ".join(_sigla_legislacao(nm) for nm in nomes_legs)
                    if nomes_legs
                    else "Sem legislação"
                )
                rotulo_base = f"Vigência {dt_ini} a {dt_fim} · {siglas_txt}"
                rotulo = rotulo_base
                if rotulo in props_por_cli[cli_nome]:
                    rotulo = f"{rotulo_base} (#{pid[-4:]})"
                props_por_cli[cli_nome][rotulo] = {
                    "proposta_id": pid,
                    "cliente_id": r["cliente_id"],
                    "legislacoes_nomes": nomes_legs,
                }
                rotulo_por_id[pid] = rotulo

            self._propostas_por_cliente = dict(props_por_cli)
            self._rotulo_proposta_por_id = rotulo_por_id

            loc_id_por_nome: dict[str, str] = {}
            loc_por_cli_prop_dict: dict[tuple[str, str], dict[str, None]] = defaultdict(dict)
            loc_por_cli_dict: dict[str, dict[str, None]] = defaultdict(dict)

            for r in locais_rows:
                lnome = r["local_nome"]
                lid = r["local_id"]
                cli_nome = r["cliente_nome"]
                pid = r["proposta_id"]
                rot_prop = rotulo_por_id.get(pid, "")

                loc_id_por_nome[lnome] = lid
                if rot_prop:
                    loc_por_cli_prop_dict[(cli_nome, rot_prop)][lnome] = None
                loc_por_cli_dict[cli_nome][lnome] = None

            self._locais_id_por_nome = loc_id_por_nome
            self._locais_por_cliente_proposta = {
                chave: list(locais_unicos.keys())
                for chave, locais_unicos in loc_por_cli_prop_dict.items()
            }
            self._locais_por_cliente = {
                cli: list(locais_unicos.keys())
                for cli, locais_unicos in loc_por_cli_dict.items()
            }
            self._laboratorio_padrao_id = lab_row["id"] if lab_row else None
            self._usuario_padrao_id = usr_row["id"] if usr_row else None
            self._carregado = True

    # ------------------------------------------------------------------
    # Autenticação (RF-01)
    # ------------------------------------------------------------------
    def autenticar(self, nome_usuario: str, senha: str) -> Optional[Usuario]:
        login_limpo = (nome_usuario or "").strip()
        if not login_limpo or not senha:
            return None
        row = consultar_um(obter_query("auth", "buscar_usuario_por_login"), (login_limpo,))
        if not row:
            return None
        if str(row["senha_hash"]) != str(senha):
            return None
        return Usuario(
            id=row["id"],
            nome_usuario=row["nome_usuario"],
            senha_hash=row["senha_hash"],
        )

    def _resolver_usuario_id(self, usuario: Optional[str], conn: Optional[psycopg.Connection] = None) -> str:
        self._garantir_catalogo()
        if usuario:
            termo = usuario.strip()
            row = consultar_um(
                obter_query("auth", "buscar_usuario_por_id_ou_login"),
                (termo, termo),
                conn=conn,
            )
            if row:
                return row["id"]
        if self._usuario_padrao_id:
            return self._usuario_padrao_id
        raise RuntimeError("Nenhum usuário conferente cadastrado na tabela 'usuario'.")

    # ------------------------------------------------------------------
    # Contexto Comercial e Base Legal (RF-02 / RNF-01)
    # ------------------------------------------------------------------
    def listar_clientes(self) -> list[str]:
        self._garantir_catalogo()
        return list(self._clientes)

    def listar_propostas(self, cliente: str) -> list[str]:
        self._garantir_catalogo()
        return list(self._propostas_por_cliente.get(cliente, {}).keys())

    def listar_locais(self, cliente: str, proposta: str) -> list[str]:
        self._garantir_catalogo()
        return list(self._locais_por_cliente_proposta.get((cliente, proposta), []))

    def listar_locais_por_cliente(self, cliente: str) -> list[str]:
        self._garantir_catalogo()
        return list(self._locais_por_cliente.get(cliente, []))

    def obter_contexto_padrao_proposta(self, cliente: str, proposta: str) -> dict:
        """
        Deriva a Origem da Amostra e as normas iniciais (1 a 3) a partir de
        `proposta_legislacao` da proposta selecionada (RF-02).
        """
        self._garantir_catalogo()
        meta_prop = self._propostas_por_cliente.get(cliente, {}).get(proposta)
        nomes_legs = meta_prop["legislacoes_nomes"] if meta_prop else []
        siglas_prop = [_sigla_legislacao(nm) for nm in nomes_legs]

        # Escolhe origem compatível com o maior número de legislações vinculadas à proposta
        melhor_origem = self._origens[0] if self._origens else "Água Tratada"
        preferencia_origens = [
            "Efluente Tratado",
            "Água Superficial (Água doce)",
            "Água Tratada",
            "Água Bruta (Captação/Subterrânea)",
            "Água de Consumo Humano",
        ]
        origens_cadastradas_set = set(self._origens)
        preferencia_set = set(preferencia_origens)
        origens_ordenadas = [o for o in preferencia_origens if o in origens_cadastradas_set] + [
            o for o in self._origens if o not in preferencia_set
        ]

        melhor_score = -1
        for orig in origens_ordenadas:
            legs_orig = {m["sigla"] for m in self.listar_legislacoes_por_origem(orig)}
            score = sum(1 for s in siglas_prop if s in legs_orig)
            if score > melhor_score:
                melhor_score = score
                melhor_origem = orig

        legs_disp = {m["sigla"]: m for m in self.listar_legislacoes_por_origem(melhor_origem)}
        normas_ini: list[dict[str, Optional[str]]] = []

        for s in siglas_prop:
            if s not in legs_disp:
                continue
            classes = self.listar_classes_legislacao(s, melhor_origem)
            if not classes:
                normas_ini.append({"sigla": s, "classe": None})
            elif s == "CONAMA 430" and len(siglas_prop) == 1:
                for cl in classes[:2]:
                    normas_ini.append({"sigla": s, "classe": cl})
            else:
                normas_ini.append({"sigla": s, "classe": classes[0]})
            if len(normas_ini) >= 3:
                break

        if not normas_ini and legs_disp:
            m0 = next(iter(legs_disp.values()))
            cl0 = m0["classes"][0] if m0["classes"] else None
            normas_ini.append({"sigla": m0["sigla"], "classe": cl0})

        return {"origem": melhor_origem, "normas": normas_ini[:3]}

    def listar_origens(self) -> list[str]:
        self._garantir_catalogo()
        return list(self._origens)

    def listar_legislacoes_por_origem(self, origem: str) -> list[dict]:
        self._garantir_catalogo()
        saida: list[dict] = []
        for sigla, meta in self._leg_meta_por_sigla.items():
            if origem in meta["origens"]:
                classes_orig = list(meta["classes_por_origem"].get(origem, meta["classes"]))
                saida.append(
                    {
                        "sigla": sigla,
                        "nome_completo": meta["nome_completo"],
                        "origens": list(meta["origens"]),
                        "classes": classes_orig,
                    }
                )
        return saida

    def listar_classes_legislacao(self, sigla: str, origem: Optional[str] = None) -> list[str]:
        self._garantir_catalogo()
        meta = self._leg_meta_por_sigla.get(sigla)
        if not meta:
            return []
        if origem and origem in meta["classes_por_origem"]:
            return list(meta["classes_por_origem"][origem])
        return list(meta["classes"])

    # ------------------------------------------------------------------
    # Helpers internos de resolução de Normas / Parâmetros VMP
    # ------------------------------------------------------------------
    def _coletar_referencias_vmp(
        self,
        origem: Optional[str],
        normas_selecionadas: Optional[list[tuple[str, Optional[str]]]],
    ) -> tuple[set[int], dict[int, list[str]], dict[int, set[str]]]:
        """Monta conjuntos (codigos_com_vmp, unidades_vmp_por_ensaio, operadores_por_ensaio) das normas ativas."""
        self._garantir_catalogo()
        codigos_com_vmp: set[int] = set()
        unidades_por_ensaio_dict: dict[int, dict[str, None]] = defaultdict(dict)
        operadores_por_ensaio: dict[int, set[str]] = defaultdict(set)

        if origem and normas_selecionadas:
            for sigla, classe_ui in normas_selecionadas:
                meta = self._leg_meta_por_sigla.get(sigla)
                if not meta:
                    continue
                possui_cl = self._possui_classes_por_leg_origem.get(
                    (meta["nome_completo"], origem), bool(meta["possui_classes"])
                )
                classe_db = _classe_para_db(classe_ui, possui_cl)
                mapa = self._parametros_por_contexto.get((origem, sigla, classe_db), {})
                for cod, (_, param) in mapa.items():
                    codigos_com_vmp.add(cod)
                    unidades_por_ensaio_dict[cod][param.unidade] = None
                    operadores_por_ensaio[cod].add(param.operador)
        else:
            for mapa in self._parametros_por_contexto.values():
                for cod, (_, param) in mapa.items():
                    codigos_com_vmp.add(cod)
                    unidades_por_ensaio_dict[cod][param.unidade] = None
                    operadores_por_ensaio[cod].add(param.operador)

        unidades_por_ensaio = {
            cod: list(unids_unicas.keys())
            for cod, unids_unicas in unidades_por_ensaio_dict.items()
        }
        return codigos_com_vmp, unidades_por_ensaio, dict(operadores_por_ensaio)

    def _construir_norma_aplicada(
        self, sigla: str, origem: str, classe_ui: Optional[str]
    ) -> tuple[NormaAplicada, Optional[str]]:
        meta = self._leg_meta_por_sigla.get(sigla)
        if not meta:
            raise ValueError(f"Legislação '{sigla}' não encontrada no catálogo.")
        possui_cl = self._possui_classes_por_leg_origem.get(
            (meta["nome_completo"], origem), bool(meta["possui_classes"])
        )
        classe_db = _classe_para_db(classe_ui, possui_cl)
        classe_can = _classe_canonica_norma(classe_db, possui_cl)
        norma = NormaAplicada(
            id=_norma_id(sigla, classe_can),
            sigla=sigla,
            nome_completo=meta["nome_completo"],
            origem=origem,
            classe=classe_can,
        )
        return norma, classe_db

    # ------------------------------------------------------------------
    # Pré-leitura e Importação UltraLIMS (RF-03 / RF-04 / CT-10 / CT-11)
    # ------------------------------------------------------------------
    def analisar_planilha(
        self,
        arquivo_bytes: bytes,
        nome_arquivo: str,
        origem: Optional[str] = None,
        normas_selecionadas: Optional[list[tuple[str, Optional[str]]]] = None,
    ) -> ResultadoPreLeituraLote:
        self._garantir_catalogo()
        codigos_existentes = {
            r["codigo_amostra"]
            for r in consultar_lista(obter_query("amostras", "listar_codigos_amostras"))
            if r.get("codigo_amostra")
        }
        cods_vmp, unids_vmp, ops_vmp = self._coletar_referencias_vmp(origem, normas_selecionadas)
        return analisar_lote_ultralims(
            arquivo_bytes=arquivo_bytes,
            nome_arquivo=nome_arquivo,
            catalogo_ensaios=self._ensaios_por_id_num,
            unidades_vmp_referencia=unids_vmp,
            codigos_com_vmp=cods_vmp,
            codigos_existentes=codigos_existentes,
            operadores_vmp_referencia=ops_vmp,
        )

    def recalcular_lote(
        self,
        lote: ResultadoPreLeituraLote,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> ResultadoPreLeituraLote:
        self._garantir_catalogo()
        cods_vmp, unids_vmp, ops_vmp = self._coletar_referencias_vmp(origem, normas_selecionadas)
        return recalcular_lote_por_normas(
            lote=lote,
            catalogo_ensaios=self._ensaios_por_id_num,
            codigos_com_vmp=cods_vmp,
            unidades_vmp_por_ensaio=unids_vmp,
            operadores_por_ensaio=ops_vmp,
        )

    def _persistir_amostra_em_transacao(
        self,
        conn: psycopg.Connection,
        pre_leitura: ResultadoPreLeitura,
        local_id: str,
        origem: str,
        origem_id: str,
        usuario_id: str,
        lab_id: Optional[str],
        normas_selecionadas: list[tuple[str, Optional[str]]],
    ) -> str:
        codigo = pre_leitura.codigo_amostra_principal.strip()
        existente = consultar_um(
            obter_query("amostras", "buscar_amostra_base_por_codigo"),
            (codigo,),
            conn=conn,
        )
        if existente is not None:
            raise ValueError(
                f"A amostra '{codigo}' já está cadastrada no banco de dados (RNF-03 / CT-11)."
            )

        normas_resolvidas = [
            self._construir_norma_aplicada(sigla, origem, cl)
            for sigla, cl in normas_selecionadas
        ]

        am_row = consultar_um(
            obter_query("amostras", "inserir_amostra"),
            (
                codigo,
                pre_leitura.codigo_externo,
                pre_leitura.data_coleta,
                pre_leitura.data_conclusao,
                None,
                None,
                local_id,
                origem_id,
                usuario_id,
                lab_id,
            ),
            conn=conn,
        )
        if not am_row:
            raise RuntimeError(f"Falha ao inserir amostra '{codigo}'.")
        amostra_id = am_row["id"]

        data_analise_ts = (
            datetime.combine(pre_leitura.data_conclusao, datetime.min.time())
            if pre_leitura.data_conclusao
            else datetime.combine(pre_leitura.data_coleta, datetime.min.time())
        )

        # Persiste TODOS os ensaios mapeados no catálogo (inclusive sem VMP, para histórico RN-08)
        for id_num, bruto in pre_leitura.valores_brutos.items():
            ensaio_uuid = self._ensaios_uuid_por_id_num.get(id_num)
            meta_e = self._ensaios_por_id_num.get(id_num)
            if not ensaio_uuid or not meta_e:
                continue

            tipo_val, qual, val_num = interpretar_valor_bruto(bruto)
            if tipo_val == "ignorado":
                continue

            ra_row = consultar_um(
                obter_query("amostras", "inserir_resultado_amostra"),
                (amostra_id, ensaio_uuid, bruto, val_num, qual, data_analise_ts),
                conn=conn,
            )
            if not ra_row:
                continue
            resultado_id = ra_row["id"]

            for norma_obj, classe_db in normas_resolvidas:
                mapa_params = self._parametros_por_contexto.get(
                    (origem, norma_obj.sigla, classe_db), {}
                )
                par_entry = mapa_params.get(id_num)
                if not par_entry:
                    continue
                param_uuid, param_obj = par_entry
                conf, _ = avaliar_parametro(
                    valor_bruto=bruto,
                    tipo_avaliacao=meta_e["tipo"],
                    unidade_ensaio=meta_e["unidade"],
                    parametro=param_obj,
                )
                executar_sql(
                    obter_query("conferencia", "inserir_analise_conformidade"),
                    (resultado_id, param_uuid, conf, None),
                    conn=conn,
                )

        # Hidrata na própria transação para calcular status geral 100% derivado e minuta automática (RN-07)
        am_hidratada = self._hidratar_amostra_unica(codigo, conn=conn)
        if not am_hidratada:
            raise RuntimeError(f"Falha ao hidratar amostra recém-importada '{codigo}'.")

        status_derivado = calcular_status_geral(am_hidratada.ensaios) if am_hidratada.ensaios else GERAL_PENDENTE
        am_hidratada.status_geral = status_derivado  # type: ignore[assignment]
        minuta = gerar_parecer_automatico(am_hidratada)

        executar_sql(
            obter_query("conferencia", "atualizar_conclusao_amostra"),
            (_status_geral_para_bool(status_derivado), minuta, amostra_id),
            conn=conn,
        )
        return codigo

    def criar_amostra_importada(
        self,
        pre_leitura: ResultadoPreLeitura,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
        usuario: Optional[str] = None,
    ) -> Amostra:
        criadas = self.criar_lote_importado(
            lote=ResultadoPreLeituraLote(nome_arquivo=pre_leitura.nome_arquivo, amostras=[pre_leitura]),
            cliente=cliente,
            proposta=proposta,
            local_coleta=local_coleta,
            origem=origem,
            normas_selecionadas=normas_selecionadas,
            usuario=usuario,
        )
        return criadas[0]

    def criar_lote_importado(
        self,
        lote: ResultadoPreLeituraLote,
        cliente: str,
        proposta: str,
        local_coleta: str,
        origem: str,
        normas_selecionadas: list[tuple[str, Optional[str]]],
        usuario: Optional[str] = None,
    ) -> list[Amostra]:
        self._garantir_catalogo()
        if not lote.amostras:
            raise ValueError("Nenhuma amostra presente no lote para importação.")
        if not (1 <= len(normas_selecionadas) <= 3):
            raise ValueError("Selecione de 1 a 3 normas aplicáveis antes de confirmar.")

        codigos_lote = [a.codigo_amostra_principal.strip() for a in lote.amostras]
        if len(codigos_lote) != len(set(codigos_lote)):
            raise ValueError("O lote contém códigos de amostra repetidos no mesmo arquivo (CT-11).")

        local_id = self._locais_id_por_nome.get(local_coleta)
        if not local_id:
            raise ValueError(f"Local de coleta '{local_coleta}' não encontrado no cadastro.")
        origem_id = self._origens_id_por_nome.get(origem)
        if not origem_id:
            raise ValueError(f"Origem '{origem}' não encontrada no cadastro.")

        with transaction() as conn:
            usuario_id = self._resolver_usuario_id(usuario, conn=conn)
            for pre in lote.amostras:
                self._persistir_amostra_em_transacao(
                    conn=conn,
                    pre_leitura=pre,
                    local_id=local_id,
                    origem=origem,
                    origem_id=origem_id,
                    usuario_id=usuario_id,
                    lab_id=self._laboratorio_padrao_id,
                    normas_selecionadas=normas_selecionadas,
                )

        saida: list[Amostra] = []
        for cod in codigos_lote:
            am = self.obter_amostra(cod)
            if am:
                saida.append(am)

        # Entrega o lote ordenado pela Fila de Prioridade (heapq):
        # 1º Não favorável -> 2º Pendente -> 3º Favorável
        return ordenar_lote_por_prioridade(saida)

    def excluir_amostra(self, codigo: str) -> int:
        """Remove transacionalmente uma amostra e suas análises/resultados (útil para limpeza de testes)."""
        with transaction() as conn:
            executar_sql(obter_query("amostras", "excluir_analises_por_codigo_amostra"), (codigo,), conn=conn)
            executar_sql(obter_query("amostras", "excluir_resultados_por_codigo_amostra"), (codigo,), conn=conn)
            return executar_sql(obter_query("amostras", "excluir_amostra_por_codigo"), (codigo,), conn=conn)

    # ------------------------------------------------------------------
    # Hidratação Normalizada de Amostras, Séries Históricas e Logs
    # ------------------------------------------------------------------
    def _montar_pontos_serie(
        self,
        registros_anteriores: list[dict[str, Any]],
        amostra_codigo: str,
        amostra_data: date,
        valor_bruto_atual: str,
        valor_num_atual: Optional[float],
        qual_atual: Optional[str],
        operador_ref: str,
    ) -> list[PontoHistorico]:
        data_corte = _subtrair_meses(amostra_data, JANELA_MESES)
        validos_ant = [
            r
            for r in registros_anteriores
            if r["codigo_amostra"] != amostra_codigo
            and r["data_coleta"] is not None
            and data_corte <= r["data_coleta"] < amostra_data
        ]
        validos_ant.sort(key=lambda r: (r["data_coleta"], r["codigo_amostra"]))

        # Fila Circular de tamanho fixo (maxlen = 6) para manter apenas as últimas
        # 6 coletas anteriores em memória constante O(1)
        janela_circular: deque[dict[str, Any]] = deque(maxlen=MAX_RESULTADOS_HISTORICO)
        for registro_ant in validos_ant:
            janela_circular.append(registro_ant)
        recorte_ant = list(janela_circular)

        # Se duas coletas caem no mesmo mês/ano, inclui o dia no rótulo para não colidir no eixo X
        contagem_mes: dict[tuple[int, int], int] = defaultdict(int)
        for r in recorte_ant:
            dt = r["data_coleta"]
            contagem_mes[(dt.year, dt.month)] += 1
        contagem_mes[(amostra_data.year, amostra_data.month)] += 1

        pontos: list[PontoHistorico] = []
        for r in recorte_ant:
            dt: date = r["data_coleta"]
            v_num = float(r["valor_numerico"]) if r["valor_numerico"] is not None else None
            if v_num is None and operador_ref != "AUSENCIA" and str(r["valor_bruto"]).strip().lower() == "ausente":
                v_num = 0.0
            usar_dia = contagem_mes[(dt.year, dt.month)] > 1
            pontos.append(
                PontoHistorico(
                    data_coleta=dt,
                    rotulo_mes=_rotulo_mes(dt, incluir_dia=usar_dia),
                    codigo_amostra=r["codigo_amostra"],
                    valor_bruto=r["valor_bruto"],
                    valor_numerico=v_num,
                    qualificador=r["qualificador"] if r["qualificador"] in ("<", ">") else None,
                    is_atual=False,
                )
            )

        v_atual_ef = valor_num_atual
        if v_atual_ef is None and operador_ref != "AUSENCIA" and valor_bruto_atual.strip().lower() == "ausente":
            v_atual_ef = 0.0
        usar_dia_atual = contagem_mes[(amostra_data.year, amostra_data.month)] > 1
        pontos.append(
            PontoHistorico(
                data_coleta=amostra_data,
                rotulo_mes=f"{_rotulo_mes(amostra_data, incluir_dia=usar_dia_atual)} Atual",
                codigo_amostra=amostra_codigo,
                valor_bruto=valor_bruto_atual,
                valor_numerico=v_atual_ef,
                qualificador=qual_atual if qual_atual in ("<", ">") else None,  # type: ignore[arg-type]
                is_atual=True,
            )
        )
        return pontos

    def _construir_objeto_amostra(
        self,
        base_row: dict[str, Any],
        res_rows: list[dict[str, Any]],
        historico_por_ensaio: dict[int, list[dict[str, Any]]],
        logs_rows: list[dict[str, Any]],
    ) -> Amostra:
        self._garantir_catalogo()
        origem_amostra = base_row["origem_nome"]
        proposta_rotulo = (
            self._rotulo_proposta_por_id.get(base_row["proposta_id"], "Proposta vinculada")
            if base_row.get("proposta_id")
            else "Proposta não vinculada"
        )

        # 1. Descobre as normas distintas avaliadas na amostra (via analise_conformidade)
        normas_map: dict[str, NormaAplicada] = {}
        ensaios_agrupados: dict[int, dict[str, Any]] = {}
        tem_alguma_avaliacao = False

        for r in res_rows:
            cod = int(r["id_num"])
            entry = ensaios_agrupados.setdefault(
                cod,
                {
                    "codigo": cod,
                    "nome": r["ensaio_nome"],
                    "valor_bruto": r["valor_bruto"],
                    "valor_numerico": float(r["valor_numerico"]) if r["valor_numerico"] is not None else None,
                    "qualificador": r["qualificador"] if r["qualificador"] in ("<", ">") else None,
                    "unidade_trabalho": r["unidade_ensaio"] or "",
                    "tipo_avaliacao": (
                        "MANUAL_TECNICA" if r["tipo_avaliacao"] == "MANUAL_TECNICA" else "AUTOMATICA"
                    ),
                    "avaliacoes": {},
                    "observacao": "",
                },
            )

            if r["parametro_id"] is not None and r["legislacao_nome"] is not None:
                tem_alguma_avaliacao = True
                nome_leg = r["legislacao_nome"]
                sigla = self._sigla_por_nome_leg.get(nome_leg, _sigla_legislacao(nome_leg))
                orig_p = r["origem_parametro"] or origem_amostra
                possui_cl = self._possui_classes_por_leg_origem.get((nome_leg, orig_p), bool(r["classe_nome"]))
                classe_can = _classe_canonica_norma(r["classe_nome"], possui_cl)
                nid = _norma_id(sigla, classe_can)

                if nid not in normas_map:
                    normas_map[nid] = NormaAplicada(
                        id=nid,
                        sigla=sigla,
                        nome_completo=nome_leg,
                        origem=origem_amostra,
                        classe=classe_can,
                    )
                norma_obj = normas_map[nid]

                op_str = (r["operador"] or "MANUAL").strip().upper()
                vmin = float(r["valor_min"]) if r["valor_min"] is not None else None
                vmax = float(r["valor_max"]) if r["valor_max"] is not None else None
                p_temp = ParametroNorma(
                    norma_id=nid,
                    norma_sigla=sigla,
                    norma_nome_completo=nome_leg,
                    classe_nome=classe_can,
                    operador=op_str if op_str in ("MENOR_IGUAL", "MENOR_ESTRITO", "MAIOR_IGUAL", "FAIXA", "AUSENCIA", "MANUAL") else "MANUAL",  # type: ignore[arg-type]
                    valor_min=vmin,
                    valor_max=vmax,
                    valor_esperado=r["valor_esperado"],
                    unidade=r["unidade_parametro"] or "",
                )
                _, motivo_motor = avaliar_parametro(
                    valor_bruto=r["valor_bruto"],
                    tipo_avaliacao=entry["tipo_avaliacao"],
                    unidade_ensaio=entry["unidade_trabalho"],
                    parametro=p_temp,
                )

                entry["avaliacoes"][nid] = AvaliacaoNorma(
                    norma_id=nid,
                    norma_titulo=norma_obj.titulo_coluna,
                    norma_nome_parecer=norma_obj.nome_parecer,
                    vmp_texto=formatar_vmp_texto(p_temp),
                    vmp_numerico_ref=_vmp_ref_numerico(op_str, vmin, vmax),
                    vmp_min=vmin,
                    vmp_max=vmax,
                    operador=op_str,
                    conformidade=r["conformidade"],  # estado persistido no banco
                    motivo=motivo_motor,
                )
                if r["observacao"] and not entry["observacao"]:
                    entry["observacao"] = r["observacao"]

        normas_lista = list(normas_map.values())
        ensaios_out: list[EnsaioResultado] = []
        dt_coleta = base_row["data_coleta"] or date.today()

        for cod, entry in ensaios_agrupados.items():
            # Ensaios sem VMP ficam gravados em resultado_amostra para histórico (RF-03/RN-08),
            # enquanto a tabela regulatória exibe os ensaios avaliados nas normas selecionadas.
            if tem_alguma_avaliacao and not entry["avaliacoes"]:
                continue

            avs_list = list(entry["avaliacoes"].values())
            status_cons = consolidar_status_ensaio(avs_list) if avs_list else STATUS_PENDENTE
            op_estat = avs_list[0].operador if avs_list else "MENOR_IGUAL"

            pontos_hist = self._montar_pontos_serie(
                registros_anteriores=historico_por_ensaio.get(cod, []),
                amostra_codigo=base_row["codigo_amostra"],
                amostra_data=dt_coleta,
                valor_bruto_atual=entry["valor_bruto"],
                valor_num_atual=entry["valor_numerico"],
                qual_atual=entry["qualificador"],
                operador_ref=op_estat,
            )

            v_atual_calc = entry["valor_numerico"]
            if v_atual_calc is None and op_estat != "AUSENCIA" and entry["valor_bruto"].strip().lower() == "ausente":
                v_atual_calc = 0.0

            stats = calcular_estatistica_historica(
                pontos=pontos_hist,
                valor_atual=v_atual_calc,
                qualificador_atual=entry["qualificador"],
                operador=op_estat,
                status_conformidade=status_cons,
                data_referencia=dt_coleta,
            )

            ensaio_obj = EnsaioResultado(
                codigo=cod,
                nome=entry["nome"],
                valor_bruto=entry["valor_bruto"],
                valor_numerico=entry["valor_numerico"],
                qualificador=entry["qualificador"],
                unidade_trabalho=entry["unidade_trabalho"],
                tipo_avaliacao=entry["tipo_avaliacao"],
                avaliacoes=entry["avaliacoes"],
                status=status_cons,  # type: ignore[arg-type]
                observacao=entry["observacao"],
                historico=pontos_hist,
                estatistica=stats,
            )
            sinal, sinal_tipo = definir_sinalizacao_ensaio(ensaio_obj)
            ensaio_obj.sinalizacao = sinal
            ensaio_obj.sinalizacao_tipo = sinal_tipo  # type: ignore[arg-type]
            ensaios_out.append(ensaio_obj)

        # Histórico de auditoria RN-10 modelado como Pilha (LIFO) via deque.appendleft() em O(1)
        logs_out = _construir_pilha_logs_auditoria(logs_rows)

        status_geral_str = (
            calcular_status_geral(ensaios_out)
            if ensaios_out
            else _status_bool_para_geral(base_row["status"])
        )

        amostra = Amostra(
            codigo=base_row["codigo_amostra"],
            data_coleta=dt_coleta,
            data_conclusao=base_row["data_conclusao"],
            cliente=base_row["cliente_nome"],
            proposta=proposta_rotulo,
            local_coleta=base_row["local_nome"],
            origem=origem_amostra,
            normas=normas_lista,
            ensaios=ensaios_out,
            status_geral=status_geral_str,  # type: ignore[arg-type]
            parecer="",
            logs=logs_out,
        )
        amostra.parecer = (base_row["descricao"] or "").strip() or gerar_parecer_automatico(amostra)
        return amostra

    def _hidratar_amostra_unica(
        self, codigo: str, conn: Optional[psycopg.Connection] = None
    ) -> Optional[Amostra]:
        base_row = consultar_um(
            obter_query("amostras", "buscar_amostra_base_por_codigo"),
            (codigo,),
            conn=conn,
        )
        if not base_row:
            return None

        am_id = base_row["amostra_id"]
        loc_id = base_row["local_id"]
        dt_col = base_row["data_coleta"] or date.today()

        res_rows = consultar_lista(
            obter_query("amostras", "listar_resultados_e_avaliacoes_amostra"),
            (am_id,),
            conn=conn,
        )
        hist_rows = consultar_lista(
            obter_query("amostras", "listar_serie_historica_local"),
            (loc_id, am_id, dt_col, dt_col, JANELA_MESES),
            conn=conn,
        )
        logs_rows = consultar_lista(
            obter_query("conferencia", "listar_logs_por_amostra"),
            (am_id,),
            conn=conn,
        )

        hist_por_ensaio: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for hr in hist_rows:
            hist_por_ensaio[int(hr["id_num"])].append(hr)

        return self._construir_objeto_amostra(base_row, res_rows, hist_por_ensaio, logs_rows)

    # ------------------------------------------------------------------
    # Painel (B2) e Conferência (B4 — RF-05 / RN-10 / CT-16)
    # ------------------------------------------------------------------
    def listar_amostras(
        self,
        status_filtro: str = "Todos",
        busca: str = "",
    ) -> list[Amostra]:
        """Hidrata em lote todas as amostras em apenas 2 round-trips SQL (zero N+1)."""
        self._garantir_catalogo()
        base_rows = consultar_lista(obter_query("amostras", "listar_amostras_base"))
        all_res_rows = consultar_lista(obter_query("amostras", "listar_resultados_e_avaliacoes_todas"))

        res_por_amostra: dict[str, list[dict[str, Any]]] = defaultdict(list)
        # Dedup por resultado_id para construir séries históricas por (local_id, id_num)
        vistos_ra: set[str] = set()
        serie_por_local_ensaio: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)

        for r in all_res_rows:
            res_por_amostra[r["amostra_id"]].append(r)
            rid = r["resultado_id"]
            if rid not in vistos_ra:
                vistos_ra.add(rid)
                serie_por_local_ensaio[(r["local_id"], int(r["id_num"]))].append(
                    {
                        "id_num": int(r["id_num"]),
                        "codigo_amostra": r["codigo_amostra"],
                        "data_coleta": r["data_coleta"],
                        "valor_bruto": r["valor_bruto"],
                        "valor_numerico": r["valor_numerico"],
                        "qualificador": r["qualificador"],
                    }
                )

        termo = busca.strip().lower()
        saida: list[Amostra] = []

        for b in base_rows:
            am_id = b["amostra_id"]
            loc_id = b["local_id"]
            linhas_am = res_por_amostra.get(am_id, [])
            cods_am = {int(x["id_num"]) for x in linhas_am}
            hist_map = {
                cod: serie_por_local_ensaio.get((loc_id, cod), [])
                for cod in cods_am
            }
            am_obj = self._construir_objeto_amostra(b, linhas_am, hist_map, [])

            if status_filtro in (GERAL_FAVORAVEL, GERAL_NAO_FAVORAVEL, GERAL_PENDENTE):
                if am_obj.status_geral != status_filtro:
                    continue
            if termo:
                haystack = (
                    f"{am_obj.codigo} {am_obj.cliente} {am_obj.local_coleta} {am_obj.normas_resumo}"
                ).lower()
                if termo not in haystack:
                    continue
            saida.append(am_obj)

        return saida

    def obter_amostra(self, codigo: str) -> Optional[Amostra]:
        self._garantir_catalogo()
        return self._hidratar_amostra_unica(codigo)

    def salvar_conferencia(
        self,
        codigo: str,
        edicoes_status: dict[int, str],
        edicoes_obs: dict[int, str],
        novo_parecer: str,
        usuario: str,
    ) -> tuple[Amostra, int]:
        """
        Persiste edições manuais de status/observação, recalcula o status geral 100% derivado,
        atualiza a minuta e grava a trilha de auditoria `log_alteracao` numa única transação (RN-10).
        """
        self._garantir_catalogo()
        agora = datetime.now()

        with transaction() as conn:
            atual = self._hidratar_amostra_unica(codigo, conn=conn)
            if not atual:
                raise ValueError(f"Amostra '{codigo}' não encontrada para conferência.")

            base_row = consultar_um(
                obter_query("amostras", "buscar_amostra_base_por_codigo"),
                (codigo,),
                conn=conn,
            )
            assert base_row is not None
            amostra_id = base_row["amostra_id"]
            usuario_id = self._resolver_usuario_id(usuario, conn=conn)

            status_geral_anterior = atual.status_geral
            parecer_anterior = atual.parecer
            qtd_logs = 0

            for ensaio in atual.ensaios:
                novo_st = edicoes_status.get(ensaio.codigo, ensaio.status)
                nova_obs = edicoes_obs.get(ensaio.codigo, ensaio.observacao).strip()
                obs_db = nova_obs[:255] if nova_obs else None

                st_mudou = novo_st != ensaio.status
                obs_mudou = nova_obs != (ensaio.observacao or "").strip()

                if not st_mudou and not obs_mudou:
                    continue

                ra_row = consultar_um(
                    obter_query("conferencia", "buscar_resultado_amostra_por_ensaio"),
                    (amostra_id, ensaio.codigo),
                    conn=conn,
                )
                ra_id = ra_row["resultado_id"] if ra_row else None

                if st_mudou:
                    executar_sql(
                        obter_query("conferencia", "atualizar_conformidade_e_observacao_ensaio"),
                        (_status_ensaio_para_bool(novo_st), obs_db, amostra_id, ensaio.codigo),
                        conn=conn,
                    )
                    executar_sql(
                        obter_query("conferencia", "inserir_log_alteracao"),
                        (
                            amostra_id,
                            ra_id,
                            usuario_id,
                            "conformidade",
                            ensaio.status,
                            novo_st,
                            nova_obs or None,
                            agora,
                        ),
                        conn=conn,
                    )
                    ensaio.status = novo_st  # type: ignore[assignment]
                    qtd_logs += 1
                elif obs_mudou:
                    executar_sql(
                        obter_query("conferencia", "atualizar_observacao_ensaio"),
                        (obs_db, amostra_id, ensaio.codigo),
                        conn=conn,
                    )
                    executar_sql(
                        obter_query("conferencia", "inserir_log_alteracao"),
                        (
                            amostra_id,
                            ra_id,
                            usuario_id,
                            "conformidade",
                            ensaio.status,
                            ensaio.status,
                            nova_obs or "(observação removida)",
                            agora,
                        ),
                        conn=conn,
                    )
                    qtd_logs += 1

                ensaio.observacao = nova_obs

            novo_status_geral = calcular_status_geral(atual.ensaios) if atual.ensaios else GERAL_PENDENTE
            if novo_status_geral != status_geral_anterior:
                executar_sql(
                    obter_query("conferencia", "inserir_log_alteracao"),
                    (
                        amostra_id,
                        None,
                        usuario_id,
                        "parecer_geral",
                        status_geral_anterior,
                        novo_status_geral,
                        None,
                        agora,
                    ),
                    conn=conn,
                )
                qtd_logs += 1

            parecer_limpo = (novo_parecer or "").strip()
            if not parecer_limpo:
                atual.status_geral = novo_status_geral  # type: ignore[assignment]
                parecer_limpo = gerar_parecer_automatico(atual)

            if parecer_limpo != parecer_anterior.strip():
                executar_sql(
                    obter_query("conferencia", "inserir_log_alteracao"),
                    (
                        amostra_id,
                        None,
                        usuario_id,
                        "minuta",
                        parecer_anterior,
                        parecer_limpo,
                        None,
                        agora,
                    ),
                    conn=conn,
                )
                qtd_logs += 1

            executar_sql(
                obter_query("conferencia", "atualizar_conclusao_amostra"),
                (_status_geral_para_bool(novo_status_geral), parecer_limpo, amostra_id),
                conn=conn,
            )

            amostra_pos = self._hidratar_amostra_unica(codigo, conn=conn)
            assert amostra_pos is not None
            return amostra_pos, qtd_logs

    # ------------------------------------------------------------------
    # Tela B5 — Análise por Local de Coleta (RF-06)
    # ------------------------------------------------------------------
    def _resolver_norma_label_local(self, norma_label: str) -> Optional[tuple[str, Optional[str], str]]:
        """Converte `'CONAMA 357 — Classe 1'` ou `'GM/MS 888'` em `(legislacao_nome, classe_db, sigla)`."""
        self._garantir_catalogo()
        if not norma_label:
            return None
        if "—" in norma_label:
            partes = [p.strip() for p in norma_label.split("—", 1)]
            sigla, classe_txt = partes[0], partes[1]
        else:
            sigla, classe_txt = norma_label.strip(), None

        meta = self._leg_meta_por_sigla.get(sigla)
        if not meta:
            return None
        classe_db = _classe_para_db(classe_txt, bool(meta["possui_classes"]))
        return meta["nome_completo"], classe_db, sigla

    def listar_normas_do_local(self, cliente: str, local_coleta: str) -> list[str]:
        self._garantir_catalogo()
        if not local_coleta:
            return []
        rows = consultar_lista(
            obter_query("analise_local", "listar_normas_avaliadas_no_local"),
            (local_coleta,),
        )
        # Deduplicação em O(n) preservando a ordem com dict de chaves únicas
        rotulos_unicos: dict[str, None] = {}
        for r in rows:
            sigla = self._sigla_por_nome_leg.get(r["legislacao_nome"], _sigla_legislacao(r["legislacao_nome"]))
            possui_cl = bool(r["possui_classes"])
            classe_can = _classe_canonica_norma(r["classe_nome"], possui_cl)
            rot = f"{sigla} — {classe_can}" if classe_can else sigla
            rotulos_unicos[rot] = None

        if rotulos_unicos:
            return list(rotulos_unicos.keys())

        # Fallback: normas vinculadas à proposta comercial do local (quando local ainda não tem amostras)
        for (cli, rot_prop), locais in self._locais_por_cliente_proposta.items():
            if cli == cliente and local_coleta in locais:
                meta_prop = self._propostas_por_cliente.get(cli, {}).get(rot_prop, {})
                for nome_leg in meta_prop.get("legislacoes_nomes", []):
                    sigla = _sigla_legislacao(nome_leg)
                    meta_l = self._leg_meta_por_sigla.get(sigla)
                    if not meta_l:
                        continue
                    if meta_l["classes"]:
                        for cl_ui in meta_l["classes"]:
                            cl_can = _limpar_rotulo_classe(cl_ui)
                            rot = f"{sigla} — {cl_can}" if cl_can else sigla
                            rotulos_unicos[rot] = None
                    else:
                        rotulos_unicos[sigla] = None
        return list(rotulos_unicos.keys())

    def obter_evolucao_mensal_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[MesConformidadeLocal]:
        self._garantir_catalogo()
        resolvido = self._resolver_norma_label_local(norma_label)
        if not local_coleta or not resolvido:
            return []
        leg_nome, classe_db, _ = resolvido

        ref_row = consultar_um(obter_query("analise_local", "buscar_data_referencia_local"), (local_coleta,))
        data_ref: date = ref_row["data_ref"] if ref_row and ref_row.get("data_ref") else date.today()

        rows = consultar_lista(
            obter_query("analise_local", "listar_evolucao_amostras_local"),
            (local_coleta, data_ref, periodo_meses, leg_nome, classe_db, leg_nome, classe_db),
        )
        if not rows:
            return []

        # Constrói os buckets mensais do período encerrado em data_ref
        chaves_meses: list[tuple[int, int]] = []
        ano_cur, mes_cur = data_ref.year, data_ref.month
        for offset in range(max(1, periodo_meses) - 1, -1, -1):
            a = ano_cur
            m = mes_cur - offset
            while m <= 0:
                m += 12
                a -= 1
            chaves_meses.append((a, m))

        contadores: dict[tuple[int, int], list[int]] = {k: [0, 0, 0] for k in chaves_meses}
        for r in rows:
            dt: Optional[date] = r["data_coleta"]
            if not dt:
                continue
            k_mes = (dt.year, dt.month)
            if k_mes not in contadores:
                contadores[k_mes] = [0, 0, 0]
                chaves_meses.append(k_mes)
            st = r["status_na_norma"]
            if st is True:
                contadores[k_mes][0] += 1
            elif st is None:
                contadores[k_mes][1] += 1
            else:
                contadores[k_mes][2] += 1

        chaves_ordenadas = sorted(set(chaves_meses))[-max(1, periodo_meses) :]
        saida: list[MesConformidadeLocal] = []
        for idx, (a, m) in enumerate(chaves_ordenadas):
            fav, pend, nfav = contadores[(a, m)]
            saida.append(
                MesConformidadeLocal(
                    rotulo_mes=f"{_MESES_PT[m]}/{str(a)[-2:]}",
                    favoraveis=fav,
                    pendentes=pend,
                    nao_favoraveis=nfav,
                    is_atual=(idx == len(chaves_ordenadas) - 1),
                )
            )
        return saida

    def obter_tabela_dinamica_local(
        self,
        cliente: str,
        local_coleta: str,
        norma_label: str,
        periodo_meses: int = 6,
    ) -> list[GrupoEnsaioLocal]:
        self._garantir_catalogo()
        resolvido = self._resolver_norma_label_local(norma_label)
        if not local_coleta or not resolvido:
            return []
        leg_nome, classe_db, sigla = resolvido
        possui_cl = bool(self._leg_meta_por_sigla[sigla]["possui_classes"])
        classe_can = _classe_canonica_norma(classe_db, possui_cl)

        ref_row = consultar_um(obter_query("analise_local", "buscar_data_referencia_local"), (local_coleta,))
        data_ref: date = ref_row["data_ref"] if ref_row and ref_row.get("data_ref") else date.today()

        rows = consultar_lista(
            obter_query("analise_local", "listar_resultados_local_por_norma"),
            (local_coleta, data_ref, periodo_meses, leg_nome, classe_db),
        )
        if not rows:
            return []

        por_ensaio: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            por_ensaio[int(r["id_num"])].append(r)

        grupos: list[GrupoEnsaioLocal] = []
        vmp_pref = f"VMP {classe_can or sigla}"

        for cod, lista_rows in por_ensaio.items():
            # lista_rows vem em ordem DESC de data_coleta (mais recente primeiro)
            r0 = lista_rows[0]
            nome_ensaio = r0["ensaio_nome"]
            unid_ensaio = r0["unidade_ensaio"] or ""
            tipo_av = "MANUAL_TECNICA" if r0["tipo_avaliacao"] == "MANUAL_TECNICA" else "AUTOMATICA"
            op_str = (r0["operador"] or "MANUAL").strip().upper()
            vmin = float(r0["valor_min"]) if r0["valor_min"] is not None else None
            vmax = float(r0["valor_max"]) if r0["valor_max"] is not None else None
            p_norma = ParametroNorma(
                norma_id=_norma_id(sigla, classe_can),
                norma_sigla=sigla,
                norma_nome_completo=leg_nome,
                classe_nome=classe_can,
                operador=op_str if op_str in ("MENOR_IGUAL", "MENOR_ESTRITO", "MAIOR_IGUAL", "FAIXA", "AUSENCIA", "MANUAL") else "MANUAL",  # type: ignore[arg-type]
                valor_min=vmin,
                valor_max=vmax,
                valor_esperado=r0["valor_esperado"],
                unidade=r0["unidade_parametro"] or "",
            )
            vmp_txt = formatar_vmp_texto(p_norma)

            # Ordem cronológica para checar desvio estatístico de cada coleta contra suas anteriores
            cronologicos = list(reversed(lista_rows))
            coletas_out: list[ColetaEnsaioLocal] = []
            nums_exatos: list[float] = []
            qtd_ok = qtd_nc = qtd_pend = qtd_desv = 0

            for r in lista_rows:
                dt_c: date = r["data_coleta"]
                v_num = float(r["valor_numerico"]) if r["valor_numerico"] is not None else None
                qual = r["qualificador"]
                conf = r["conformidade"]
                _, motivo_motor = avaliar_parametro(r["valor_bruto"], tipo_av, unid_ensaio, p_norma)

                if v_num is not None and qual != "<":
                    nums_exatos.append(v_num)

                # Avalia desvio histórico frente às coletas anteriores disponíveis no período
                pts_ant = [
                    PontoHistorico(
                        data_coleta=ant["data_coleta"],
                        rotulo_mes=_rotulo_mes(ant["data_coleta"]),
                        codigo_amostra=ant["codigo_amostra"],
                        valor_bruto=ant["valor_bruto"],
                        valor_numerico=float(ant["valor_numerico"]) if ant["valor_numerico"] is not None else None,
                        qualificador=ant["qualificador"] if ant["qualificador"] in ("<", ">") else None,
                        is_atual=False,
                    )
                    for ant in cronologicos
                    if ant["data_coleta"] < dt_c
                ]
                stats_ponto = calcular_estatistica_historica(
                    pontos=pts_ant,
                    valor_atual=v_num,
                    qualificador_atual=qual,
                    operador=op_str,
                    status_conformidade=_status_bool_para_ensaio(conf),
                    data_referencia=dt_c,
                )

                if conf is False:
                    qtd_nc += 1
                    b_txt, b_var = "NÃO CONFORME", "solid-red"
                elif conf is None:
                    qtd_pend += 1
                    if motivo_motor == "UNIDADE_DIVERGENTE":
                        b_txt = "UNID. DIVERGENTE"
                    elif qual == "<":
                        b_txt = "PENDENTE (<LQ)"
                    else:
                        b_txt = "PENDENTE"
                    b_var = "outline-gray"
                else:
                    qtd_ok += 1
                    if stats_ponto.alerta_desvio:
                        qtd_desv += 1
                        if op_str == "MAIOR_IGUAL":
                            b_txt = "DESVIO < μ−0,20σ"
                        elif op_str == "FAIXA":
                            b_txt = "DESVIO μ±0,20σ"
                        else:
                            b_txt = "DESVIO > μ+0,20σ"
                        b_var = "outline-amber"
                    else:
                        b_txt, b_var = "CONFORME", "outline-green"

                coletas_out.append(
                    ColetaEnsaioLocal(
                        codigo_amostra=r["codigo_amostra"],
                        data_coleta=dt_c,
                        valor_bruto=r["valor_bruto"],
                        unidade=unid_ensaio,
                        vmp_prefixo=vmp_pref,
                        vmp_texto=vmp_txt,
                        badge_texto=b_txt,
                        badge_variant=b_var,  # type: ignore[arg-type]
                    )
                )

            total = len(coletas_out)
            pct = f"{(qtd_ok / total * 100):.1f}%".replace(".", ",") if total else "—"
            media_str = (
                f"{formatar_numero_br(sum(nums_exatos) / len(nums_exatos), 2)} {unid_ensaio}".strip()
                if nums_exatos
                else "Qualitativo"
            )
            notas: list[str] = []
            if qtd_pend:
                notas.append(f"{qtd_pend} Pendente" + ("s" if qtd_pend > 1 else ""))
            if qtd_desv:
                notas.append(f"{qtd_desv} Desvio" + ("s" if qtd_desv > 1 else ""))

            grupos.append(
                GrupoEnsaioLocal(
                    codigo_ensaio=cod,
                    nome_ensaio=nome_ensaio,
                    unidade=unid_ensaio,
                    total_coletas=total,
                    media_texto=media_str,
                    conformidade_pct=pct,
                    nao_conformes=qtd_nc,
                    pendentes_desvios_texto=" · ".join(notas) if notas else "0",
                    coletas=coletas_out,
                )
            )

        return grupos


# Singleton oficial de produção conectado ao PostgreSQL / Supabase
repo = PostgresRepository()
