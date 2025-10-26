# Guia de início rápido

Este guia cobre os passos necessários para preparar o ambiente, instalar dependências e executar o OWASP Web Scanner pela primeira vez.

## Requisitos de sistema

- **Sistema operacional**: Linux ou macOS (recomendado). Para Windows, sugerimos WSL2.
- **Python**: versão 3.12 ou superior.
- **Ferramentas externas** (instalação obrigatória para funcionalidades completas):
  - [`sqlmap`](https://sqlmap.org/) — utilitário para exploração de SQL Injection.
  - [`ffuf`](https://github.com/ffuf/ffuf) — fuzzing de diretórios/arquivos.
- **Playwright**: os navegadores serão baixados automaticamente via `playwright install`.

## Preparando o ambiente Python

1. Clone o repositório e entre no diretório raiz:

   ```bash
   git clone https://github.com/jpaullopes/OWASPWebScanner.git
   cd OWASPWebScanner
   ```

2. Crie e ative um ambiente virtual dedicado:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale o projeto em modo editável com as dependências de desenvolvimento (pytest, ruff, sphinx):

   ```bash
   pip install -e '.[dev]'
   ```

4. Baixe os navegadores necessários para o Playwright:

   ```bash
   playwright install
   ```

## Variáveis de ambiente suportadas

As etapas de reconhecimento e autenticação podem ser customizadas via variáveis carregadas do ambiente ou de um arquivo `.env` na raiz do projeto:

| Variável            | Descrição                                                                                         |
|--------------------|---------------------------------------------------------------------------------------------------|
| `SESSION_COOKIE`    | Cookie de sessão (`nome=valor`) usado para autenticação sem interação de login.                   |
| `EMAIL_LOGIN`       | E-mail utilizado no formulário de login.                                                          |
| `PASSWORD_LOGIN`    | Senha associada ao e-mail informado.                                                              |
| `HEADLESS`          | Define se o Playwright deve rodar em modo headless (`true`, `1`, `yes` ativam o comportamento).   |

> Caso nenhuma variável seja definida, o crawler tentará o login de demonstração do OWASP Juice Shop (`admin@juice-sh.op` / `admin123`).

## Execução básica

Após instalar as dependências:

```bash
owasp-web-scanner -u http://alvo.local
```

ou, alternativamente:

```bash
python main.py -u http://alvo.local
```

O relatório consolidado (`relatorio_spider.json`) será gravado na raiz do projeto ou no caminho especificado pela flag `--report`.

## Verificando a instalação

1. Valide as dependências externas:

   ```bash
   sqlmap --version
   ffuf -V
   ```

2. Rode a suíte de testes para garantir que o ambiente está saudável:

   ```bash
   pytest
   ```

3. Opcional: execute `ruff` para verificar o estilo do código:

   ```bash
   ruff check src tests
   ```

Com esses passos, o ambiente estará pronto para exploração, automação ou desenvolvimento contínuo.
