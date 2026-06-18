#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${APP_SERVICE_NAME:-assistente-pessoal}"

echo "[deploy] Iniciando deploy em $(date '+%Y-%m-%d %H:%M:%S')"
echo "[deploy] Servico alvo: ${SERVICE_NAME}"

# ---------------------------------------------------------------------------
# Validacoes de dependencias
# ---------------------------------------------------------------------------

if ! command -v git >/dev/null 2>&1; then
  echo "[deploy] ERRO: git nao encontrado no servidor"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[deploy] ERRO: uv nao encontrado no servidor"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[deploy] ERRO: systemctl nao encontrado. Configure outro gerenciador de processo."
  exit 1
fi

# ---------------------------------------------------------------------------
# Guarda commit anterior para rollback
# ---------------------------------------------------------------------------

PREVIOUS_COMMIT=$(git rev-parse HEAD)
echo "[deploy] Commit atual (pre-deploy): ${PREVIOUS_COMMIT}"

rollback() {
  echo "[deploy] ERRO detectado. Iniciando rollback para ${PREVIOUS_COMMIT}..."
  git reset --hard "$PREVIOUS_COMMIT"
  sudo systemctl restart "$SERVICE_NAME" || true
  echo "[deploy] Rollback concluido."
  exit 1
}

trap rollback ERR

# ---------------------------------------------------------------------------
# Atualiza codigo
# ---------------------------------------------------------------------------

echo "[deploy] Atualizando codigo da branch prod..."
git fetch origin prod
git checkout prod
git reset --hard origin/prod

NEW_COMMIT=$(git rev-parse HEAD)
echo "[deploy] Novo commit (pos-deploy): ${NEW_COMMIT}"

if [ "$PREVIOUS_COMMIT" = "$NEW_COMMIT" ]; then
  echo "[deploy] Nenhuma mudanca detectada. Deploy desnecessario."
  trap - ERR
  exit 0
fi

# ---------------------------------------------------------------------------
# Atualiza dependencias
# ---------------------------------------------------------------------------

echo "[deploy] Sincronizando dependencias..."
uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Reinicia servico
# ---------------------------------------------------------------------------

echo "[deploy] Reiniciando servico '${SERVICE_NAME}'..."
sudo systemctl restart "$SERVICE_NAME"
sleep 3

if ! sudo systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "[deploy] ERRO: servico nao subiu apos restart."
  sudo systemctl status "$SERVICE_NAME" --no-pager
  exit 1
fi

# ---------------------------------------------------------------------------
# Sucesso
# ---------------------------------------------------------------------------

trap - ERR
echo "[deploy] Servico '${SERVICE_NAME}' ativo e saudavel."
echo "[deploy] Deploy concluido com sucesso em $(date '+%Y-%m-%d %H:%M:%S')"