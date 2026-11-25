"""Camada de conexão PostgreSQL/Supabase com ConnectionPool e transações atômicas (RNF-05)."""

from __future__ import annotations

import atexit
import os
import threading
import warnings
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from dotenv import find_dotenv, load_dotenv
import pandas as pd
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv(find_dotenv())

_pool_lock = threading.Lock()
_pool: ConnectionPool | None = None


def get_database_url() -> str:
    """Retorna a DATABASE_URL configurada no arquivo .env."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Variável DATABASE_URL não encontrada. Configure o arquivo .env na raiz do projeto."
        )
    return url


def get_pool() -> ConnectionPool:
    """Retorna o pool singleton de conexões (inicializado sob demanda)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    conninfo=get_database_url(),
                    min_size=1,
                    max_size=int(os.getenv("LAUDOTECH_DB_POOL_MAX", "6")),
                    timeout=15.0,
                    max_idle=300.0,
                    kwargs={
                        "autocommit": True,         # 1 RTT em leituras; BEGIN/COMMIT explícito via conn.transaction()
                        "prepare_threshold": None,  # compatível com PgBouncer/Supabase
                        "connect_timeout": 10,
                    },
                    open=True,
                )
    return _pool


def close_pool() -> None:
    """Fecha o pool de conexões de forma segura no encerramento do processo."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


atexit.register(close_pool)


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    """Abre um bloco transacional atômico (COMMIT ao sair sem erro, ROLLBACK em exceção)."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.transaction():
            yield conn


def consultar_lista(
    sql: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
    conn: psycopg.Connection | None = None,
) -> list[dict[str, Any]]:
    """Executa um SELECT e retorna lista de dicionários (coluna -> valor)."""
    if conn is not None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())

    pool = get_pool()
    with pool.connection() as pooled_conn:
        with pooled_conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params or ())
            return list(cur.fetchall())


def consultar_um(
    sql: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
    conn: psycopg.Connection | None = None,
) -> dict[str, Any] | None:
    """Executa um SELECT (ou INSERT ... RETURNING) e retorna o primeiro registro como dict ou None."""
    if conn is not None:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    pool = get_pool()
    with pool.connection() as pooled_conn:
        with pooled_conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def consultar_df(sql: str, params: list | tuple | None = None) -> pd.DataFrame:
    """Executa um SELECT em SQL puro e retorna diretamente um pandas DataFrame."""
    pool = get_pool()
    with pool.connection() as conn:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.read_sql_query(sql, conn, params=params)


def executar_sql(
    sql: str,
    params: Sequence[Any] | dict[str, Any] | None = None,
    conn: psycopg.Connection | None = None,
) -> int:
    """Executa INSERT, UPDATE, DELETE ou DDL retornando rowcount."""
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount

    with transaction() as tx_conn:
        with tx_conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount


def executar_script(sql_script: str) -> None:
    """Executa um script SQL multi-statement em autocommit (útil para seeds e migrações)."""
    with psycopg.connect(get_database_url(), autocommit=True, prepare_threshold=None) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_script)


if __name__ == "__main__":
    from database.query_loader import obter_query

    df_teste = consultar_df(obter_query("auth", "ping_conexao"))
    print("Conexão com Supabase OK via ConnectionPool:")
    print(df_teste)
