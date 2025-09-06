# OWASP Web Scanner

![Status](https://img.shields.io/badge/status-em%20construção-yellow)
![Python](https://img.shields.io/badge/language-Python-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![OWASP](https://img.shields.io/badge/OWASP-Top%2010-critical)

Este projeto tem como objetivo ser uma ferramenta de aprendizado para a criação de scripts capazes de identificar as principais vulnerabilidades do OWASP Top 10. Desenvolvido com foco acadêmico, o scanner foi testado principalmente na aplicação [Juice Shop](https://github.com/juice-shop/juice-shop.git), permitindo a experimentação prática de técnicas de detecção de falhas de segurança.

## Módulos Disponíveis

- **SqlInjectionScanner**: Módulo responsável por realizar uma série de injeções SQL com objetivo de encontrar possíveis bypasses de autenticação na aplicação.

- **XssScanner**: Módulo responsável por identificar vulnerabilidades XSS na aplicação através da análise de campos de entrada e execução de testes de blind XSS.

- **AccessAnalyzer**: Módulo responsável por realizar testes de quebra de controle de acesso com base em uma word-list pré-definida.