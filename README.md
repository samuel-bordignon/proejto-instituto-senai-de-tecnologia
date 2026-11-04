# LaudoTech — IST Ambiental

Sistema de automação de análise de conformidade laboratorial de qualidade de água e apoio à emissão de pareceres técnicos para o **IST Ambiental (SENAI Blumenau/SC)**.

---

## Arquitetura do Projeto

```text
proejto-instituto-senai-de-tecnologia/
├── app/
│   └── src/                           # Frontend e aplicação interativa (Streamlit)
│       ├── painel.py                  # Entry point principal da interface
│       ├── components/                # Componentes visuais desacoplados
│       │   ├── sidebar.py
│       │   ├── cards_legislacoes.py
│       │   ├── tela_amostras.py
│       │   ├── dialog_upload.py
│       │   └── ensaios/               # Módulo da tela de visualização de ensaios
│       ├── data/                      # Motor de conformidade e dados de apoio
│       │   ├── mock_data.py
│       │   └── motor_conformidade.py
│       └── services/                  # Serviços de exportação (PDF / XLSX)
│           └── relatorio_pdf.py
├── database/                          # Camada de Conexão e SQL (PostgreSQL / Supabase via psycopg)
│   ├── __init__.py                    # Exporta consultar_sql(), consultar_df(), executar_sql(), executar_script()
│   ├── connection.py                  # Conexão direta com Supabase (SQL puro)
│   └── schema_laudotech.sql           # DDL SQL oficial e master (PostgreSQL v2.0 - 17 tabelas)
├── .env.example                       # Modelo de configuração da variável DATABASE_URL
└── requirements.txt                   # Dependências Python do projeto
```

---

## Como Rodar o Projeto

### 1. Instalar dependências
```powershell
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente (`.env`)
Copie o arquivo `.env.example` para `.env` e preencha a senha do banco do **Supabase** (usando o host do *Session Pooler* IPv4):
```env
DATABASE_URL="postgresql://postgres.dzvpreczkcmmapvsycpn:SUA_SENHA@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
```

### 3. Testar a conexão com o Banco de Dados
```powershell
python -m database.connection
```

### 4. Executar a Interface (Streamlit)
```powershell
streamlit run app/src/painel.py
```

---

## Como Usar o Banco no Python (SQL Puro)

Basta importar as funções do pacote `database`:

```python
from database import consultar_sql, consultar_df, executar_sql

# 1. Consulta retornando lista de dicionários
clientes = consultar_sql("SELECT id, razao_social, cidade FROM cliente WHERE uf = %s", ["SC"])

# 2. Consulta retornando pandas DataFrame (pronto para exibir no Streamlit)
df_amostras = consultar_df("SELECT * FROM amostra ORDER BY data_coleta DESC")

# 3. Execução de comandos INSERT, UPDATE ou DELETE
executar_sql(
    "INSERT INTO cliente (razao_social, cidade, uf) VALUES (%s, %s, %s)",
    ["SAMAE Blumenau", "Blumenau", "SC"]
)
```
