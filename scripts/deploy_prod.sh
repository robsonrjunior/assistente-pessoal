#!/usr/bin/env bash
set -euo pipefail

echo "[deploy] Iniciando deploy em $(date '+%Y-%m-%d %H:%M:%S')"

if ! command -v git >/dev/null 2>&1; then
  echo "[deploy] ERRO: git nao encontrado no servidor"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[deploy] ERRO: uv nao encontrado no servidor"
  exit 1
fi

git fetch origin prod
git checkout prod
git reset --hard origin/prod

uv sync

SERVICE_NAME="${APP_SERVICE_NAME:-assistente-pessoal}"

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart "${SERVICE_NAME}"
  sudo systemctl is-active --quiet "${SERVICE_NAME}"
  echo "[deploy] Servico '${SERVICE_NAME}' reiniciado com sucesso"
else
  echo "[deploy] ERRO: systemctl nao encontrado. Configure outro gerenciador de processo."
  exit 1
fi

echo "[deploy] Deploy concluido"
