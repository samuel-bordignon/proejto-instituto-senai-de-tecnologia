# LaudoTech — IST Ambiental

Sistema de conferência técnica assistida de qualidade de água e efluentes para o **IST Ambiental (SENAI Blumenau/SC)**.

---

## Arquitetura do Projeto

```text
proejto-instituto-senai-de-tecnologia/
├── app/
│   ├── main.py                        # Entry point da interface web (NiceGUI)
│   ├── assets/                        # Imagens, ícones e folha de estilo (CSS)
│   ├── core/                          # Regras puras de domínio (parser, conformidade, estatística, modelos)
│   ├── repo/                          # Repositório de dados e fixtures mockadas da POC
│   ├── services/                      # Serviços de aplicação (geração de PDF)
│   └── ui/                            # Páginas (/login, /, /importar, /amostra/{codigo}, /analise) e componentes
├── database/                          # Conexão PostgreSQL/Supabase (psycopg), DDL oficial e migrações
│   ├── __init__.py                    # Exporta consultar_df(), executar_sql(), get_database_url()
│   ├── connection.py                  # Conexão direta com Supabase (SQL puro)
│   ├── schema_laudotech.sql           # DDL SQL oficial (PostgreSQL v2.2 — 18 tabelas)
│   └── migrations/
│       └── 001_migracao_v2_1.sql      # Migração idempotente v2.0 -> v2.2 + backfill de unidades
├── seeds/                             # Scripts SQL de povoamento (Portarias 888/1468, CONAMA 430/357 e CT-01..CT-16)
├── .env.example                       # Modelo de configuração da variável DATABASE_URL
└── requirements.txt                   # Dependências Python do projeto
```

---

## Como Rodar o Projeto

### 1. Instalar dependências
```powershell
pip install -r requirements.txt
```

### 2. Executar a Interface Web (NiceGUI — POC)
```powershell
python app\main.py
```
A aplicação sobe em `http://127.0.0.1:8080` (usuário de demonstração: `samuel.wiegand` / `123456`).  
Para usar outra porta, defina `LAUDOTECH_PORT` (ex.: `$env:LAUDOTECH_PORT="8081"`).

### 3. Configurar e testar a conexão com o Banco de Dados (opcional na POC)
Copie `.env.example` para `.env`, preencha `DATABASE_URL` e execute:
```powershell
python -m database.connection
```

---

## Como Usar o Banco no Python (SQL Puro)

```python
from database import consultar_df, executar_sql

# Consulta retornando pandas DataFrame
df_amostras = consultar_df("SELECT * FROM amostra ORDER BY data_coleta DESC")

# Execução de INSERT, UPDATE ou DELETE
executar_sql(
    "INSERT INTO cliente (razao_social, cidade, uf) VALUES (%s, %s, %s)",
    ["SAMAE Blumenau", "Blumenau", "SC"],
)
```
