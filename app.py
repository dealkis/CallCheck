from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "chave_segura_acex"


# CONFIGURAÇÃO DE CONEXÃO
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


# LÓGICA DE VERIFICAÇÃO
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


# ROTAS DO SITE
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        numero_pesquisado = request.form.get("numero")
        
        # Aqui você teria a lógica de verificar se o número é fraude ou não.
        # Vamos simular um resultado:
        resultado_simulado = {
            "numero": numero_pesquisado,
            "empresa": "Empresa Desconhecida",
            "status": "Suspeito"
        }
        # 1. Verifica se já existe uma lista de pesquisas na sessão
        if 'pesquisas_recentes' not in session:
            session['pesquisas_recentes'] = []
        # 2. Adiciona a nova pesquisa no INÍCIO da lista
        pesquisas = session['pesquisas_recentes']
        pesquisas.insert(0, resultado_simulado)
        # 3. Limita para salvar apenas as últimas 5 pesquisas (para não pesar)
        session['pesquisas_recentes'] = pesquisas[:5]
        # Importante: avisa ao Flask que a sessão foi modificada
        session.modified = True 
        # Renderiza a página passando o resultado (adapte para o seu código atual)
        return render_template("index.html", resultado=resultado_simulado)
        
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))
        
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario")
        senha_digitada = request.form.get("senha")

        if usuario_digitado == "admin" and senha_digitada == "123":
            session.permanent = True
            session["usuario_logado"] = usuario_digitado
            return redirect(url_for('perfil_usuario'))
        else:
            erro = "Usuário não encontrado ou senha incorreta."
    
    return render_template("login.html", erro=erro)

@app.route("/usuario")
def perfil_usuario():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
        
    return render_template("usuario.html")

@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for('login'))
    
@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
@app.route("/historico")
def historico():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("historico.html", pesquisas=pesquisas)
