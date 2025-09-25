# OWASP Web Scanner

![Status](https://img.shields.io/badge/status-em%20construção-yellow)
![Python](https://img.shields.io/badge/language-Python-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OWASP](https://img.shields.io/badge/OWASP-Top%2010-critical)

Este projeto é uma ferramenta educacional desenvolvida para explorar e demonstrar a identificação de vulnerabilidades comuns listadas no OWASP Top 10. Focado em aprendizado prático, o scanner foi extensivamente testado contra a aplicação [Juice Shop](https://github.com/juice-shop/juice-shop.git), proporcionando um ambiente seguro para experimentar técnicas de detecção de falhas de segurança. É ideal para estudantes e entusiastas de segurança que desejam aprofundar seus conhecimentos em testes de segurança de aplicações web.

## Instalação

### Pré-requisitos
- Python 3.12+
- Playwright, requests, beautifulsoup4, pyngrok, python-dotenv (instalados via `pip install -r requirements.txt`)
- Ferramentas externas:
  - sqlmap: `apt install sqlmap` ou `pip install sqlmap`
  - ffuf: `go install github.com/ffuf/ffuf@latest`

### Passos
1. Clone o repositório: `git clone https://github.com/jpaullopes/OWASPWebScanner.git`
2. Instale dependências: `pip install -r requirements.txt`
3. Instale ferramentas externas conforme acima.
4. Execute: `python main.py` (orquestrador automático) ou módulos individuais.

## Uso

### Execução Completa (Recomendado)
```bash
python main.py -u http://site-alvo.com
```
Isso executa todos os módulos em ordem: Crawler → CallbackServer → Scanners.

### Execução Manual
1. **Crawler**: `python src/Recon/web_crawler.py` (gera `relatorio_spider.json`)
2. **CallbackServer**: `python src/modules/CallbackServer/xss_http_server.py` (em background)
3. **SQLi Scanner**: `python src/modules/SqlInjectionScanner/sql_injection.py`
4. **Access Analyzer**: `python test/run_access_analyzer_test.py`

### Configuração
- Crie um arquivo `.env` com `SESSION_COOKIE=seu_cookie_aqui` (obtenha via login manual no navegador).
- Ou deixe vazio para tentar login automático.
- Relatório salvo em `relatorio_spider.json`.

## Fluxo de Execução

1. **Crawler (Recon/web_crawler.py)**: Navega no site, extrai links/formulários, roda ffuf para dir enum, salva relatório.
2. **CallbackServer (CallbackServer/xss_http_server.py)**: Servidor HTTP para detectar XSS callbacks.
3. **Scanners**:
   - **SQLi**: Usa sqlmap nos alvos do relatório.
   - **XSS**: Injeta payloads e monitora callbacks.
   - **Access**: Testa acesso aos paths descobertos.

## Módulos Detalhados

### SqlInjectionScanner
**Arquivo**: `src/modules/SqlInjectionScanner/sql_injection.py`

**Descrição**: Detecta vulnerabilidades de Injeção SQL usando sqlmap. Executa testes automatizados em URLs com parâmetros.

**Como Funciona**:
- Lê alvos do `relatorio_spider.json`.
- Roda sqlmap com cookies de sessão.
- Verifica saída para indicadores de vulnerabilidade.

**Exemplo de Saída**:
```
[*] Alvo: http://site.com/search?q=test
[*] Executando sqlmap...
[!!!] SUCESSO! Alvo parece ser vulnerável a SQL Injection.
```

**Limitações**: Depende de sqlmap; pode gerar falsos positivos/negativos.

### XssScanner
**Arquivos**: `src/modules/XssScanner/scanner.py`, `src/modules/XssScanner/xss.py`

**Descrição**: Detecta vulnerabilidades XSS (Cross-Site Scripting), focando em Blind XSS.

**Como Funciona**:
- Lê formulários do relatório.
- Injeta payloads (ex.: `<img src=x onerror=fetch('callback_url')>`).
- Monitora o CallbackServer por execuções remotas.

**Exemplo de Saída**:
```
[!!!] BLIND XSS CONFIRMADO! Chamada recebida!
[+] Payload ID identificado: 123
```

**Limitações**: Requer CallbackServer rodando; payloads podem ser bloqueados por WAF.

### AccessAnalyzer
**Arquivo**: `src/modules/AccessAnalyzer/url_scan.py`

**Descrição**: Testa falhas de Controle de Acesso (Broken Access Control) tentando acessar paths restritos.

**Como Funciona**:
- Lê paths descobertos pelo crawler (via ffuf).
- Faz requests autenticados com cookies.
- Verifica se URLs retornam status 200 (acessíveis).

**Exemplo de Saída**:
```
[+] URL acessível: http://site.com/admin (Status: 200)
```

**Limitações**: Não testa permissões granulares; usa threads (pode sobrecarregar o alvo).

## Contribuição
- Relate issues no GitHub.
- Pull requests são bem-vindos.
- Teste apenas em ambientes autorizados.

## Licença
MIT License.