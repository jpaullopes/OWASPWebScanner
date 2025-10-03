# Operação e automação

Esta seção orienta a execução do scanner em diferentes cenários, como auditorias pontuais, execução parcial de etapas e automação em pipelines.

## CLI e parâmetros suportados

Com o projeto instalado (`pip install -e '.[dev]'`), o comando principal disponível é:

```bash
owasp-web-scanner -u http://alvo.local [--callback-port 8000] [--report caminho/do/relatorio.json]
```

| Flag             | Tipo   | Descrição                                                                                     |
|------------------|--------|-------------------------------------------------------------------------------------------------|
| `-u, --url`      | str    | **Obrigatória**. URL base do alvo. O caminho é normalizado retirando barras finais duplicadas. |
| `--callback-port`| int    | Porta utilizada pelo servidor de callback de XSS (padrão: `8000`).                             |
| `--report`       | str    | Caminho para o arquivo JSON que consolida o reconhecimento (padrão: `relatorio_spider.json`). |
| `--verbose-ffuf` | flag   | Exibe o output completo da enumeração de diretórios (`ffuf`).                                |
| `--verbose-sql`  | flag   | Habilita a saída detalhada do `sqlmap` durante o fuzzing de SQLi.                            |
| `--sql-timeout`  | int    | Tempo máximo, em segundos, para cada alvo analisado pelo `sqlmap` (padrão: `120`).           |

### Saída padrão

Durante a execução, a CLI imprime o andamento do pipeline:

Antes da sequência numerada, a CLI valida se `sqlmap`, `ffuf` e `dalfox` estão disponíveis no `PATH`.

1. **Reconhecimento**: o crawler Scrapy integra o Playwright para navegar de forma dinâmica, captura formulários/cookies e grava o relatório.
2. **Servidor de callback**: inicialização e URL de escuta utilizada pelos payloads de XSS.
3. **SQL Injection**: resultado por alvo (`VULNERÁVEL` ou `OK`).
4. **XSS (Playwright)**: logs de eco para cada campo (`<-` refletiu, `~` refletiu mas foi ignorado, `X` sem reflexão) e payloads realmente injetados.
5. **Dalfox XSS**: fuzzing complementar com o binário `dalfox`, exibindo payloads e PoCs retornados.
6. **Análise de acesso**: URLs acessíveis inesperadamente.

## Execução parcial de etapas

Os módulos podem ser executados de forma isolada dentro de scripts Python personalizados:

```python
from pathlib import Path
from owasp_scanner.core.config import load_configuration
from owasp_scanner.core.report import ReconReport
from owasp_scanner.recon.crawler import Spider
from owasp_scanner.scanners.sql.runner import run_sql_scanner
from owasp_scanner.scanners.xss.runner import run_xss_scanner
from owasp_scanner.scanners.dalfox import run_dalfox_scanner
from owasp_scanner.access.analyzer import run_access_analyzer

config = load_configuration("http://alvo.local")
report = Spider(config).run()
report.save(Path(config.report_path))

sql_results = run_sql_scanner(report.as_sql_targets())
xss_results = run_xss_scanner(config, report.as_xss_targets(), "http://localhost:8000")
dalfox_results = run_dalfox_scanner(config, report.as_xss_targets())
access_results = run_access_analyzer(config, report.as_access_targets())
accessible_urls = access_results.accessible_urls
```

Essa abordagem é útil quando você deseja integrar o scanner a um orquestrador externo ou depurar apenas um estágio.

## Uso de relatórios pré-existentes

Como `ReconReport` pode ser salvo e carregado de disco (`ReconReport.save()` / `ReconReport.load()`), é possível reutilizar dados coletados anteriormente sem refazer o crawling:

```python
from pathlib import Path
from owasp_scanner.core.report import ReconReport
from owasp_scanner.scanners.sql.runner import run_sql_scanner

report = ReconReport.load(Path("relatorio_spider.json"))
results = run_sql_scanner(report.as_sql_targets())
```

## Execução headless vs interativa

- Defina `HEADLESS=true` para manter o navegador sem interface (padrão).
- Para depuração visual, exporte `HEADLESS=false` ou `HEADLESS=0`; o Playwright abrirá uma janela visível.

## Automação e CI/CD

1. **Configuração do ambiente**
   - Use uma imagem base com Python 3.12.
   - Instale `sqlmap`, `ffuf` e os navegadores Playwright (
     `playwright install --with-deps` em ambientes Linux headless).

2. **Etapas típicas do pipeline**

   ```bash
   pip install -e '.[dev]'
   playwright install --with-deps
   pytest
   owasp-web-scanner -u http://alvo.ci --report relatorio-ci.json --callback-port 8080
   ```

3. **Artefatos**
   - Publique `relatorio_spider.json` (ou o nome definido) como artefato de build.
   - Opcionalmente, armazene stdout/stderr para auditoria.

## Segurança operacional

- Execute o scanner apenas em ambientes onde você tem autorização explícita.
- O módulo de XSS injeta payloads que fazem requisições HTTP para o servidor de callback; garanta que a porta esteja acessível apenas internamente.
- Avalie políticas de rate-limit do alvo para ajustar timeouts e número de threads (SQLi/XSS usam defaults conservadores, mas podem ser customizados na camada de código).

## Monitoramento e logging

Atualmente, o projeto oferece logs simples via `print`. Para integrações corporativas:

- Substitua `print` por um logger estruturado (por exemplo, `logging.Logger`).
- Envolva as chamadas de scanners em blocos `try/except` personalizando alertas ou notificações.
- Utilize os dicionários retornados (`SqlScanResult`, payloads XSS) para gerar métricas em dashboards externos.
