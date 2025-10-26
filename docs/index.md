# OWASP Web Scanner — Documentação

Bem-vindo à documentação oficial do **OWASP Web Scanner**. Este portal reúne instruções operacionais, visão arquitetural, detalhamento de módulos e orientações de desenvolvimento para que você possa usar, estender e manter a ferramenta com segurança.

## Estrutura da documentação

- [Guia de início rápido](getting_started.md) — preparação do ambiente, instalação, variáveis suportadas e primeiros passos.
- [Arquitetura e fluxo de dados](architecture.md) — visão de alto nível dos componentes, integrações externas e fluxo entre módulos.
- [Referência de módulos e APIs](modules.md) — catálogo das principais funções, classes e responsabilidades por pacote.
- [Operação e automação](operations.md) — formas de executar a CLI, rodar módulos isolados e integrar em pipelines.
- [Guia de desenvolvimento](development.md) — convenções de código, estrutura de diretórios, testes, lint e processo de contribuição.
- [Resolução de problemas](troubleshooting.md) — solução para erros frequentes envolvendo ambiente, dependências e execuções.

## Visão geral do projeto

O OWASP Web Scanner é uma suíte educacional que orquestra múltiplas etapas de reconhecimento e exploração alinhadas ao OWASP Top 10. A aplicação foi construída em Python 3.12, utiliza Playwright para automação de navegador, integra ferramentas externas (sqlmap e ffuf), injeta payloads de XSS e mantém um servidor próprio para callbacks de blind XSS.

Principais metas do projeto:

- Demonstrar como integrar diferentes técnicas de reconhecimento (crawler, brute-force de diretórios, coleta de cookies).
- Automatizar scanners de SQL Injection e XSS utilizando resultados compartilhados.
- Validar o controle de acesso em URLs descobertas durante o reconhecimento.
- Manter uma base de código modular, testável e extensível.

Se você está chegando agora, comece pelo [guia de início rápido](getting_started.md) e avance conforme o seu objetivo (uso, automação ou desenvolvimento interno).
