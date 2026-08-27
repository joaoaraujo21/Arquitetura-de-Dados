#!/bin/bash
# Script para criar o repositório e fazer push para o GitHub
# Uso: ./push_to_github.sh SEU_TOKEN

set -e

TOKEN="$1"
if [ -z "$TOKEN" ]; then
  echo "Uso: $0 <github_token>"
  exit 1
fi

REPO_NAME="Arquitetura-de-Dados"
USER="joaoaraujo21"

echo "==> Criando repositório $REPO_NAME..."
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO_NAME\",\"description\":\"Estrutura de projeto para engenharia de dados com suporte a Databricks (Notebooks, DLT, dbt, Unity Catalog) e execucao local seguindo arquitetura medalhao (Bronze/Silver/Gold)\",\"private\":false}"

echo ""
echo "==> Configurando remote..."
cd "$(dirname "$0")"
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USER:$TOKEN@github.com/$USER/$REPO_NAME.git"
git branch -M main

echo "==> Fazendo push..."
git push -u origin main

echo "==> Sucesso! Repositório disponível em:"
echo "https://github.com/$USER/$REPO_NAME"
