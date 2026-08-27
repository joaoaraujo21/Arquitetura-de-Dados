# CLAUDE.md — Lakehouse Multi-Cloud

> Onboarding do Claude Code neste repositório. Leia antes de sugerir código, comandos
> ou mudanças de infra. Se uma seção estiver desatualizada, atualize neste arquivo —
> ele é a fonte de verdade para a IA.

---

## 1. Arquitetura em uma linha

**ADLS (Delta, camadas Bronze/Silver/Gold) → Unity Catalog (Databricks) → BigQuery (serving/BI)**

- O **ADLS** é a fonte da verdade dos dados (raw + camadas medallion em Delta).
- O **Databricks** é onde acontece a transformação (PySpark + DLT, governado pelo
  Unity Catalog).
- O **BigQuery** é a camada de serving — recebe o Gold (via cópia ou tabela externa
  sobre Delta, conforme decisão de cada projeto) e atende BI/analytics.
- Há cruzamentos pontuais (ex.: dados de produto no GCS, ERP no Azure SQL); trate-os
  como exceções e documente a origem em `docs/data-lineage/`.

### Identificadores do ambiente (preencher)

- **Azure (lake)**
  - Tenant: `<TENANT_ID_AZURE>`
  - Subscription: `<SUBSCRIPTION_ID>`
  - Storage account (ADLS): `<STORAGE_ACCOUNT>.dfs.core.windows.net`
  - Containers: `raw`, `bronze`, `silver`, `gold`
  - Key Vault: `<KEY_VAULT_NAME>`
  - Databricks workspace: `https://adb-<WORKSPACE_ID>.<REGION>.azuredatabricks.net`
- **Databricks**
  - Unity Catalog metastore: `<METASTORE_ID>`
  - Catalog padrão: `<CATALOG_PRIMARY>` (ex.: `lakehouse`)
  - Schemas: `bronze`, `silver`, `gold`, `sandbox`
  - Cluster policy: `<CLUSTER_POLICY_NAME>` (usar para todos os jobs)
- **GCP (serving)**
  - Projeto: `<PROJECT_GCP_ID>`
  - Dataset BQ serving: `<DATASET_BQ_GOLD>` (ex.: `gold_serving`)
  - Service account de leitura: `<SA_READER>@<PROJECT_GCP_ID>.iam.gserviceaccount.com`

---

## 2. Stack e padrões de código

### Linguagens e ferramentas

- **PySpark** para transformações pesadas e DLT.
- **SQL (Spark SQL)** dentro de `spark.sql(...)` para transformações legíveis e
  testáveis.
- **Delta Live Tables (DLT)** para pipelines Bronze→Silver→Gold.
- **Terraform** para IaC multi-cloud (AzureRM, Databricks, GCP).
- **Databricks Asset Bundles (DABs)** para deploy de jobs/pipelines.
- **dbt-on-Databricks** (se aplicável) para modelos Gold.

### Convenções de PySpark

- **Sempre use Delta** como formato de escrita (`format("delta")`).
- **Particionamento**: usar apenas quando o filtro downstream é claro e estável.
  Particionar por `event_date` (date) ou `tenant_id` (low-cardinality string).
  Evitar partições por colunas de alta cardinalidade.
- **Z-order** somente em colunas usadas em filtros de equality/merge (`zorderBy`).
- **Broadcast hints**: prefira `F.broadcast()` explícito a `autoBroadcastJoinThreshold`.
  Documente no código por que cada broadcast é seguro (estimativa de tamanho).
- **Evite UDFs Python** em caminhos críticos — preferir `pyspark.sql.functions`.
  Se UDF for inevitável, usar Pandas UDF com `Arrow`.
- **Idempotência**: todo job deve ser reexecutável sem efeito colateral. Use
  `MERGE INTO` em vez de `INSERT OVERWRITE` quando possível.
- **Leituras**: sempre especifique o schema (`spark.read.schema(...)`) em produção
  para evitar inferência cara e breaking changes silenciosos.

### Convenções de SQL

- **Spark SQL** segue o estilo do `sqlfluff` (config em `.sqlfluff`).
- CTE > subqueries aninhadas. Nomeie CTEs pelo seu papel semântico, não por
  número (`clientes_ativos`, não `cte_2`).
- Comente **por quê**, não **o que**. O `o que` está no nome.
- Identificadores de catálogo: `<catalog>.<schema>.<table>` (3 níveis, nunca 2).

---

## 3. Estrutura do repositório (monorepo por domínio)

```
.
├── pipelines/                  # DLT pipelines e jobs Spark
│   ├── bronze/                 # ingestão raw → bronze
│   ├── silver/                 # bronze → silver (dedupe, limpeza)
│   └── gold/                   # silver → gold (regras de negócio, agregações)
├── transformations/            # código reutilizável (helpers, UDFs, schemas)
├── infra/
│   ├── terraform/              # IaC multi-cloud
│   └── bundles/                # DABs por job
├── tests/                      # unit + integration tests
├── docs/
│   ├── runbooks/               # procedimentos operacionais
│   ├── data-lineage/           # linhagem por domínio
│   └── adrs/                   # Architecture Decision Records
├── .claude/                    # skills, agents, settings deste projeto
│   ├── skills/
│   ├── agents/
│   └── settings.json
└── CLAUDE.md                   # este arquivo
```

Cada subpasta pode ter seu próprio `CLAUDE.md` com contexto específico
(ex.: `pipelines/bronze/CLAUDE.md` com regras de ingestão).

---

## 4. Comandos canônicos

> Antes de propor um comando, verifique se já existe neste README. **Não invente
> comandos** — consulte `Makefile` ou `infra/bundles/*/databricks.yml`.

- `make lint` — sqlfluff + ruff + terraform validate
- `make test` — pytest (unit) + suíte de integração leve
- `make bundle-validate ENV=dev` — valida os DABs
- `make deploy-jobs ENV=dev` — deploy de jobs (não roda)
- `make run-pipeline PIPELINE=gold_vendas ENV=dev` — dispara uma DLT pipeline
- `make tf-plan ENV=dev` — terraform plan (NÃO apply)
- `make logs JOB=<id> RUN=<run_id>` — baixa logs de um run Databricks

**Ambientes**: `dev`, `staging`, `prod`. Toda mudança em `prod` exige PR com
aprovação + label `prod-impact`.

---

## 5. Gotchas e armadilhas conhecidas

> Atualize esta seção sempre que descobrir um problema recorrente. O objetivo é
> que a IA antecipe o erro antes de você refazer o mesmo debug três vezes.

- **ADLS + Databricks**: o cluster **deve** usar a service principal via
  Workload Identity Federation (NÃO usar access keys). Quebrar isso expõe credenciais.
- **BigQuery servindo do Delta**: a sincronização ADLS→BQ pode ter **lag de 5–10 min**.
  Se um teste precisa de dados "frescos", use `--incremental` no job de sync.
- **DLT + MERGE**: DLT não roda `MERGE` arbitrário. Para upserts, use `apply_changes`
  com `seq_by`. Não tente contornar com `dlt.apply_changes` custom.
- **Partição `event_date`**: usar sempre `date`, nunca `timestamp`. Timestamps em
  partição geram explosão de partições pequenas.
- **Cluster policy**: jobs sem a policy correta são rejeitados pelo deploy.
  Não usar `cluster_id` fixo em código de job.
- **Terraform state**: cada cloud tem seu próprio backend (Azure Storage para AzureRM,
  GCS para GCP). Não misturar.
- **Unity Catalog + GCS externo**: grants em external locations precisam de
  `READ_FILES` ou `WRITE_FILES`, não `SELECT`/`MODIFY`.

---

## 6. Workflow de debug (prioridade do time)

Quando algo falha:

1. **Identifique o job e o run**: `make logs JOB=... RUN=...` para baixar logs.
2. **Leia o erro** — copie a stacktrace e pergunte ao Claude Code: *"explique essa
   falha e proponha a correção"*.
3. **Verifique dependências**: jobs upstream podem estar atrasados. Confirme o estado
   da tabela de entrada (`describe history`, `show partitions`).
4. **Verifique custos antes de re-executar**: jobs Gold reescrevem muito. Use
   `OPTIMIZE` + `ZORDER` antes de reprocessar grandes volumes.
5. **Pós-mortem**: falhas recorrentes viram item na seção 5 *e* novo runbook em
   `docs/runbooks/`.

---

## 7. MCP servers esperados

O `settings.json` deste projeto deve declarar:

- `@databricks/mcp` — listar jobs, ler runs, executar SQL no warehouse.
- GCP MCP (ou `gcloud` via Bash allowlist) — `bq query`, `gsutil ls`.
- Azure MCP — `az` + ADLS para investigar storage e Key Vault.

Se algum desses MCPs não estiver configurado, o Claude Code ainda funciona
(usando CLI via Bash), mas com menos contexto. Consulte `.claude/settings.json`.

---

## 8. Skills e subagentes do projeto

- `skills/dlt-patterns/` — checklist de DLT (CDC, SCD2, expectations).
- `skills/spark-optimizer/` — heurísticas de performance (partition, broadcast, skew).
- `skills/bigquery-sql/` — armadilhas do dialecto BQ (slots, partition decorators,
  funções não suportadas).
- `agents/databricks-debug/` — subagente focado em debug de jobs (lê logs,
  cruza com Unity Catalog, sugere fix).
- `agents/cost-guardrail/` — analisa query/job e estima custo antes de execução.

Use-os via `/skill-name` ou deixando o Claude Code sugerir.

---

## 9. Regras de revisão de PR

Toda PR com mudança em `pipelines/`, `transformations/` ou `infra/` deve ter:

- [ ] Teste unitário (ou justificativa explícita de por que não é testável).
- [ ] `make lint` verde.
- [ ] Schema versionado se houver mudança de estrutura (Avro/Delta schema evolution).
- [ ] Estimativa de impacto em custo (linha em `docs/data-lineage/<domínio>.md`).
- [ ] Sem secrets commitados (verificado por hook pre-commit).
- [ ] ADRs atualizados em `docs/adrs/` se a mudança altera arquitetura.

---

## 10. Glossário

- **Medallion**: padrão Bronze (raw), Silver (limpo), Gold (agregado/regra de negócio).
- **DLT**: Delta Live Tables — framework declarativo do Databricks.
- **DAB**: Databricks Asset Bundle — IaC para jobs/pipelines.
- **UC**: Unity Catalog — governança de dados no Databricks.
- **ADLS**: Azure Data Lake Storage (gen2).
- **OIDC federation**: autenticação sem senha entre clouds (workload identity).
