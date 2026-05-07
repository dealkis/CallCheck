# CallCheck - Verificador de Procedência (Projeto ACEX)

O **CallCheck** é uma aplicação Full-Stack desenvolvida para o **Projeto ACEX** do curso de **Bacharelado em Ciência de Dados**. O sistema funciona como um verificador de segurança para identificar a procedência de números de telefone e empresas, auxiliando o utilizador a evitar golpes e SPAM.

## Funcionalidades Principais

- **Consulta Inteligente:** Pesquisa por nome de empresa, UF (Estado) ou número de telefone.
- **Painel do Utilizador:** Visualização de estatísticas de busca e histórico de consultas.
- **Painel Administrativo:** Interface restrita para cadastro e gestão de empresas oficiais na base de dados.
- **Sistema de Denúncias:** Opção para reportar números suspeitos diretamente pela interface.
- **Base de Dados Integrada:** Consulta em tempo real a uma base de estabelecimentos (PostgreSQL).
- **Acessibilidade:** Design focado em alto contraste e fontes legíveis para melhor usabilidade.

## Tecnologias Utilizadas

- **Backend:** Python com Framework [Flask](https://flask.palletsprojects.com/)
- **Base de Dados:** PostgreSQL (alojado no Render.com)
- **Frontend:** HTML5, CSS3 (Responsivo) e Jinja2
- **Gestão de Dados:** SQL e Psycopg2 (com Pool de Conexões para performance)
- **Deploy:** Preparado para execução em ambientes WSGI (Gunicorn)

##  Estrutura de Arquivos

- `app.py`: Lógica central, rotas e conexão com a base de dados.
- `requirements.txt`: Lista de dependências do Python.
- `static/`: Contém o arquivo `style.css` com a estilização e regras de responsividade.
- `templates/`: Interface do utilizador (index, login, painel admin, lista de empresas).

##  Como Executar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
