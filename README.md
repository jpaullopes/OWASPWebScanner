# OWASP Web Scanner

![Status](https://img.shields.io/badge/status-em%20construção-yellow)
![Python](https://img.shields.io/badge/language-Python-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OWASP](https://img.shields.io/badge/OWASP-Top%2010-critical)

Este projeto é uma ferramenta educacional desenvolvida para explorar e demonstrar a identificação de vulnerabilidades comuns listadas no OWASP Top 10. Focado em aprendizado prático, o scanner foi extensivamente testado contra a aplicação [Juice Shop](https://github.com/juice-shop/juice-shop.git), proporcionando um ambiente seguro para experimentar técnicas de detecção de falhas de segurança. É ideal para estudantes e entusiastas de segurança que desejam aprofundar seus conhecimentos em testes de segurança de aplicações web.

## Módulos Disponíveis

- **SqlInjectionScanner**: Este módulo foca na detecção de vulnerabilidades de Injeção SQL. Ele executa uma série de testes de injeção, buscando identificar possíveis bypasses de autenticação e outras falhas relacionadas à manipulação de consultas SQL em aplicações web.

- **XssScanner**: Dedicado à identificação de vulnerabilidades de Cross-Site Scripting (XSS). O módulo analisa campos de entrada em páginas web e realiza testes de Blind XSS, injetando payloads e monitorando callbacks para detectar a execução de código malicioso no lado do cliente.

- **AccessAnalyzer**: Projetado para testar falhas de Controle de Acesso Quebrado. Este módulo utiliza uma word-list pré-definida para tentar acessar recursos restritos ou executar ações não autorizadas, simulando ataques de escalonamento de privilégios ou acesso indevido.