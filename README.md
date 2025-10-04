# OWASP Web Scanner

![Status](https://img.shields.io/badge/status-em%20construção-yellow)
![Python](https://img.shields.io/badge/language-Python-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OWASP](https://img.shields.io/badge/OWASP-Top%2010-critical)

Ferramenta educacional focada em demonstrar técnicas de reconhecimento e exploração das principais vulnerabilidades do OWASP Top 10. O projeto foi testado com a aplicação [OWASP Juice Shop](https://github.com/juice-shop/juice-shop.git) e serve como laboratório controlado para estudantes e entusiastas de segurança web.

## ✨ Principais funcionalidades

- Reconhecimento automatizado com Playwright (coleta de links, formulários e cookies).
- Enumeração de diretórios usando `ffuf`.
- Execução de sqlmap em possíveis parâmetros vulneráveis.
- Injeção de payloads de XSS e monitoramento via servidor de callback embutido.
- Validação de controle de acesso em URLs descobertas.
- Relatório unificado (`relatorio_spider.json`) compartilhado entre todas as etapas.

## ⚙️ Pré-requisitos

- Python 3.12+
- Navegadores do Playwright (`playwright install` após a instalação das dependências Python)
- Ferramentas externas disponíveis no `PATH`:
  - [`sqlmap`](https://sqlmap.org/) – `apt install sqlmap` ou `pip install sqlmap`
  - [`ffuf`](https://github.com/ffuf/ffuf) – `go install github.com/ffuf/ffuf@latest`

## 🚀 Instalação

Instalação rápida:

```bash
git clone https://github.com/jpaullopes/OWASPWebScanner.git
cd OWASPWebScanner

# Instala as dependências Python em modo editável
pip install -e .

# Baixa os navegadores necessários para o Playwright
playwright install
```

Crie um arquivo `.env` (opcional) na raiz do projeto com variáveis auxiliares:

```ini
SESSION_COOKIE=nome_cookie=valor
EMAIL_LOGIN=usuario@example.com
PASSWORD_LOGIN=minha_senha
HEADLESS=true
```

## 🕹️ Uso

### CLI principal

O orquestrador completo está exposto como console script e também via `main.py` para compatibilidade local:

```bash
# Forma recomendada
owasp-web-scanner -u http://alvo.exemplo

# Equivalente
python main.py -u http://alvo.exemplo
```

Argumentos relevantes:

| Opção | Descrição |
| ----- | --------- |
| `-u, --url` | URL base do alvo (obrigatório) |
| `--callback-port` | Porta para o servidor de callback (padrão: 8000) |
| `--report` | Nome do arquivo de relatório (padrão: `relatorio_spider.json`) |

### Execução manual de etapas

Cada módulo pode ser executado separadamente importando diretamente o pacote:

```python
from pathlib import Path
from owasp_scanner.core.config import load_configuration
from owasp_scanner.core.report import ReconReport
from owasp_scanner.recon.crawler_legacy import Spider
from owasp_scanner.scanners.sql.runner import run_sql_scanner
from owasp_scanner.scanners.xss.runner import run_xss_scanner
from owasp_scanner.access.analyzer import run_access_analyzer

config = load_configuration("http://alvo.exemplo")
report = Spider(config).run()
report.save(Path(config.report_path))
sql_results = run_sql_scanner(report.as_sql_targets())
xss_results = run_xss_scanner(config, report.as_xss_targets(), "http://localhost:8000")
access_results = run_access_analyzer(config, report.as_access_targets())
accessible = access_results.accessible_urls
```

## 🗂️ Estrutura do projeto

```text
src/owasp_scanner/
  core/           # Configuração, verificação de dependências e modelo de relatório
  recon/          # Crawler com Playwright e enumeração de diretórios (ffuf)
  scanners/
    sql/          # Execução de sqlmap
    xss/          # Injeção e monitoramento de payloads XSS
  callback/       # Servidor HTTP para callbacks de Blind XSS
  access/         # Validação de Broken Access Control
  resources/      # Wordlists e arquivos auxiliares
  cli.py          # Orquestrador da linha de comando
```

O relatório `relatorio_spider.json` é salvo na raiz do projeto (ou no caminho configurado) e contém todas as descobertas para reutilização posterior.

A base de código ativa vive inteiramente em `src/owasp_scanner/`. Estruturas
anteriores como `src/modules/` foram mantidas apenas para referência histórica e
não participam mais da execução.

## 🧪 Testes

O repositório possui uma suíte de testes unitários construída com `pytest`, cobrindo os componentes centrais (configuração, relatório, analisadores e utilidades). Para executá-los:

```bash
pip install -e .[dev]
pytest
```

## 📚 Documentação completa

Encontrou um overview rápido aqui, mas a documentação completa (guia de início, arquitetura, referência de módulos, automação e troubleshooting) está disponível em [`docs/`](docs/index.md).

## 🤝 Contribuindo

Pull requests são bem-vindos! Abra uma issue descrevendo o problema ou sugestão e certifique-se de executar o scanner apenas em ambientes para os quais você possui autorização explícita.

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.
