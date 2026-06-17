# Assistente Pessoal

Projeto de assistente pessoal em Python com interação por terminal, suporte a memória de conversa e ferramentas para preferências e controle de calorias.

## Visão geral

Este projeto implementa um assistente conversacional que:

- Recebe mensagens do usuário via terminal.
- Mantém contexto de conversa com checkpoint.

## Funcionalidades principais

- Chat contínuo no terminal (`main.py`).
- Middleware para reduzir histórico e injetar preferências no contexto.
- Tools para preferências.
- Tools para contagem de calorias.
- Tools utilitárias.
- Persistência local com SQLite.

## Tecnologias usadas

- Python 3.14+
- LangChain
- LangGraph
- Google Generative AI
- SQLite
- Pydantic

## Estrutura do projeto

```text
.
├── assistant.py
├── main.py
├── pyproject.toml
├── databases/
└── tools/
		├── calories.py
		├── date.py
		└── preferences.py
```

## Execução (resumo)

1. Configure as variáveis de ambiente necessárias (ex.: banco e chave de API).
2. Instale as dependências do projeto.
3. Execute:

```bash
python main.py
```

Para sair do chat, digite `exit` ou `quit`.

## Instalação de dependências

Na raiz do projeto, ative seu ambiente virtual e instale as depêndencias pelo uv.

```bash
source .venv/Scripts/activate
pip install uv
uv sync
```

## Gateway do Telegram

### 1. Criar o bot

1. Abra o Telegram e converse com o BotFather.
2. Execute o comando `/newbot`.
3. Defina nome e username do bot.
4. Copie o token gerado.

### 2. Configurar variáveis de ambiente

Defina no seu ambiente (ou em `.env`):

- `TELEGRAM_BOT_TOKEN`: token recebido do BotFather.
- `ALLOWED_USERS`: lista de IDs permitidos (ex.: `[123456789,987654321]`). Use `[]` para liberar acesso a qualquer usuário.

### 3. Executar

```bash
python -m gateways.telegram_gateway
```

Depois disso, envie uma mensagem para o seu bot no Telegram.

# Deploy — Assistente Pessoal

## 1. Preparar o servidor de producao

No servidor Linux:

1. Clone o repositorio em `/opt/assistente-pessoal` e ajuste o dono:

```bash
sudo git clone <url-do-repo> /opt/assistente-pessoal
sudo chown -R deploy:deploy /opt/assistente-pessoal
```

2. Instale Python 3.14+ e `uv`.

3. Dentro do diretorio, rode `uv sync` para criar o `.venv` antes do primeiro start:

```bash
cd /opt/assistente-pessoal
uv sync
```

4. Configure as variaveis de ambiente da aplicacao (`.env`).

Sugestao: copie o `.env.example` para `.env` e ajuste os valores:

```bash
cp .env.example .env
```

Minimo recomendado para producao:

- `GOOGLE_API_KEY`
- `ASSISTANT_DB`
- `CHECKPOINTER_DB`
- `TELEGRAM_BOT_TOKEN`
- `ALLOWED_USERS`
- `RUN_INTERACTIVE_CONSOLE=false` (quando rodar via `systemd`)

5. Permita que o usuario `deploy` reinicie o servico sem senha. Crie o arquivo `/etc/sudoers.d/deploy`:

```
Defaults:deploy !use_pty
deploy ALL=(ALL) NOPASSWD: \
  /usr/bin/systemctl restart assistente-pessoal, \
  /usr/bin/systemctl is-active assistente-pessoal, \
  /usr/bin/systemctl status assistente-pessoal
```

6. Configure um servico `systemd` para manter a aplicacao em execucao.

Exemplo de servico (`/etc/systemd/system/assistente-pessoal.service`):

```ini
[Unit]
Description=Assistente Pessoal
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/assistente-pessoal
Environment=RUN_INTERACTIVE_CONSOLE=false
ExecStart=/opt/assistente-pessoal/.venv/bin/python /opt/assistente-pessoal/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl enable assistente-pessoal
sudo systemctl start assistente-pessoal
```

---

## 2. Configurar credenciais no Jenkins

Crie estas credenciais no Jenkins:

- `prod-ssh-key`: chave SSH com acesso ao servidor de producao.
- `prod-deploy-host`: host/IP do servidor (Secret text).
- `prod-deploy-user`: usuario SSH do deploy (Secret text).

---

## 3. Configurar o job no Jenkins

O pipeline usa **polling** para detectar novos commits: a cada 2 minutos o Jenkins verifica se ha mudancas na branch `prod` e, se houver, dispara o deploy automaticamente.

Nenhuma configuracao extra de rede e necessaria no servidor — o Jenkins e quem inicia a conexao.

> O pipeline bloqueia deploy automaticamente em qualquer branch diferente de `prod`.

---

## 4. Fluxo final

Ao dar push em `prod`:

1. Jenkins detecta o novo commit via polling (ate 2 minutos de delay).
2. Executa o `Jenkinsfile`.
3. Conecta via SSH no servidor.
4. Executa `scripts/deploy_prod.sh`.
5. Verifica se ha mudancas desde o ultimo deploy; encerra sem acao se nao houver.
6. Atualiza o codigo para `origin/prod`.
7. Reinstala dependencias com `uv sync --frozen --no-dev`.
8. Reinicia o servico `assistente-pessoal`.
9. Confirma que o servico esta ativo; executa rollback automatico em caso de falha.
