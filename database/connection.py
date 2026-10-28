from __future__ import annotations

import os
import warnings
from dotenv import find_dotenv, load_dotenv
import pandas as pd
import psycopg

# Procura o arquivo .env automaticamente subindo as pastas (igual ao dotenv do JS)
load_dotenv(find_dotenv())

def get_database_url() -> str:
    # Retorna a DATABASE_URL configurada no arquivo .env sanitizada para o psycopg.
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Variável DATABASE_URL não encontrada. Configure o arquivo .env na raiz do projeto."
        )
    return url

def consultar_df(sql: str, params: list | tuple | None = None) -> pd.DataFrame:
    #Executa um SELECT em SQL puro usando pd.read_sql_query e retorna diretamente um DataFrame
    with psycopg.connect(get_database_url()) as conn:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return pd.read_sql_query(sql, conn, params=params)
        
def executar_sql(sql: str, params: list | tuple | None = None) -> None:
    #Executa um comando SQL (INSERT, UPDATE, DELETE, DDL) em SQL puro no Supabase
    with psycopg.connect(get_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
        conn.commit()

if __name__ == "__main__":
    df_teste = consultar_df("SELECT current_database() AS db, current_user AS usuario;")
    print("Conexão com Supabase OK via pd.read_sql_query:")
    print(df_teste)
