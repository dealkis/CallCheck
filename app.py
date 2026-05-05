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
    resultado = None
    erro_formulario = None # Variável para guardar o erro de campo vazio

    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        # VALIDAÇÃO: Se o usuário não digitou NADA em nenhum dos campos
        if not nome_digitado and not telefone_digitado:
            erro_formulario = "Por favor, informe pelo menos o nome da empresa ou um telefone."
            return render_template("index.html", erro_formulario=erro_formulario)

        # Lógica de status (PARA TESTE)
        if request.method == "POST":
            nome_digitado = request.form.get("nome", "").strip()
            telefone_digitado = request.form.get("telefone", "").strip()
        
            # PRIORIDADE 1: Se o usuário pesquisou APENAS pelo nome
            if nome_digitado and not telefone_digitado:
                status_simulado = "Oficial"
                mensagem_simulada = f"Informações oficiais encontradas para a empresa {nome_digitado}."
                
                # Preparamos os dados para exibição
                empresa_exibir = nome_digitado
                telefone_exibir = "Não informado"
        
            # PRIORIDADE 2: Se o usuário inseriu um telefone (com ou sem nome)
            elif telefone_digitado:
                # A verificação de fraude agora usa o telefone_digitado com a máscara (11)
                if telefone_digitado.startswith("(11)"):
                    status_simulado = "Não Oficial"
                    mensagem_simulada = "Atenção: Este número NÃO é um canal oficial de atendimento."
                else:
                    status_simulado = "Oficial"
                    mensagem_simulada = "Este número é verificado e seguro para contato."
                
                empresa_exibir = nome_digitado if nome_digitado else "Empresa não identificada"
                telefone_exibir = telefone_digitado
        
            # Criando o dicionário que o seu usuario.html e index.html já usam
            resultado = {
                "empresa": empresa_exibir,
                "telefone": telefone_exibir,
                "status": status_simulado,
                "mensagem": mensagem_simulada
            }

        # Salva no histórico da sessão
        if 'pesquisas_recentes' not in session:
            session['pesquisas_recentes'] = []
        
        pesquisas = session['pesquisas_recentes']
        pesquisas.insert(0, resultado)
        session['pesquisas_recentes'] = pesquisas[:5]
        session.modified = True 

    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

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

@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
        
    resultado_local = None

    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        if nome_digitado or telefone_digitado:
            status_simulado = "Não Oficial" if telefone_digitado.startswith("(11)") else "Oficial"
            
            resultado_local = {
                "empresa": nome_digitado if nome_digitado else "Não informada",
                "telefone": telefone_digitado if telefone_digitado else "---",
                "status": status_simulado,
                "mensagem": "Verificado com sucesso!"
            }

            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []
            
            pesquisas = session['pesquisas_recentes']
            pesquisas.insert(0, resultado_local)
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True 

    pesquisas = session.get('pesquisas_recentes', [])
    # Passamos o resultado_local aqui para o HTML saber que deve abrir a caixa
    return render_template("usuario.html", pesquisas=pesquisas, resultado_modal=resultado_local)
    
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
