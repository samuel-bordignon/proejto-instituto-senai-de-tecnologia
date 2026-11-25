"""Carregador centralizado de queries SQL isoladas em database/queries/*.sql (RNF-06)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

PASTA_QUERIES = Path(__file__).resolve().parent / "queries"
_RE_MARCADOR_NOME = re.compile(r"^\s*--\s*name\s*:\s*([a-zA-Z0-9_]+)\s*$")


@lru_cache(maxsize=32)
def carregar_arquivo_queries(dominio: str) -> dict[str, str]:
    """
    Lê `database/queries/<dominio>.sql` e retorna dict {nome_query: sql}.
    Cada bloco deve ser precedido por `-- name: <nome_query>`.
    """
    nome_limpo = dominio[:-4] if dominio.endswith(".sql") else dominio
    caminho = PASTA_QUERIES / f"{nome_limpo}.sql"
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de queries não encontrado: {caminho}")

    blocos: dict[str, list[str]] = {}
    nome_atual: str | None = None

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        m = _RE_MARCADOR_NOME.match(linha)
        if m:
            novo_nome = m.group(1)
            if novo_nome in blocos:
                raise ValueError(f"Query duplicada '{novo_nome}' em {caminho.name}")
            nome_atual = novo_nome
            blocos[nome_atual] = []
            continue

        if nome_atual is not None:
            blocos[nome_atual].append(linha)

    resultado: dict[str, str] = {}
    for chave, linhas in blocos.items():
        sql = "\n".join(linhas).strip()
        if not sql:
            raise ValueError(f"Query '{chave}' em {caminho.name} está vazia.")
        resultado[chave] = sql

    return resultado


def obter_query(dominio: str, nome: str) -> str:
    """Retorna o texto SQL exato da query `nome` definida em `database/queries/<dominio>.sql`."""
    mapa = carregar_arquivo_queries(dominio)
    if nome not in mapa:
        disponiveis = ", ".join(sorted(mapa.keys()))
        raise KeyError(
            f"Query '{nome}' não encontrada em '{dominio}.sql'. Disponíveis: [{disponiveis}]"
        )
    return mapa[nome]


def listar_todas_queries() -> dict[str, list[str]]:
    """Lista todos os domínios `.sql` e seus identificadores de query registrados."""
    inventario: dict[str, list[str]] = {}
    for arq in sorted(PASTA_QUERIES.glob("*.sql")):
        dom = arq.stem
        inventario[dom] = list(carregar_arquivo_queries(dom).keys())
    return inventario
