# Resolução de problemas

Esta página compila erros comuns encontrados durante a instalação ou execução do OWASP Web Scanner e como corrigi-los.

## Ambiente Python

### `error: externally-managed-environment`

**Causa:** tentativa de instalar dependências no Python fornecido pela distribuição Linux (PEP 668).

**Solução:** crie um ambiente virtual dedicado e reinstale o projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### `ModuleNotFoundError: No module named 'owasp_scanner'`

**Causa:** execução direta dos módulos sem ter instalado o pacote ou sem adicionar `src/` ao `PYTHONPATH`.

**Solução:** instale o pacote em modo editável ou execute scripts via `python -m` / `owasp-web-scanner`.

## Dependências externas

### `sqlmap` ou `ffuf` não encontrados

**Sintoma:** a CLI imprime `[!] sqlmap não encontrado`.

**Solução:**

- Instale `sqlmap` e `ffuf` via gerenciador de pacotes do sistema (por exemplo, `apt`, `brew`) ou via `pipx`/`go install`.
- Garanta que os binários estejam no `PATH` antes de rodar o scanner.

### `DirectoryEnumerationError`

**Causa:** falha na execução do `ffuf` (timeout ou wordlist ausente).

**Solução:**

- Valide se `resources/common_dirs.txt` existe e está acessível.
- Ajuste o timeout chamando `run_ffuf(..., timeout=600)` ao usar a API manualmente.
- Garanta conectividade com o alvo (firewall, proxy, VPN).

## Estrutura de código

### `ModuleNotFoundError` ao importar de `src.modules`

**Causa:** as rotas `src/modules/` e `src/Recon/` foram descontinuadas na refatoração mais recente.

**Solução:** importe sempre a partir de `owasp_scanner`:

```python
# Correto
from owasp_scanner.recon.crawler_legacy import Spider
from owasp_scanner.access.analyzer import run_access_analyzer
```

## Execução do CLI

### SQL scanner não executa

**Sintoma:** a etapa `[3/5] SQL Injection` termina imediatamente sem listar alvos.

**Solução:** verifique se o arquivo `src/owasp_scanner/cli.py` contém a chamada para `run_sql_scanner`.
Se estiver trabalhando com uma cópia antiga, atualize-a para a mesma lógica da branch atual.

## Playwright

### `playwright._impl._errors.Error: Browser closed` ou timeouts frequentes

**Causa:** binários dos navegadores não instalados ou recursos insuficientes.

**Solução:**

```bash
playwright install --with-deps
```

Se o ambiente for headless, adicione `--with-deps` para instalar dependências do sistema.

### Login não funciona (cookies vazios)

**Causa:** credenciais incorretas ou fluxo de autenticação diferente.

**Solução:**

- Defina `EMAIL_LOGIN`/`PASSWORD_LOGIN` com credenciais válidas.
- Verifique se o site exige 2FA ou CAPTCHA (não suportados).
- Use `SESSION_COOKIE` para sessões previamente autenticadas.

## Servidor de callback

### `OSError: [Errno 98] Address already in use`

**Causa:** porta de callback em uso.

**Solução:**

- Finalize processos concorrentes (`lsof -i :8000`).
- Altere a flag `--callback-port` ao iniciar a CLI.

## Testes automatizados

### `pytest` falha carregando variáveis reais do `.env`

**Solução:**

- Certifique-se de que os testes executam em ambiente limpo ou sem `.env` com credenciais reais.
- Caso necessário, remova/renomeie temporariamente o arquivo `.env` ou sobrescreva variáveis dentro dos testes com `monkeypatch`.

## Dicas gerais

- Use `HEADLESS=false` para depurar visualmente o comportamento do Playwright.
- Habilite logging adicional adicionando prints/`logging` nos pontos relevantes (crawler, scanners).
- Ao rodar contra alvos lentos, aumente timeouts: `SQLMAP_TIMEOUT`, `run_ffuf(... timeout=600)` e `page.goto(..., timeout=20000)` podem ser ajustados via código.
- Sempre execute o scanner em ambientes autorizados para evitar implicações legais.
