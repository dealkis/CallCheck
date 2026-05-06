# Importa as bibliotecas necessárias para a aplicação:
# Flask: framework web; render_template: renderiza HTML; request: lida com dados recebidos; 
# redirect/url_for: redirecionamento de rotas; session: armazena dados da sessão do usuário.
from flask import Flask, render_template, request, redirect, url_for, session
# psycopg2: biblioteca para conectar e interagir com o banco de dados PostgreSQL.
import psycopg2
# RealDictCursor: permite que os resultados do banco de dados ajam como dicionários (chave-valor).
from psycopg2.extras import RealDictCursor
# os: permite acessar variáveis de ambiente do sistema operacional.
import os

# Inicializa a aplicação Flask.
app = Flask(__name__)
# Define uma chave secreta para a aplicação, necessária para gerenciar sessões de forma segura. 
# Tenta pegar da variável de ambiente, se não achar, usa "chave_segura_acex".
app.secret_key = os.getenv("SECRET_KEY", "chave_segura_acex")

# =========================
# CONEXÃO
# =========================
def conectar():
    # Tenta estabelecer a conexão com o banco de dados usando credenciais das variáveis de ambiente.
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
    # Caso ocorra algum erro na conexão, imprime o erro no console e retorna None.
    except Exception as e:
        print("Erro ao conectar:", e)
        return None

# =========================
# UTIL
# =========================
def limpar_telefone(tel):
    # Recebe uma string de telefone e remove tudo que não for número (ex: parênteses, traços).
    return ''.join(filter(str.isdigit, tel or ""))

# =========================
# VERIFICAÇÃO
# =========================
def verificar_empresa(nome=None, telefone=None):
    # Abre a conexão com o banco.
    conn = conectar()

    # Se a conexão falhar, retorna um dicionário de erro.
    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        # Cria um cursor para executar comandos SQL.
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Limpa o telefone recebido para ter apenas os dígitos numéricos.
        telefone = limpar_telefone(telefone)

        # BUSCA POR TELEFONE
        # Se o usuário digitou apenas o telefone (sem o nome da empresa).
        if telefone and not nome:
            # Procura no banco qual empresa está vinculada a este número.
            cursor.execute("""
                SELECT e.nome, t.numero
                FROM telefone t
                JOIN empresa e ON t.empresa_id = e.id
                WHERE regexp_replace(t.numero, '\\D', '', 'g') = %s
            """, (telefone,))
            
            resultado = cursor.fetchone()
            conn.close()

            # Se encontrou, retorna os dados da empresa.
            if resultado:
                return {
                    "empresa": resultado["nome"],
                    "telefone": telefone,
                    "status": "ENCONTRADO",
                    "mensagem": "Telefone vinculado a uma empresa."
                }
            # Se não encontrou, avisa que o número não foi localizado.
            else:
                return {
                    "empresa": None,
                    "telefone": telefone,
                    "status": "NAO_ENCONTRADO",
                    "mensagem": "Telefone não encontrado."
                }

        empresa = None

        # BUSCA POR NOME
        # Se o usuário digitou o nome da empresa (pode ter digitado o telefone junto ou não).
        if nome:
            # Busca a empresa pelo nome ignorando maiúsculas/minúsculas (ILIKE) usando curingas (%nome%).
            cursor.execute("SELECT * FROM empresa WHERE nome ILIKE %s", (f"%{nome}%",))
            empresa = cursor.fetchone()

            # Se a empresa não existir no banco, encerra e retorna aviso.
            if not empresa:
                conn.close()
                return {
                    "empresa": nome,
                    "status": "NAO_CADASTRADA",
                    "mensagem": "Empresa não encontrada."
                }

        telefones = []

        # Se encontrou a empresa, busca todos os telefones vinculados ao ID dela.
        if empresa:
            cursor.execute("SELECT id, numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
            dados_tel = cursor.fetchall()
            # Cria uma lista apenas com os números limpos desses telefones.
            telefones = [limpar_telefone(t["numero"]) for t in dados_tel]

        # Monta a estrutura base da resposta que será enviada.
        resposta = {
            "empresa": empresa["nome"] if empresa else None,
            "telefones": telefones,
            "telefone": telefone if telefone else "Não informado"
        }

        # SÓ EMPRESA
        # Se o usuário buscou apenas pelo nome, retorna a lista de canais/telefones da empresa.
        if nome and not telefone:
            resposta.update({
                "status": "CANAIS",
                "mensagem": "Canais oficiais da empresa."
            })

        # EMPRESA + TELEFONE
        # Se o usuário buscou preenchendo tanto o nome quanto o telefone.
        elif nome and telefone:
            # Verifica se o telefone digitado pertence à lista de telefones da empresa.
            if telefone in telefones:
                resposta.update({
                    "status": "OFICIAL",
                    "mensagem": "Número verificado e seguro."
                })
            # Se não pertence à empresa, verifica se há denúncias contra este número.
            else:
                cursor.execute("""
                    SELECT d.tipo
                    FROM denuncia d
                    JOIN telefone t ON d.telefone_id = t.id
                    WHERE regexp_replace(t.numero, '\\D', '', 'g') = %s
                """, (telefone,))
                
                denuncia = cursor.fetchone()

                # Se houver denúncia, alerta o usuário.
                if denuncia:
                    resposta.update({
                        "status": "ALERTA",
                        "mensagem": "Número possui denúncias!"
                    })
                # Se não houver denúncia, mas não for da empresa, avisa que não é oficial.
                else:
                    resposta.update({
                        "status": "NAO_OFICIAL",
                        "mensagem": "Número não é oficial."
                    })

        # Se não caiu em nenhuma condição anterior (ex: campos vazios).
        else:
            resposta.update({
                "status": "ERRO",
                "mensagem": "Informe nome ou telefone."
            })

        # Fecha a conexão e retorna o resultado montado.
        conn.close()
        return resposta

    # Captura exceções e garante que a conexão será fechada caso algo dê errado.
    except Exception as e:
        if conn:
            conn.close()
        return {"status": "ERRO", "mensagem": str(e)}

# =========================
# ROTAS PRINCIPAIS
# =========================
# Rota principal (página inicial). Aceita métodos GET e POST.
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None

    # Se o formulário foi enviado (POST).
    if request.method == "POST":
        # Pega os dados digitados, removendo espaços no início e no fim.
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()

        # Valida se pelo menos um dos campos foi preenchido.
        if not nome and not telefone:
            erro_formulario = "Informe nome ou telefone"
        else:
            # Chama a função de verificação.
            resultado = verificar_empresa(nome, telefone)

    # Renderiza o arquivo HTML passando os resultados ou erros encontrados.
    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

# =========================
# USUÁRIO
# =========================
# Rota para o perfil do usuário, também aceita GET e POST.
@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    # Verifica se o usuário está logado na sessão; caso não esteja, manda para a tela de login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    resultado_local = None

    # Se uma nova pesquisa for feita por dentro do perfil (POST).
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if nome or telefone:
            # Faz a verificação no banco de dados.
            resultado_local = verificar_empresa(nome, telefone)

            # Salva o resultado no histórico de pesquisas recentes da sessão do usuário.
            pesquisas = session.get('pesquisas_recentes', [])
            pesquisas.insert(0, resultado_local)
            # Limita o histórico salvo para apenas as 5 pesquisas mais recentes.
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True

    # Recupera o histórico de pesquisas para mostrar na tela.
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("usuario.html", pesquisas=pesquisas, resultado_modal=resultado_local)

# =========================
# LOGIN / LOGOUT
# =========================
# Rota de login.
@app.route("/login", methods=["GET", "POST"])
def login():
    # Se o usuário já estiver logado, redireciona diretamente para o perfil.
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))

    erro = None

    # Se enviou as credenciais (POST).
    if request.method == "POST":
        # Verifica se as credenciais são "admin" e "123" (hardcoded/fixado no código).
        if request.form.get("usuario") == "admin" and request.form.get("senha") == "123":
            # Marca o usuário como logado na sessão e redireciona.
            session["usuario_logado"] = "admin"
            return redirect(url_for('perfil_usuario'))
        else:
            erro = "Usuário ou senha incorretos."

    # Se for GET (apenas acessando a página), renderiza o formulário de login.
    return render_template("login.html", erro=erro)

# Rota para sair do sistema.
@app.route("/logout")
def logout():
    # Remove o usuário logado da sessão, destruindo seu acesso autenticado.
    session.pop("usuario_logado", None)
    return redirect(url_for('login'))

# =========================
# PÁGINAS
# =========================
# Rotas para exibir páginas estáticas de informação.
@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

# Rota para ver o histórico completo, bloqueada apenas para usuários logados.
@app.route("/historico")
def historico():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    # Pega o histórico da sessão e manda para o template.
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("historico.html", pesquisas=pesquisas)

# =========================
# ADMIN (PROTEGER!)
# =========================
# Função auxiliar para verificar se há alguém logado.
def proteger():
    return "usuario_logado" in session

# Rota de teste/admin para adicionar uma empresa direto pelo código (apenas se logado).
@app.route("/add-empresa")
def add_empresa():
    # Bloqueia caso não passe na proteção.
    if not proteger():
        return "Acesso negado"

    # Conecta e insere manualmente uma linha fixa de teste.
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO empresa (nome) VALUES ('Banco do Brasil')")
    conn.commit()
    conn.close()

    return "Empresa adicionada!"

# Rota do painel de administrador para cadastrar empresas via formulário.
@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Exige login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    mensagem = None

    # Lida com o envio do formulário de cadastro de nova empresa e telefone.
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")

        if nome:
            conn = conectar()
            cursor = conn.cursor()

            # insere a empresa no banco de dados e retorna o ID recém-criado.
            cursor.execute(
                "INSERT INTO empresa (nome) VALUES (%s) RETURNING id",
                (nome,)
            )
            empresa_id = cursor.fetchone()[0]

            # insere telefone (se o usuário preencheu no formulário).
            if telefone:
                # Limpa os caracteres não numéricos antes de salvar.
                telefone = ''.join(filter(str.isdigit, telefone))

                cursor.execute(
                    "INSERT INTO telefone (empresa_id, numero) VALUES (%s, %s)",
                    (empresa_id, telefone)
                )

            # Efetiva as mudanças e fecha a conexão.
            conn.commit()
            conn.close()

            mensagem = "Empresa cadastrada com sucesso!"

    return render_template("admin.html", mensagem=mensagem)

# Rota administrativa para listar todas as empresas cadastradas no banco.
@app.route("/admin/empresas")
def listar_empresas():
    # Exige login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    # Puxa tudo da tabela 'empresa' e renderiza na tela de listagem.
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM empresa")
    empresas = cursor.fetchall()
    conn.close()

    return render_template("empresas.html", empresas=empresas)

# Rota administrativa para deletar uma empresa específica (passada pelo ID na URL).
@app.route("/admin/excluir/<int:id>")
def excluir_empresa(id):
    # Exige login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    # Deleta a empresa com base no ID recebido e redireciona de volta para a lista.
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM empresa WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('listar_empresas'))

# Rota administrativa para editar apenas o nome de uma empresa.
@app.route("/admin/editar/<int:id>", methods=["GET", "POST"])
def editar_empresa(id):
    # Exige login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    conn = conectar()
    cursor = conn.cursor()

    # Se for submissão (POST), atualiza o nome no banco de dados e redireciona.
    if request.method == "POST":
        novo_nome = request.form.get("nome")

        cursor.execute(
            "UPDATE empresa SET nome = %s WHERE id = %s",
            (novo_nome, id)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('listar_empresas'))

    # GET (carregar dados): Se for apenas o acesso à página, busca os dados da empresa para exibir no formulário.
    cursor.execute("SELECT * FROM empresa WHERE id = %s", (id,))
    empresa = cursor.fetchone()

    conn.close()
    return render_template("editar_empresa.html", empresa=empresa)

# Rota de painel de controle completo para uma empresa específica (múltiplas ações na mesma página).
@app.route("/admin/empresa/<int:id>", methods=["GET", "POST"])
def gerenciar_empresa(id):
    # Exige login.
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    conn = conectar()
    cursor = conn.cursor()

    # Se um formulário for enviado, ele usa um campo 'acao' (input hidden) para saber o que fazer.
    if request.method == "POST":
        acao = request.form.get("acao")

        # =========================
        # EDITAR NOME
        # =========================
        if acao == "editar_nome":
            novo_nome = request.form.get("nome")
            cursor.execute(
                "UPDATE empresa SET nome = %s WHERE id = %s",
                (novo_nome, id)
            )

        # =========================
        # ADICIONAR TELEFONE
        # =========================
        elif acao == "add_telefone":
            telefone = request.form.get("telefone")
            # Limpa formatação.
            telefone = ''.join(filter(str.isdigit, telefone))

            # Associa um novo telefone a este ID de empresa.
            cursor.execute(
                "INSERT INTO telefone (empresa_id, numero) VALUES (%s, %s)",
                (id, telefone)
            )

        # =========================
        # EXCLUIR TELEFONE
        # =========================
        elif acao == "excluir_telefone":
            tel_id = request.form.get("tel_id")
            # Deleta apenas o telefone específico com base no ID recebido.
            cursor.execute("DELETE FROM telefone WHERE id = %s", (tel_id,))

        # =========================
        # EXCLUIR EMPRESA
        # =========================
        elif acao == "excluir_empresa":
            # Primeiro deleta todos os telefones vinculados a ela (evitando erros de chave estrangeira).
            cursor.execute("DELETE FROM telefone WHERE empresa_id = %s", (id,))
            # Depois deleta a empresa em si.
            cursor.execute("DELETE FROM empresa WHERE id = %s", (id,))
            conn.commit()
            conn.close()
            # Redireciona para a lista porque essa empresa não existe mais.
            return redirect(url_for('listar_empresas'))

        # Confirma as alterações de nome/telefone no banco caso tenha caído nas 3 primeiras ações.
        conn.commit()

    # =========================
    # BUSCAR DADOS
    # =========================
    # Busca os dados atualizados da empresa e todos os seus telefones para exibir na tela.
    cursor.execute("SELECT * FROM empresa WHERE id = %s", (id,))
    empresa = cursor.fetchone()

    cursor.execute("SELECT * FROM telefone WHERE empresa_id = %s", (id,))
    telefones = cursor.fetchall()

    conn.close()

    # Renderiza a página de detalhes com as informações da empresa e seus telefones.
    return render_template("empresa_detalhe.html", empresa=empresa, telefones=telefones)

# =========================
# FINAL
# =========================
# Checa se o script está sendo rodado diretamente (e não importado como módulo em outro arquivo).
if __name__ == "__main__":
    # Define a porta do servidor, pegando da variável de ambiente ou o padrão 5000.
    port = int(os.environ.get("PORT", 5000))
    # Roda a aplicação Flask de forma que fique acessível na rede ("0.0.0.0").
    app.run(host="0.0.0.0", port=port)
