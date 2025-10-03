# Referência de módulos e APIs

Esta referência resume os principais pacotes do projeto, destacando classes, funções e responsabilidades. Use-a como ponto de partida para navegar pelo código-fonte em `src/owasp_scanner`.

## CLI (`owasp_scanner.cli`)

| Símbolo                | Tipo     | Descrição                                                                                 |
|------------------------|----------|-------------------------------------------------------------------------------------------|
| `parse_arguments()`    | Função   | Cria o parser `argparse` e retorna os parâmetros CLI.                                     |
| `print_dependency_status()` | Função | Executa `verify_dependencies()` e imprime um resumo legível das ferramentas externas.     |
| `run_cli()`            | Função   | Orquestra o pipeline completo: reconhecimento, callback server, SQLi, XSS e acesso.      |
| `main()`               | Função   | Entry point compatível com console script (`owasp-web-scanner`).                         |

## Núcleo (`owasp_scanner.core`)

### `config.py`

- `ScannerConfig`: dataclass que agrega opções como URL alvo, cookie de sessão, caminho do relatório, modo headless e credenciais.
- `load_configuration(target_url, report_name="relatorio_spider.json")`: carrega variáveis do ambiente/`.env`, normaliza URLs e retorna um `ScannerConfig` pronto para uso.

### `report.py`

- `ReconReport`: dataclass com coleções para SQLi, XSS, análise de acesso e cookies.
  - `to_json()`: serializa o relatório em JSON legível.
  - `save(path)`: persiste o JSON em disco.
  - `load(path)`: carrega um relatório previamente gerado.

### `models.py`

- `FieldAttributes`: `TypedDict` com atributos opcionais (`id`, `name`, `placeholder`, `aria_label`, `data_testid`, `type`, `tag`) usados para reidentificar inputs.
- `FieldInfo`: `TypedDict` que combina `identifier` (string estável com prefixos como `placeholder::` ou `aria::`) e `attributes`.

### `dependencies.py`

- `REQUIRED_TOOLS`: lista os comandos a validar (`sqlmap`, `ffuf`).
- `check_tool(command)`: encapsula `shutil.which` e `subprocess.run` para testar a ferramenta.
- `verify_dependencies()`: devolve um dicionário `{nome: bool}` com o status de cada comando.

## Autenticação (`owasp_scanner.auth.login`)

- `login_with_credentials(page, login_url, email, password)`: utiliza Playwright para submeter o formulário de login e retorna cookies em caso de sucesso.
- `login_juice_shop_demo(page, base_url)`: login de fallback com credenciais padrão do Juice Shop.

## Reconhecimento (`owasp_scanner.recon`)

### `crawler.py`

- `Spider`: classe principal do crawling. Métodos internos relevantes:
  - `_bootstrap_session(page)`: injeta cookies fornecidos ou tenta autenticação automática.
  - `_extract_links(page, url)`: adiciona URLs internas ao conjunto de visita e marca alvos potencialmente vulneráveis a SQLi.
  - `_extract_forms(page)`: converte inputs em `FieldInfo`, priorizando atributos mais estáveis (placeholder, `aria-label`, `data-testid`, `id`) e ignora campos ocultos.
  - `_register_field_identifier(url, field_info)`: registra o campo tanto para XSS quanto para SQLi reutilizando os metadados estruturados.
  - `run()`: loop de navegação que popula o `ReconReport` e aciona `run_ffuf` ao final.

### `directory_enum.py`

- `DirectoryEnumerationError`: exceção específica para falhas do ffuf.
- `run_ffuf(base_url, cookies=None, wordlist=None, threads=15, timeout=300)`: executa `ffuf` usando a wordlist padrão (`resources/common_dirs.txt`) e retorna um `set` de URLs encontrados.

### `utils.py`

- `build_cookie_header(cookies)`: converte uma lista de cookies em header HTTP `Cookie: nome=valor; ...`.

## Callback (`owasp_scanner.callback.server`)

- `PayloadInfo` / `CallbackInfo`: dataclasses que descrevem payloads injetados e callbacks recebidos.
- `PayloadTracker`: armazena dicionários de payloads (`injected`) e callbacks (`received`).
- `CallbackServer(port, tracker)`: encapsula um `socketserver.TCPServer` em thread própria.
  - `start()` / `stop()`: inicializam e encerram o servidor web local.
- `register_payload(...)`: helper que delega para `PayloadTracker.register_payload`.
- `tracker`: instância global reutilizada pelos scanners de XSS.

## Scanners

### SQL (`owasp_scanner.scanners.sql.runner`)

- `SqlScanResult`: dataclass com campos `target`, `vulnerable` e `raw_output`.
- `run_sql_scanner(report)`: itera sobre `report.sqli_targets`, executa `sqlmap` e retorna uma lista de `SqlScanResult`.

### XSS (`owasp_scanner.scanners.xss`)

- `XSSScanner`: encapsula a lógica de teste de eco e injeção de payloads via Playwright utilizando `FieldInfo`.
  - `_iter_fields(campos)`: converte cada entrada (dict ou string legacy) em par `(identifier, FieldAttributes)`.
  - `_echo_test(url, identifier, metadata)`: retorna `EchoResult` informando se houve reflexão e se o campo permanece disponível após a navegação.
  - `_apply_payload(identifier, payload_id, template_index, metadata)`: injeta payloads com base nos metadados e atualiza o `PayloadTracker` com `field_id` / `field_name` reais quando disponíveis.
  - `run(form_targets)`: registra eco apenas quando o campo continua presente na página final e injeta payloads nos alvos válidos, retornando dicionários com `field`, `field_id`, `field_name`, `payload_id` e `payload`.
- `run_xss_scanner(config, report, listener_url)`: função de alto nível que prepara o browser, aplica cookies e executa o `XSSScanner`.
- **Integração com Dalfox** (`owasp_scanner.scanners.dalfox`): reutiliza os mesmos `FieldInfo`, monta alvos com o parâmetro a ser fuzzado e invoca o binário `dalfox` para executar payloads contextuais e registrar vulnerabilidades encontradas.

## Analisador de acesso (`owasp_scanner.access.analyzer`)

- `run_access_analyzer(config, report)`: cria uma sessão `requests`, aplica cookies coletados e testa URLs em paralelo (máximo de 15 threads).
- `_prepare_session(report)`: injeta cookies na `Session`.
- `_check_url(session, url)`: retorna a URL caso o status HTTP seja 200.

## Scripts auxiliares

- `main.py`: entry point compatível com execução direta (`python main.py`) que apenas delega para `owasp_scanner.cli.main()` adicionando `src/` ao `sys.path` quando necessário.

## Dados e recursos estáticos

- `resources/common_dirs.txt`: wordlist padrão utilizada pelo `ffuf`.

Para detalhes adicionais sobre fluxos ou uso, consulte as seções de [arquitetura](architecture.md) e [operações](operations.md).
