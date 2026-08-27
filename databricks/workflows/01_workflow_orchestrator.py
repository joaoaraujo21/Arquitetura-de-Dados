# Databricks notebook source
# MAGIC %md
# MAGIC # Workflow Orchestrator
# MAGIC
# MAGIC Orquestrador de tasks usando Databricks Workflows e Jobs API.

# COMMAND ----------

import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime

# COMMAND ----------

class DatabricksJobsAPI:
    """Cliente para a API de Jobs do Databricks."""

    def __init__(self, host: str, token: str):
        self.host = host.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def create_job(self, job_config: Dict) -> int:
        """Cria um novo job."""
        response = requests.post(
            f"{self.host}/api/2.1/jobs/create",
            headers=self.headers,
            json=job_config
        )
        response.raise_for_status()
        return response.json()["job_id"]

    def run_job_now(self, job_id: int, notebook_params: Optional[Dict] = None) -> int:
        """Dispara execução imediata de um job."""
        payload = {"job_id": job_id}
        if notebook_params:
            payload["notebook_params"] = notebook_params

        response = requests.post(
            f"{self.host}/api/2.1/jobs/run-now",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()["run_id"]

    def get_run_status(self, run_id: int) -> Dict:
        """Obtém status de uma execução."""
        response = requests.get(
            f"{self.host}/api/2.1/jobs/runs/get",
            headers=self.headers,
            params={"run_id": run_id}
        )
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, run_id: int, timeout_seconds: int = 3600) -> Dict:
        """Aguarda conclusão de uma execução."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            status = self.get_run_status(run_id)
            life_cycle = status.get("state", {}).get("life_cycle_state")

            if life_cycle in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
                result_state = status.get("state", {}).get("result_state")
                return {
                    "run_id": run_id,
                    "life_cycle_state": life_cycle,
                    "result_state": result_state,
                    "duration_ms": status.get("execution_duration", 0)
                }

            time.sleep(30)

        raise TimeoutError(f"Job {run_id} não finalizou em {timeout_seconds}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Definição de Pipeline Completo

# COMMAND ----------

# Configuração do pipeline de ingestão + transformação
ingestion_pipeline = {
    "name": "openrouter_daily_ingestion",
    "max_concurrent_runs": 1,
    "schedule": {
        "quartz_cron_expression": "0 0 2 * * ?",  # 2h da manhã todo dia
        "timezone_id": "America/Sao_Paulo"
    },
    "email_notifications": {
        "on_failure": ["dataeng@example.com"],
        "no_alert_for_skipped_runs": False
    },
    "tasks": [
        {
            "task_key": "ingest_api_data",
            "description": "Ingere dados de APIs externas",
            "notebook_task": {
                "notebook_path": "/Workspace/openrouter/notebooks/ingestion/01_ingest_raw_data",
                "base_parameters": {
                    "source": "api",
                    "incremental": "true"
                }
            },
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 2,
                "data_security_mode": "SINGLE_USER"
            }
        },
        {
            "task_key": "ingest_s3_data",
            "description": "Ingere dados do S3",
            "depends_on": [{"task_key": "ingest_api_data"}],
            "notebook_task": {
                "notebook_path": "/Workspace/openrouter/notebooks/ingestion/01_ingest_raw_data",
                "base_parameters": {
                    "source": "s3",
                    "incremental": "true"
                }
            },
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 2,
                "data_security_mode": "SINGLE_USER"
            }
        },
        {
            "task_key": "transform_silver",
            "description": "Transforma dados bronze para silver",
            "depends_on": [
                {"task_key": "ingest_api_data"},
                {"task_key": "ingest_s3_data"}
            ],
            "notebook_task": {
                "notebook_path": "/Workspace/openrouter/notebooks/transformation/02_transform_silver"
            },
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 4,
                "data_security_mode": "SINGLE_USER"
            }
        },
        {
            "task_key": "transform_gold",
            "description": "Cria agregações gold",
            "depends_on": [{"task_key": "transform_silver"}],
            "notebook_task": {
                "notebook_path": "/Workspace/openrouter/notebooks/transformation/03_transform_gold"
            },
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 4,
                "data_security_mode": "SINGLE_USER"
            }
        },
        {
            "task_key": "data_quality_checks",
            "description": "Valida qualidade dos dados gold",
            "depends_on": [{"task_key": "transform_gold"}],
            "notebook_task": {
                "notebook_path": "/Workspace/openrouter/notebooks/quality/04_quality_checks"
            },
            "new_cluster": {
                "spark_version": "13.3.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "num_workers": 2,
                "data_security_mode": "SINGLE_USER"
            }
        }
    ],
    "tags": {
        "project": "openrouter",
        "environment": "production",
        "team": "data-engineering"
    }
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy do Pipeline

# COMMAND ----------

# Configuração
DATABRICKS_HOST = dbutils.secrets.get(scope="openrouter", key="databricks_host")
DATABRICKS_TOKEN = dbutils.secrets.get(scope="openrouter", key="databricks_token")

# Inicializa API client
jobs_api = DatabricksJobsAPI(DATABRICKS_HOST, DATABRICKS_TOKEN)

# Cria ou atualiza job
try:
    job_id = jobs_api.create_job(ingestion_pipeline)
    print(f"Job criado com ID: {job_id}")
except Exception as e:
    print(f"Erro ao criar job: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execução Manual

# COMMAND ----------

# Exemplo: executar job manualmente com parâmetros customizados
# run_id = jobs_api.run_job_now(
#     job_id=job_id,
#     notebook_params={"execution_date": datetime.now().isoformat()}
# )
# result = jobs_api.wait_for_completion(run_id, timeout_seconds=7200)
# print(f"Execução finalizada: {result}")
