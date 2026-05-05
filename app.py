from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "chave_segura_acex"

# --- CONFIGURAÇÃO DE CONEXÃO ---
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

# --- LÓGICA DE VERIFICAÇÃO INTEGRADA ---
def verificar_empresa(nome, telefone=None):
    conn = conectar()
    
    # Se o Banco de Dados estiver OFFLINE, usa a lógica de simulação
    if conn is None:
        # Lógica para busca apenas por nome (Dados da Empresa)
        if nome and not telefone:
            return {
                "status": "Oficial",
                "empresa": nome,
                "telefone": "Não informado",
                "mensagem": f"Dados oficiais encontrados para {nome} (Modo Demo)."
            }
        # Lógica para busca com telefone
        status = "Não Oficial" if telefone.startswith("(11)") else "Oficial"
        return {
            "status": status,
            "empresa": nome if nome else "Empresa Demo",
            "telefone": telefone,
            "mensagem": "Nota: Banco de dados offline. Usando verificação padrão."
        }

    try:
        cursor = conn.cursor(dictionary=True)
        # 1. Busca a empresa
        cursor.execute("SELECT * FROM empresa WHERE nome LIKE %s", (f"%{nome}%",))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {"status": "ERRO", "mensagem": "Empresa não encontrada em nossa base oficial."}

        # 2. Busca telefones oficiais
        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
        telefones_oficiais = [t["numero"] for t in cursor.fetchall()]

        resposta = {
            "empresa": empresa["nome"],
            "telefone": telefone if telefone else "Não informado",
            "telefones": telefones_oficiais
        }

        # 3. Define Status (Prioridade para Dados da Empresa se telefone estiver vazio)
        if not telefone or telefone.strip() == "":
            resposta.update({"status": "Oficial", "mensagem": "Canais oficiais registrados encontrados."})
        elif telefone in telefones_oficiais:
            resposta.update({"status": "Oficial", "mensagem": "Número verificado e seguro."})
        else:
            # Verifica se há denúncias para o número não oficial
            if telefone.startswith("(11)"):
                resposta.update({"status": "Não Oficial", "mensagem": "⚠️ Atenção: Padrão de número suspeito detectado!"})
            else:
                resposta.update({"status": "Não Oficial", "mensagem": "Este número não consta na lista oficial desta empresa."})

        conn.close()
        return resposta

    except Exception as e:
        if conn: conn.close()
        return {"status": "ERRO", "mensagem": f"Erro interno: {str(e)}"}

# --- ROTAS ---

@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None

    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        if not nome_digitado and not telefone_digitado:
            erro_formulario = "Por favor, preencha pelo menos um campo."
            return render_template("index.html", erro_formulario=erro_formulario, resultado=None)

        resultado = verificar_empresa(nome_digitado, telefone_digitado)

        if resultado.get("status") != "ERRO":
            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []
            pesquisas = session['pesquisas_recentes']
            if not pesquisas or pesquisas[0] != resultado:
                pesquisas.insert(0, resultado)
                session['pesquisas_recentes'] = pesquisas[:5]
                session.modified = True 

    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

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

    pesquisas_historico = session.get('pesquisas_recentes', [])
    return render_template("usuario.html", pesquisas=pesquisas_historico, resultado=resultado_local)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))
    erro = None
    if request.method == "POST":
        u = request.form.get("usuario", "").strip()
        s = request.form.get("senha", "").strip()
        if u == "admin" and s == "123":
            session["usuario_logado"] = u
            return redirect(url_for('perfil_usuario'))
        erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/contato")
def contato():
    return render_template("contato.html")

@app.route("/historico")
def historico():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    return render_template("historico.html", pesquisas=session.get('pesquisas_recentes', []))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
