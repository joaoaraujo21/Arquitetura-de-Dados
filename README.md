# Data Engineering Project - OpenRouter Aula

> Estrutura completa de projeto para engenharia de dados seguindo arquitetura medallion (bronze/silver/gold), com suporte para Databricks (Notebooks, DLT, dbt, Unity Catalog) e execução local (PostgreSQL, Airflow).

## 📁 Estrutura do Projeto

```
openrouteraula/
├── README.md                    # Esta documentação
├── .gitignore                   # Arquivos ignorados pelo Git
├── .env.example                 # Template de variáveis de ambiente
├── pyproject.toml               # Configuração do projeto Python
├── docker-compose.yml           # Serviços locais
├── Makefile                     # Comandos úteis de automação
│
├── src/                         # Código fonte Python (execução local)
│   ├── ingestion/               # Extract (Extração)
│   │   ├── extractors/          # Extratores por fonte
│   │   └── connectors/          # Conectores (PostgreSQL, etc)
│   ├── transformation/          # Transform - Camadas Medalhão
│   │   ├── bronze/              # Dados brutos
│   │   ├── silver/              # Limpos/validados
│   │   └── gold/                # Agregados/negócio
│   ├── loading/                 # Load (Carga)
│   ├── quality/                 # Qualidade de dados
│   ├── pipelines/               # Pipelines ETL/ELT
│   ├── utils/                   # Utilitários (logging)
│   └── settings.py              # Configurações centralizadas
│
├── databricks/                  # 🔷 Estrutura específica para Databricks
│   ├── notebooks/               # Notebooks Spark/Python
│   │   ├── ingestion/           # Notebooks de ingestão
│   │   ├── transformation/      # Notebooks de transformação
│   │   ├── ml/                  # Notebooks de ML
│   │   └── analytics/           # Notebooks analíticos
│   ├── dlt/                     # Delta Live Tables (DLT)
│   ├── dbt/                     # dbt-databricks project
│   │   ├── models/              # Modelos dbt (staging/marts)
│   │   ├── macros/              # Macros reutilizáveis
│   │   ├── tests/               # Testes de dados
│   │   ├── seeds/               # Dados de seed
│   │   ├── snapshots/           # SCD Type 2
│   │   ├── dbt_project.yml      # Configuração dbt
│   │   └── profiles.yml         # Credenciais (env vars)
│   ├── workflows/               # Databricks Workflows/Jobs
│   └── schemas/                 # DDLs (Unity Catalog)
│       ├── unity_catalog_setup.sql
│       ├── 01_bronze_tables.sql
│       ├── 02_silver_tables.sql
│       └── 03_gold_tables.sql
│
├── config/                      # Configurações
├── tests/                       # Testes (unit/integration)
├── data/                        # Dados locais
├── notebooks/                   # Jupyter notebooks locais
├── sql/                         # SQL scripts locais
├── infrastructure/              # IaC (Terraform, Docker, K8s)
├── docs/                        # Documentação
├── scripts/                     # Scripts utilitários
├── .github/workflows/           # CI/CD GitHub Actions
└── monitoring/                  # Observabilidade
```

## 🎯 Visão Geral: Local vs Databricks

Este projeto suporta **dois modos de execução**:

### 🖥️ Execução Local (src/)
- PostgreSQL + Airflow
- Python puro (pandas, polars)
- Indicado para: desenvolvimento, testes locais, dados pequenos/médios

### 🔷 Databricks (databricks/)
- Delta Lake + Unity Catalog
- Apache Spark + DLT
- dbt-databricks para transformações
- Indicado para: produção, big data, ML/AI

## 🔷 Databricks - Guia de Início

### Pré-requisitos
- Databricks Workspace (AWS, Azure ou GCP)
- Unity Catalog habilitado
- Service Principal ou PAT para deploy
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html)

### Deploy no Databricks

```bash
# Instala Databricks CLI
pip install databricks-cli

# Configura autenticação
databricks configure --host https://<workspace>.cloud.databricks.com \
  --token <seu-personal-access-token>

# Deploy dos notebooks
databricks workspace import_dir ./databricks/notebooks /Shared/openrouter/notebooks
databricks workspace import_dir ./databricks/dlt /Shared/openrouter/dlt
databricks workspace import_dir ./databricks/workflows /Shared/openrouter/workflows

# Cria Unity Catalog e tabelas
databricks sql execute --sql-file databricks/schemas/unity_catalog_setup.sql
databricks sql execute --sql-file databricks/schemas/01_bronze_tables.sql
databricks sql execute --sql-file databricks/schemas/02_silver_tables.sql
databricks sql execute --sql-file databricks/schemas/03_gold_tables.sql
```

### Arquitetura Medalhão no Databricks

```
┌─────────────────────────────────────────────────────┐
│              Landing (S3/ADLS/GCS)                  │
└──────────────────────┬──────────────────────────────┘
                       │ Auto Loader
                       ▼
┌─────────────────────────────────────────────────────┐
│ BRONZE (raw) - Streaming, schema evolution          │
│ • openrouter_catalog.bronze.raw_events              │
│ • openrouter_catalog.bronze.raw_users               │
│ • openrouter_catalog.bronze.raw_billing             │
└──────────────────────┬──────────────────────────────┘
                       │ DLT / dbt / Notebooks
                       ▼
┌─────────────────────────────────────────────────────┐
│ SILVER (cleaned) - Deduplicated, validated, typed   │
│ • openrouter_catalog.silver.clean_events            │
│ • openrouter_catalog.silver.clean_users             │
│ • openrouter_catalog.silver.dim_models              │
│ • openrouter_catalog.silver.dim_date                │
└──────────────────────┬──────────────────────────────┘
                       │ dbt models / Notebooks
                       ▼
┌─────────────────────────────────────────────────────┐
│ GOLD (aggregated) - Business metrics, dimensions   │
│ • openrouter_catalog.gold.fact_daily_usage          │
│ • openrouter_catalog.gold.fact_sessions             │
│ • openrouter_catalog.gold.dim_user_360              │
│ • openrouter_catalog.gold.agg_hourly_metrics        │
└─────────────────────────────────────────────────────┘
```

### Componentes Databricks Criados

| Componente | Arquivo | Descrição |
|-----------|---------|-----------|
| **Ingestão** | `databricks/notebooks/ingestion/01_ingest_raw_data.py` | Ingestão de API + S3 com metadados |
| **Silver** | `databricks/notebooks/transformation/02_transform_silver.py` | Limpeza + Great Expectations |
| **Gold** | `databricks/notebooks/transformation/03_transform_gold.py` | Dimensões e fatos |
| **DLT** | `databricks/dlt/01_dlt_pipeline.py` | Pipeline streaming com quality checks |
| **dbt** | `databricks/dbt/dbt_project.yml` + `models/` | Transformações versionadas com testes |
| **Workflows** | `databricks/workflows/01_workflow_orchestrator.py` | Orquestração de tasks |
| **Unity Catalog** | `databricks/schemas/*.sql` | Setup de catálogo, schemas e tabelas |

## 🏗️ Arquitetura Medalhão (Detalhada)

### Bronze (Raw)
- Dados exatamente como chegam da fonte
- Sem transformações, apenas ingestão
- Auto Loader para schema evolution
- Metadados: `_ingest_timestamp`, `_source_file`
- Tabelas: `bronze.<source>_<entity>`

### Silver (Cleaned/Validated)
- Dados limpos, tipados, deduplicados
- Validações com Great Expectations + DLT Expectations
- Tabelas: `silver.<domain>_<entity>`
- Constraints declarativas no schema

### Gold (Business/Aggregated)
- Dados prontos para consumo analítico
- Star schema (fact + dim tables)
- Z-ordering + clustering para performance
- Tabelas: `gold.<business_area>_<metric>`

## 🛠️ Comandos Úteis

```bash
# Setup local
make install
make docker-up
make dev

# Testes
make test-unit
make test-integration
make test-coverage

# Qualidade
make lint
make type-check
make format

# Databricks
databricks workspace import_dir ./databricks/notebooks /Shared/openrouter
databricks bundle deploy --target prod  # se usar Databricks Asset Bundles
```

## 🧪 Testes

```bash
# Testes unitários
make test-unit

# Testes de integração
make test-integration

# Todos os testes com coverage
make test-coverage
```

## 📊 Qualidade de Dados

- **dbt tests**: `databricks/dbt/tests/` (not_null, unique, etc.)
- **Great Expectations**: `databricks/notebooks/transformation/02_transform_silver.py`
- **DLT Expectations**: `databricks/dlt/01_dlt_pipeline.py` (@dlt.expect)
- **Unity Catalog Constraints**: `databricks/schemas/*.sql` (CHECK constraints)

## 🔄 Orquestração

- **Databricks Workflows**: `databricks/workflows/01_workflow_orchestrator.py`
- **Airflow** (modo local): `dags/` com DAGs versionadas

## 📚 Documentação

- `docs/architecture.md` - Arquitetura do sistema
- `docs/data_model.md` - Modelo de dados (ERD, dicionário)
- `docs/runbook.md` - Procedimentos operacionais

## 🔍 Observabilidade

- **Logs**: Estruturados (JSON) via `structlog`
- **Métricas**: Prometheus + Grafana (local) / Databricks SQL Analytics (cloud)
- **Tracing**: OpenTelemetry
- **Lineage**: Unity Catalog (automático para Databricks)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.