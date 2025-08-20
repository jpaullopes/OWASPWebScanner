
# OWASP Web Scanner

Este projeto tem como objetivo ser uma ferramenta de aprendizado para a criação de scripts capazes de identificar as principais vulnerabilidades do OWASP Top 10. Desenvolvido com foco acadêmico, o scanner foi testado principalmente na aplicação [Juice Shop](https://github.com/juice-shop/juice-shop.git), permitindo a experimentação prática de técnicas de detecção de falhas de segurança.

## Módulos Disponíveis

- **sql_injection**: Módulo responsável por realizar uma série de injeções SQL com objetivo de encontrar possíveis bypasses de autenticação na aplicação.

- **xss**: Módulo responsável por identificar vulnerabilidades XSS na aplicação através da análise de campos de entrada e execução de testes de blind XSS.