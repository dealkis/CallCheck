from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import psycopg2
import os
#-----------------#
#-----------------#
#-----------------#
#-----------------#
app = Flask(__name__)
app.secret_key = "chave_segura_acex"
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# CONFIGURAÇÃO DE CONEXÃO#
def conectar():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
    except Exception as e:
        print("Erro ao conectar:", e)
        return None 
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# LÓGICA DE VERIFICAÇÃO#
def verificar_empresa(nome, telefone=None):
    conn = conectar()
#-----------------#
#-----------------#
#-----------------#
#-----------------#
#SIMULAÇÃO#
    if conn is None:
        return {
            "empresa": nome if nome else "Empresa Demo",
            "telefone": telefone if telefone else "Não informado",
            "telefones": ["(11) 4004-0000", "(11) 99999-9999"],
            "emails": ["contato@exemplo.com"],
            "status": "CANAIS" if not telefone else "OFICIAL",
            "mensagem": "Nota: Modo de demonstração (Banco offline)."
        }

    try:
        cursor = conn.cursor(dictionary=True)
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# Busca aproximada pelo nome#
        cursor.execute("SELECT * FROM empresa WHERE nome LIKE %s", (f"%{nome}%",))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {"status": "ERRO", "mensagem": "Empresa não encontrada em nossa base oficial."}
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# Busca telefones vinculados
        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
        telefones = [t["numero"] for t in cursor.fetchall()]
        emails = ["atendimento@oficial.com.br"]

        resposta = {
            "empresa": empresa["nome"], 
            "telefones": telefones, 
            "emails": emails,
            "telefone": telefone if telefone else "Não informado"
        }
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# Lógica de Status
        if not telefone or telefone.strip() == "":
            resposta.update({"status": "CANAIS", "mensagem": "Canais oficiais registrados."})
        elif telefone in telefones:
            resposta.update({"status": "OFICIAL", "mensagem": "Número verificado e seguro."})
        else:
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# Verifica denúncias
            cursor.execute("""
                SELECT d.tipo FROM denuncia d 
                JOIN telefone t ON d.telefone_id = t.id 
                WHERE t.numero = %s
            """, (telefone,))
            denuncia = cursor.fetchone()
            if denuncia:
                resposta.update({"status": "ALERTA", "mensagem": "Este número possui denúncias!"})
            else:
                resposta.update({"status": "NAO_OFICIAL", "mensagem": "Número não consta na lista oficial."})
        conn.close()
        return resposta
        
    except Exception as e:
        if conn: conn.close()
        return {"status": "ERRO", "mensagem": f"Erro interno: {str(e)}"}
#-----------------#
#-----------------#
#-----------------#
#-----------------#
# ROTAS DO SITE
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None
    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()
        
        if not nome_digitado and not telefone_digitado:
            erro_formulario = "Por favor, informe pelo menos o nome da empresa ou um telefone."
            
        else:
            resultado = verificar_empresa(nome_digitado, telefone_digitado)
            
            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []
            pesquisas = session['pesquisas_recentes']
            pesquisas.insert(0, resultado)
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True 
            
    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA USUARIO#
@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    resultado_local = None

    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        if nome_digitado or telefone_digitado:
            resultado_local = verificar_empresa(nome_digitado, telefone_digitado)

            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []

            pesquisas = session['pesquisas_recentes']
            pesquisas.insert(0, resultado_local)
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True 

    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("usuario.html", pesquisas=pesquisas, resultado_modal=resultado_local)

#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA LOGIN#
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario")
        senha_digitada = request.form.get("senha")
        if usuario_digitado == "admin" and senha_digitada == "123":
            session["usuario_logado"] = usuario_digitado
            return redirect(url_for('perfil_usuario'))
        else:
            erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)
#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA LOGOUT#
@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for('login'))
#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA SOBRE#
@app.route("/sobre")
def sobre():
    return render_template("sobre.html")
#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA CONTATO#
@app.route("/contato")
def contato():
    return render_template("contato.html")
#-----------------#
#-----------------#
#-----------------#
#-----------------#
#PAGINA HISTORICO#
@app.route("/historico")
def historico():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("historico.html", pesquisas=pesquisas)
#-----------------#
#-----------------#
#-----------------#
#-----------------#
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

#-----------------#
#-----------------#
#-----------------#
#-----------------#
@app.route("/criar-banco")
def criar_banco():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS empresa (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telefone (
        id SERIAL PRIMARY KEY,
        empresa_id INT REFERENCES empresa(id),
        numero VARCHAR(20)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS denuncia (
        id SERIAL PRIMARY KEY,
        telefone_id INT REFERENCES telefone(id),
        tipo VARCHAR(100)
    );
    """)

    conn.commit()
    conn.close()

    return "Banco criado!"
#-----------------#
#-----------------#
#-----------------#
#-----------------#
@app.route("/teste")
def teste():
    conn = conectar()
    if conn:
        return "Conectado com sucesso!"
    return "Erro ao conectar"
@app.route("/add-empresa")
def add_empresa():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO empresa (nome)
        VALUES ('Banco do Brasil')
    """)

    conn.commit()
    conn.close()

    return "Empresa adicionada!"
@app.route("/add-telefone")
def add_telefone():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO telefone (empresa_id, numero)
        VALUES (1, '(11) 4004-0001')
    """)

    conn.commit()
    conn.close()

    return "Telefone adicionado!"
    
@app.route("/add-denuncia")
def add_denuncia():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO denuncia (telefone_id, tipo)
        VALUES (1, 'Golpe de falsa central')
    """)

    conn.commit()
    conn.close()

    return "Denúncia adicionada!"
@app.route("/ver-empresas")
def ver_empresas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM empresa")
    dados = cursor.fetchall()

    conn.close()
    return str(dados)
