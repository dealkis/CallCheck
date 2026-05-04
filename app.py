from flask import Flask, render_template, request, url_for, redirect
import mysql.connector
import os


app = Flask(__name__)

# =========================
# CONFIGURAÇÃO DE CONEXÃO (Seu código original)
# =========================
def conectar():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "callcheck"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

# =========================
# LÓGICA DE VERIFICAÇÃO (Seu código original)
# =========================
def verificar_empresa(nome, telefone=None):
    conn = conectar()
    if conn is None:
        return {
            "empresa": nome,
            "telefones": ["Conexão com banco indisponível"],
            "emails": ["contato@exemplo.com"],
            "status": "SIMULACAO",
            "mensagem": "Nota: O sistema está em modo de demonstração pois não detectou um banco de dados ativo."
        }

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM empresa WHERE nome = %s", (nome,))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {"status": "ERRO", "mensagem": "Empresa não encontrada em nossa base de dados oficial."}

        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
        telefones = [t["numero"] for t in cursor.fetchall()]
        
        emails = ["atendimento@oficial.com.br"]

        denuncias = []
        if telefone:
            cursor.execute("""
                SELECT d.tipo, d.descricao 
                FROM denuncia d
                JOIN telefone t ON d.telefone_id = t.id
                WHERE t.numero = %s
            """, (telefone,))
            denuncias = cursor.fetchall()

        conn.close()
        resposta = {"empresa": empresa["nome"], "telefones": telefones, "emails": emails}

        if not telefone:
            resposta.update({"status": "CANAIS", "mensagem": "Estes são os canais oficiais registrados para esta empresa."})
        elif telefone in telefones:
            resposta.update({"status": "OFICIAL", "mensagem": "Este é um número verificado e pertence à empresa."})
        elif denuncias:
            resposta.update({"status": "ALERTA", "mensagem": "Atenção! Este número possui denúncias de atividades suspeitas.", "denuncias": denuncias})
        else:
            resposta.update({"status": "NAO_OFICIAL", "mensagem": "Este número NÃO consta na lista oficial da empresa."})
        
        return resposta

    except Exception as e:
        if conn: conn.close()
        return {"status": "ERRO", "mensagem": f"Erro interno no processamento: {str(e)}"}

# =========================
# ROTAS DO SITE
# =========================

@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    if request.method == "POST":
        nome_empresa = request.form.get("nome")
        numero_tel = request.form.get("telefone")
        if numero_tel:
            numero_tel = numero_tel.strip()
        resultado = verificar_empresa(nome_empresa, numero_tel)
    return render_template("index.html", resultado=resultado)

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    sucesso = None
    
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario")
        senha_digitada = request.form.get("senha")

        # Lógica de teste sem banco de dados
        if usuario_digitado == "admin" and senha_digitada == "123":
            sucesso = "Login realizado com sucesso! Bem-vindo ao painel ACEX."
        else:
            erro = "Usuário não encontrado ou senha incorreta."
    
    return render_template("login.html", erro=erro, sucesso=sucesso)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
