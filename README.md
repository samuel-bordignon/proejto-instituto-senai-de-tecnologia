# LaudoTech — IST Ambiental

Sistema web de **conferência técnica assistida de laudos de qualidade de água e efluentes** desenvolvido para o **IST Ambiental (SENAI Blumenau/SC)** no contexto do Projeto Aplicado 1 (Ciência de Dados e Inteligência Artificial — UniSENAI).

**Equipe:** Bruno Araujo Dombroski · Maria Balbis Cardoso · Samuel Bordignon Wiegand

---

## Arquitetura de Produção

```text
proejto-instituto-senai-de-tecnologia/
├── app/
│   ├── main.py                        # Entry point da interface web (NiceGUI)
│   ├── assets/                        # Imagens institucionais e folha de estilo corporativa v3
│   ├── core/                          # Regras puras de domínio (motor VMP, estatística 6m, parser UltraLIMS)
│   ├── repo/                          # Repositório PostgreSQL/Supabase (base.py, postgres_repo.py)
│   ├── services/                      # Exportação oficial em PDF (ReportLab) e XLSX 3 abas (OpenPyXL)
│   └── ui/                            # 5 telas (/login, /, /importar, /amostra/{codigo}, /analise) e componentes
├── database/                          # Camada de persistência PostgreSQL/Supabase (psycopg + ConnectionPool)
│   ├── connection.py                  # Pool de conexões (autocommit + prepare_threshold=None) e transaction()
│   ├── query_loader.py                # Carregador de queries nomeadas (-- name: <chave>)
│   ├── queries/                       # Todas as queries SQL isoladas por domínio (RNF-06 — zero SQL em Python)
│   │   ├── auth.sql
│   │   ├── cadastros.sql
│   │   ├── base_legal.sql
│   │   ├── amostras.sql
│   │   ├── conferencia.sql
│   │   └── analise_local.sql
│   ├── schema_laudotech.sql           # DDL oficial normalizado (PostgreSQL v2.2 — 18 tabelas)
│   └── migrations/
│       └── 001_migracao_v2_1.sql      # Migração idempotente v2.0 -> v2.2 + backfill de unidades
├── seeds/                             # Povoamento idempotente (GM/MS 888, SES-SC 1468, CONAMA 430/357, CT-01..16)
├── tests/                             # Suíte automatizada pytest cobrindo CT-01 a CT-16
├── .env.example                       # Modelo de configuração da variável DATABASE_URL
└── requirements.txt                   # Dependências Python do projeto
```

---

## Estratégia de Branches

| Branch | Finalidade |
|---|---|
| **`main`** | Produção / Entrega Oficial conectada ao **PostgreSQL / Supabase** (zero código mock). |
| **`develop`** | Branch de integração contínua das features (`DEV-8` a `DEV-16`). |
| **`stage`** | Contingência congelada com a POC original em memória (`MockRepository`). |

---

## Como Executar o Sistema

### 1. Instalar dependências
```powershell
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente
Copie `.env.example` para `.env` na raiz do repositório e defina `DATABASE_URL` apontando para a instância PostgreSQL / Supabase:
```powershell
Copy-Item .env.example .env
# Teste rápido do pool de conexões:
python -m database.connection
```

### 3. Iniciar a aplicação NiceGUI
```powershell
python app\main.py
```
Acesse `http://127.0.0.1:8080` (usuários operacionais cadastrados no seed: `samuel.wiegand`, `maria.cardoso`, `bruno.dombroski`, `conferente` — senha MVP: `123456`).  
Para alterar a porta padrão, defina `LAUDOTECH_PORT` (ex.: `$env:LAUDOTECH_PORT="8081"`).

---

## Como Executar a Suíte de Testes (`CT-01` a `CT-16`)

```powershell
python -m pytest -v tests/
```

A suíte valida automaticamente:
- **`CT-01` a `CT-09`** (`tests/test_motor_conformidade.py`): operadores `<=`, `<` estrito, `>=`, `FAIXA`, `AUSENCIA`, lógica intervalar `<LQ` / `>LS`, conflito multi-norma (`GM/MS 888` vs. `SES-SC 1468`, `CONAMA 430`, `CONAMA 357`) e bloqueio de divergência de unidade (`RN-05` / `RNF-02`).
- **`CT-10` a `CT-11`** (`tests/test_parser_ultralims.py`): limpeza de sujeiras reais do UltraLIMS sem falso positivo em vírgula PT-BR, descarte `RN-02` (`________`, `SVOC`), detecção de amostras duplicadas, planilha real `.xlsx` e exportações PDF/XLSX (`RF-07`).
- **`CT-12` a `CT-15`** (`tests/test_estatistica_historica.py`): histórico mínimo (`n >= 3`), desvio estatístico (`μ ± 0,20σ`) dentro do VMP, séries com `<LQ` misturado (`RN-09`) e janela calendário de 6 meses / teto de 6 resultados (`RN-08`).
- **`CT-16` e `RNF-06`** (`tests/test_postgres_repo.py`): isolamento 100% das queries em `database/queries/*.sql`, bloqueio transacional de reimportação e persistência atômica de conferência + trilha `log_alteracao` (`RN-10`).
