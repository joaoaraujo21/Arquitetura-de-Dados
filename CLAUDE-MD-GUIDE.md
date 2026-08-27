# Guia Completo do CLAUDE.md

> **Data:** 27 de agosto de 2026
> **Autor:** Claude Code Agent
> **Última atualização:** 27 de agosto de 2026

---

## Sumário

1. [O que é o CLAUDE.md](#1-o-que-é-o-claudemd)
2. [Por que o CLAUDE.md é diferente de tudo mais](#2-por-que-o-claudemd-é-diferente-de-tudo-mais)
3. [Hierarquia de carregamento (4 níveis)](#3-hierarquia-de-carregamento-4-níveis)
4. [Quando usar CLAUDE.md vs. outras ferramentas](#4-quando-usar-claudemd-vs-outras-ferramentas)
5. [Anatomia de um CLAUDE.md eficaz](#5-anatomia-de-um-claudemd-eficaz)
6. [Boas práticas e anti-patterns](#6-boas-práticas-e-anti-patterns)
7. [Exemplo completo por contexto](#7-exemplo-completo-por-contexto)
8. [Fluxo de manutenção](#8-fluxo-de-manutenção)
9. [Ferramentas complementares](#9-ferramentas-complementares)

---

## 1. O que é o CLAUDE.md

O `CLAUDE.md` é um arquivo Markdown que o **Claude Code lê automaticamente no início de cada sessão**, antes de processar qualquer mensagem do usuário. Ele funciona como um **documento de onboarding para a IA**: o que ela precisa saber sobre o projeto, a equipe e o contexto de trabalho, sem que o usuário precise repetir a cada conversa.

Não é:
- Um prompt de sistema (não é injetado via `--system`).
- Um arquivo de configuração (não tem schema obrigatório).
- Um mecanismo de roteamento de tarefas.

É:
- **Documentação executável** — o modelo age com base no que lê.
- **Versionado via git** — todas as mudanças passam por PR review.
- **Declarativo** — descreve o contexto, não instrui o comportamento.

O nome é por convenção: `CLAUDE.md` (com as duas letras maiúsculas). O Claude Code procura exatamente esse nome no filesystem.

---

## 2. Por que o CLAUDE.md é diferente de tudo mais

### O que o diferencia

| Aspecto | CLAUDE.md | README.md | .env | system prompt |
|---|---|---|---|---|
| **Lido automaticamente** | ✅ Sim | ❌ Não (precisa pedir) | ❌ Não | ✅ Sim, mas custo tokens |
| **Versionado** | ✅ Sim (git) | ✅ Sim | ⚠️ Risco (pode vazar secrets) | ❌ Não |
| **Custo de tokens** | Zero (no início da sessão) | Cobra a cada referência | N/A | Cobra toda interação |
| **Escopo** | Todo o repo | Todo o repo | Variáveis | Sessão atual |
| **Manutenção** | Como qualquer doc | Como qualquer doc | Propenso a stale | Descartado ao fim |

### Custo zero de tokens na prática

O `CLAUDE.md` é injetado no **system prompt** uma vez, no início da sessão. Cada mensagem subsequente do usuário referencia o contexto já carregado, sem custo adicional de repetição. Isso é diferente de um prompt in-line, que repetiria o conteúdo a cada chamada.

Para um projeto com 10–20 seções de documentação, isso pode representar **milhares de tokens economizados** por semana em sessões longas.

### Hierarquia de carregamento

O Claude Code carrega `CLAUDE.md` de até **4 níveis**, do mais genérico ao mais específico:

```
Nível 1 (global, organização):  ~/.claude/CLAUDE.md
Nível 2 (pessoal):              ~/.claude/CLAUDE.md (do usuário)
Nível 3 (repositório):          ./CLAUDE.md
Nível 4 (subpasta):             ./<subpasta>/CLAUDE.md
```

Os níveis são **combinados de forma somativa**: o Claude Code carrega todos os que existem e os mescla. Quando há conflito, **o mais específico vence** (uma seção em `./src/CLAUDE.md` sobrepõe a mesma seção em `./CLAUDE.md`).

Isso permite cenários poderosos:
- **Global** (`~/.claude/CLAUDE.md`): preferências pessoais do desenvolvedor (formato de commits, como gosta de review).
- **De organização**: padrões de código, convenções de nomenclatura, fluxos de trabalho.
- **Por repositório**: contexto específico do projeto (arquitetura, stack).
- **Por subpasta**: contexto de equipe ou domínio (ex.: `./pipelines/bronze/CLAUDE.md` com regras de ingestão).

---

## 3. Hierarquia de carregamento (4 níveis)

### Nível 1 — Global (organização)

`~/.claude/CLAUDE.md`

É o arquivo que vive no home do usuário. Pode ser lido por qualquer sessão de Claude Code em qualquer diretório. Ideal para padrões organizacionais e preferências pessoais.

### Nível 2 — Pessoal

`~/.claude/CLAUDE.md` (mesmo arquivo que o nível 1 — coexistem no mesmo arquivo, com seções distintas)

O arquivo no home do usuário é a combinação de contexto organizacional e preferências pessoais. Se o home for compartilhado (ex.: `/home/dev` em ambiente corporativo), o nível 1 é organizacional e o nível 2 pode não existir.

### Nível 3 — Repositório

`./CLAUDE.md` (na raiz do repositório git)

É o arquivo que é commitado junto com o código. Qualquer pessoa que clone o repo tem esse contexto automaticamente. Este é o **nível mais importante** para projetos de equipe.

### Nível 4 — Subpasta

`./<subpasta>/CLAUDE.md`

Útil para monorepos onde cada domínio/equipe tem suas próprias convenções. Exemplo:

```
monorepo/
├── CLAUDE.md                    # contexto geral (todas as sessões)
├── pipelines/
│   ├── bronze/
│   │   └── CLAUDE.md            # só sessões dentro de bronze
│   ├── silver/
│   │   └── CLAUDE.md            # só sessões dentro de silver
│   └── gold/
│       └── CLAUDE.md            # só sessões dentro de gold
└── ml/
    └── CLAUDE.md                # contexto de ML
```

---

## 4. Quando usar CLAUDE.md vs. outras ferramentas

### Matriz de decisão

| Situação | Ferramenta certa |
|---|---|
| Convenções de código, arquitetura, comandos | **CLAUDE.md** |
| Preferências pessoais do usuário (não do time) | **Memória** (`memory/`) |
| Procedimento detalhado com checklist (ex.: como fazer code review de Spark) | **Skill** (`skills/`) |
| Comando rápido reutilizável (ex.: `deploy-job --env=prod`) | **Slash command** (`commands/`) |
| Fatos duráveis sobre o usuário ou o projeto (não no código) | **Memória** (`memory/`) |
| Integração com serviços externos (BQ, Databricks, Azure) | **MCP server** |
| Validação automática em eventos (pre-commit, post-edit) | **Hook** (`settings.json`) |
| Perspectiva isolada com ferramentas específicas | **Subagente** (`agents/`) |
| Tarefa que cruza múltiplas dimensões (debug de job) | **Workflow** (multi-agente) |

### Como eles se conectam

```
CLAUDE.md
├── Referencia skills          → "use /spark-optimizer para reviews"
├── Referencia MCPs            → "databricks-mcp é a fonte de logs"
├── Referencia hooks           → "pre-commit impede secrets"
└── Referencia subagentes      → "para debug, use /databricks-debug"

Skills
├── Podem referenciar skills   → "use /cost-guard como pré-requisito"
├── Podem referenciar MCPs     → "confira o DLT via databricks-mcp"
└── Podem referenciar memória   → "seja consistente com preferências em memory/"

Subagentes
├── Carregam CLAUDE.md local   → cada um tem seu contexto
└── Podem usar MCPs            → acesso direto às plataformas
```

---

## 5. Anatomia de um CLAUDE.md eficaz

### Estrutura recomendada (seções)

```
1. Arquitetura de uma linha
   → O que é o sistema, onde cada parte vive, qual o fluxo de dados.

2. Identificadores do ambiente
   → IDs de projetos, tenants, storage accounts, URIs.
   → IMPORTANTE: usar placeholders para valores sensíveis.

3. Stack e padrões de código
   → Linguagens, frameworks, ferramentas usadas.
   → Convenções de estilo e nomenclatura.

4. Estrutura do repositório
   → Layout de pastas com explicação do papel de cada uma.

5. Comandos canônicos
   → make targets, scripts, CLI principais.
   → O que cada um faz (não como).

6. Gotchas e armadilhas
   → Problemas conhecidos, soluções, exceções.

7. Workflow operacional
   → Como fazer as tarefas mais comuns (debug, deploy, etc.).

8. Ferramentas externas (MCPs)
   → Quais MCP servers estão configurados e para quê.

9. Skills e subagentes disponíveis
   → Onde encontrar ajuda especializada.

10. Regras de revisão de PR
    → Checklist que o Claude deve aplicar em reviews.

11. Glossário
    → Termos específicos do domínio (siglas, abreviações).
```

### O que NÃO colocar

- **Secrets, tokens, senhas, chaves de API.** Nunca. Mesmo em repositórios privados, é uma prática de risco. Use variáveis de ambiente.
- **Conteúdo volátil** (status de projetos, métricas que mudam toda semana, bugs em aberto). Use issues e project boards.
- **O que o código já diz.** Se o código documenta seus imports, não repita no CLAUDE.md.
- **Prompts longos.** O arquivo é lido inteiro. Cada linha custa no contexto. Idealmente < 200 linhas.

---

## 6. Boas práticas e anti-patterns

### Boas práticas

**1. Nomeie as seções com hierarquia semântica**
Números e títulos claros fazem o arquivo ser navegável tanto por humanos quanto pelo modelo.

**2. Use placeholders nomeados para valores sensíveis**

```
# ❌ Errado — nome fictício que parece real
storage_account: "datalakefakeprod"

# ✅ Certo — placeholder claro que você substitui
storage_account: "<STORAGE_ACCOUNT_NAME>"

# ✅ Certo — variável de ambiente referenciada
storage_account: "${STORAGE_ACCOUNT_NAME}"
```

**3. Escreva para ser atualizado, não para ser perfeito**
O CLAUDE.md é um documento vivo. Um arquivo desatualizado é melhor que um arquivo inexistente. Priorize ter conteúdo razoável agora e refinar depois.

**4. Use o glossário para termos específicos do domínio**
Siglas como "DLT", "UC", "ADLS" significam coisas diferentes em cada organização. O glossário evita mal-entendidos.

**5. Referencie outras ferramentas (skills, MCPs, hooks)**
O CLAUDE.md não precisa conter tudo — ele pode ser um hub que aponta para onde ir.

### Anti-patterns

**1. Escrever o CLAUDE.md como se fosse um README**

```
# ❌ Anti-pattern: README disfarçado
# Este projeto usa PySpark para processar dados...
# O repositório tem as seguintes pastas...

# ✅ Certo: contexto acionável para a IA
# Transformações PySpark em pipelines/ devem usar Delta.
# Particionamento: usar event_date (date), nunca timestamp.
```

**2. Colocar a mesma informação em múltiplos lugares**
Se a convenção de particionamento está no CLAUDE.md, não repita na skill. Um é a fonte de verdade.

**3. Usar jargão sem definições**
Se você escreve "o UC grant precisa de WRITE_FILES", mas nunca definiu WRITE_FILES, a IA vai tentar adivinhar.

**4. Esquecer de atualizar após mudanças de arquitetura**
O CLAUDE.md fica stale como qualquer documentação. Vincule a atualização do CLAUDE.md a um evento (ex.: whenever you change infrastructure, update CLAUDE.md in the same PR).

---

## 7. Exemplo completo por contexto

### 7.1 Data Engineer (multi-cloud: ADLS + BigQuery + Databricks)

*Este é o CLAUDE.md criado para o cenário do usuário.*

```
# CLAUDE.md — Lakehouse Multi-Cloud

## Arquitetura em uma linha
ADLS (Delta, Bronze/Silver/Gold) → Unity Catalog (Databricks) → BigQuery (serving/BI)

## Identificadores do ambiente
- Azure: <TENANT_ID>, <STORAGE_ACCOUNT>.dfs.core.windows.net
- Databricks: adb-<WORKSPACE_ID>.<REGION>.azuredatabricks.net
- GCP: <PROJECT_GCP_ID>, dataset BQ: <DATASET_BQ_GOLD>

## Stack
- PySpark + Delta Live Tables (DLT) para transformações.
- Spark SQL para queries legíveis/testáveis.
- Terraform + DABs para IaC.
- Databricks Asset Bundles para deploy de jobs.

## Convenções de PySpark
- Sempre usar Delta como formato de escrita.
- Particionamento: usar event_date (date), nunca timestamp.
- Broadcast hints explícitos (F.broadcast()).
- Evitar UDFs Python — preferir pyspark.sql.functions.

## Estrutura
pipelines/{bronze,silver,gold}/ — DLT pipelines por camada.
transformations/ — helpers, UDFs, schemas reutilizáveis.
infra/ — Terraform + DABs.
tests/ — unit + integração.

## Comandos canônicos
make lint         # sqlfluff + ruff + terraform validate
make test         # pytest
make logs JOB=... RUN=...  # baixa logs do Databricks
make tf-plan ENV=dev  # terraform plan (NÃO apply)

## Gotchas
- ADLS + Databricks: usar Workload Identity Federation, não access keys.
- DLT: usar apply_changes para upserts, não MERGE arbitrário.
- Partição event_date: usar date, não timestamp.
- Cluster policy: jobs sem policy são rejeitados no deploy.

## Workflow de debug
1. make logs → baixar logs do run.
2. Perguntar ao Claude: "explique essa falha e proponha correção."
3. Verificar dependências (describe history da tabela de entrada).
4. Verificar custo antes de re-executar (OPTIMIZE + ZORDER).
5. Falhas recorrentes → gotcha nova + runbook.

## Skills disponíveis
skills/dlt-patterns/    # CDC, SCD2, expectations
skills/spark-optimizer/ # partition, broadcast, skew
skills/bigquery-sql/    # armadilhas do BigQuery

## Glossário
- Medallion: Bronze (raw), Silver (limpo), Gold (agregado).
- DLT: Delta Live Tables.
- DAB: Databricks Asset Bundle.
- UC: Unity Catalog.
- ADLS: Azure Data Lake Storage gen2.
- OIDC federation: autenticação sem senha entre clouds.
```

---

### 7.2 DevOps / Platform Engineer

```
# CLAUDE.md — Platform Engineering

## Arquitetura
Kubernetes (EKS) → ArgoCD (GitOps) → Terraform (IaC) → Prometheus/Grafana (observability)

## Ambientes
dev, staging, prod (isolamento via AWS Account + VPC).

## Stack
- Terraform para IaC (módulos em infra/modules/).
- ArgoCD para deploy (app-of-apps pattern).
- Helm para packaging de charts.
- kustomize para overlay de ambientes.

## Fluxo de deploy
1. PR com mudança → make plan → approval.
2. Merge → make apply → terraform state atualizado.
3. ArgoCD detecta drift → sync automática em dev/staging.
4. Prod: sync manual após validação.

## Convenções de Terraform
- Estado remoto: S3 + DynamoDB (lock).
- Módulos versionados com git tags.
- Nomenclatura: <project>-<env>-<component>.

## Comandos
make plan ENV=dev        # terraform plan
make apply ENV=dev        # terraform apply (DEV apenas)
make validate-chart       # helm lint + kubeval
make argocd-sync APP=...  # argoapp sync manual

## Gotchas
- NUNCA rodar apply em prod sem approval explícito.
- Lock de state: se make apply travar, verificar DynamoDB.
- Drift entre Terraform e ArgoCD: ArgoCD vence (GitOps source of truth).
```

---

### 7.3 Data Scientist

```
# CLAUDE.md — Data Science

## Arquitetura
Raw data (S3) → Feature store (Feast) → Training (SageMaker) → Model registry → Inference

## Estrutura
src/features/     — Feature definitions (Feast).
src/training/     — Scripts de treino (scikit-learn, PyTorch).
src/inference/    — Batch e real-time inference.
models/           — Model registry (MLflow).
data/features/    — Feature store (parquet).

## Convenções
- Features versionadas via Feast + Parquet (não em tabelas SQL).
- Treino: sempre usar seed固定的 (reproducibilidade).
- Métricas de validação: ROC-AUC + PR-AUC, não apenas accuracy.
- Dados de teste: nunca ver dados de treino (TS fresh split).

## Comandos
make features          # gerar feature set
make train MODEL=...   # treinar modelo
make validate          # cross-validation + métricas
make serve             # subir endpoint local

## MLflow
- Tracking URI: <MLFLOW_TRACKING_URI>
- Experiment padrão: <DEFAULT_EXPERIMENT>
- Aliases: champion, challenger (para A/B).

## Observabilidade
- Data drift: Evidently AI (Dashboards em Grafana).
- Model drift: retrainar quando PR-AUC < 0.7.

## Glossário
- Feature store: repositório centralizado de features.
- Online store: Redis (low-latency inference).
- Offline store: S3 (batch training).
- SVR: Schema View Registration (monitoramento de drift).
```

---

## 8. Fluxo de manutenção

O CLAUDE.md é um documento vivo. Para mantê-lo útil:

### Gatilhos de atualização

Adicione uma regra ao time:

> **Whenever you change infrastructure, architecture, or operational procedures, update CLAUDE.md in the same PR.**

Isso pode ser enforcing via checklist no template de PR:

```
- [ ] CLAUDE.md atualizado (se aplicável)
```

### Revisões periódicas

- **Semestral**: leitura completa do CLAUDE.md pelo time, com proposta de updates.
- **Trimestral**: remover gotchas resolvidas, adicionar aprendizados do trimestre.
- **Após incidentes**: toda falha recorrente vira gotcha; todo runbook vira seção operacional.

### Métricas de saúde

- **Staleness score**: fração de seções sem atualização em 6 meses.
- **Cobertura de gotchas**: razão entre falhas recorrentes e gotchas documentadas
  (idealmente > 0.8: a maioria das falhas recorrentes está documentada).

---

## 9. Ferramentas complementares

### Skills (`.claude/skills/`)

Procedimentos detalhados com checklist, invocáveis via `/skill-name`.

**Para o cenário data engineer:**
- `spark-optimizer/` — heurísticas de performance Spark.
- `dlt-patterns/` — CDC, SCD2, expectations em DLT.
- `bigquery-sql/` — armadilhas do BigQuery.
- `cost-guardrail/` — detecção de padrões custosos.

**Como criar:**

```
.claude/skills/
└── spark-optimizer/
    └── SKILL.md   # instruções detalhadas
```

### Memória (`memory/`)

Fatos duráveis que o Claude Code lembra **entre sessões**. Diferente do CLAUDE.md
(versionado, por repo), a memória é **local e pessoal** (não commitada).

**Quando usar memória:**
- Preferências pessoais do usuário (não do time).
- Contexto cross-repo (ex.: "o usuário trabalha com Python 3.11").
- Fatos sobre o usuário que informam como se comunicar (ex.: "prefere explicações curtas").

**Formato:**

```markdown
---
name: <slug>
description: <resumo de uma linha>
metadata:
  type: user | feedback | project | reference
---

<conteúdo>
```

### MCP servers (Model Context Protocol)

Conectam serviços externos (GCP, Databricks, Azure) diretamente ao Claude Code.

**Configuração em `settings.json`:**

```json
{
  "mcpServers": {
    "databricks": {
      "command": "npx",
      "args": ["-y", "@databricks/mcp"]
    }
  }
}
```

**Benefício:** o Claude pode ler jobs, logs, executar queries — não apenas falar sobre eles.

---

## Referências

- [Documentação oficial do Claude Code — CLAUDE.md](https://docs.anthropic.com/en/docs/claude-code)
- [Skills do Claude Code](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Memory no Claude Code](https://docs.anthropic.com/en/docs/claude-code/memory)
- [MCP — Model Context Protocol](https://modelcontextprotocol.io/)
