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
