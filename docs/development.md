# Guia de desenvolvimento

Este guia destina-se a contribuintes e mantenedores interessados em evoluir o projeto.

## Preparando o ambiente de desenvolvimento

1. Crie um ambiente virtual dedicado:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instale o projeto com dependências de desenvolvimento:

   ```bash
   pip install -e '.[dev]'
   ```

3. Baixe os navegadores do Playwright (necessários para testes de integração envolvendo crawling/XSS):

   ```bash
   playwright install
   ```

## Estrutura de diretórios

```text
src/owasp_scanner/      # Código-fonte principal
  core/                 # Configuração, relatório e verificação de dependências
  recon/                # Crawler, enumeração de diretórios e utilidades
  scanners/sql/         # Runner de SQL Injection (sqlmap)
  scanners/xss/         # Scanner de XSS com Playwright
  access/               # Verificação de Broken Access Control
  callback/             # Servidor HTTP para blind XSS
  auth/                 # Helpers de login (Playwright)
resources/              # Wordlists e artefatos estáticos
tests/unit/             # Testes unitários com pytest
```

## Convenções de código

- Python 3.12, tipagem opcional com `from __future__ import annotations`.
- Limite de 90 caracteres por linha (configurado no `pyproject.toml` via Ruff).
- Siga a filosofia "fail-safe": capture exceções externas (HTTP, subprocessos, Playwright) e reporte sem abortar a execução global, exceto quando necessário.
- Prefira funções puras reutilizáveis (por exemplo, `run_sql_scanner`, `run_xss_scanner`) para facilitar testes.

## Testes

- **Execução**: `pytest`
- Estrutura:
  - `tests/unit/test_config.py`: carga de configuração e variáveis de ambiente.
  - `tests/unit/test_report.py`: serialização/armazenamento do `ReconReport`.
  - `tests/unit/test_sql_runner.py`: montagem de comandos `sqlmap` e parsing do resultado.
  - `tests/unit/test_utils.py`: helpers genéricos (`build_cookie_header`).
  - `tests/unit/test_access_analyzer.py`: lógica de sessão e validação de URLs.
  - `tests/unit/test_dependencies.py`: checagem de ferramentas externas.
- Os testes usam `monkeypatch` e fixtures temporárias para isolar efeitos colaterais (subprocessos, rede, login).

> Dica: configure a variável `HEADLESS=false` ao depurar Playwright manualmente, permitindo observar o navegador.

## Lint e formatação

- Ruff (linters E/F/I) é instalado pelo extra `dev`. Execute:

  ```bash
  ruff check src tests
  ```

- Para formatação consistente, habilite uma extensão como `ruff` ou `black` no seu editor. O projeto não impõe formatação automática, mas mantém linting ativo.

## Documentação

- A documentação oficial vive em `docs/`. Ao adicionar recursos importantes, atualize ou crie novas páginas.
- É possível migrar para uma doc gerada com Sphinx (já listado em `pyproject.toml`) se desejar HTML/PDF; por ora, os arquivos Markdown servem como fonte única.

## Processos de contribuição

1. Crie uma branch a partir de `main`.
2. Faça commits descritivos e inclua testes sempre que alterar lógica.
3. Garanta que `pytest` e `ruff check` passam antes de abrir uma pull request.
4. Atualize a documentação (`README.md` e `docs/`) conforme necessário.

## Releases e versionamento

- A versão atual é definida em `pyproject.toml`. Siga o versionamento semântico (`MAJOR.MINOR.PATCH`).
- Empacotamento e publicação podem ser feitos com `build`/`twine` caso o projeto seja disponibilizado no PyPI.

## Próximos passos sugeridos

- Registrar logs estruturados em vez de `print`.
- Adicionar testes de integração que exercitem Playwright via `pytest-playwright`.
- Suportar wordlists customizadas via CLI.
- Exportar resultados em formatos adicionais (por exemplo, CSV ou HTML).
