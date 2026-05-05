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

# LÓGICA DE VERIFICAÇÃO (MELHORADA)
def verificar_empresa(nome, telefone=None):
    conn = conectar()
    
    # Se não houver banco, retorna simulação mas com a chave 'telefone'
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
        # Busca aproximada pelo nome
        cursor.execute("SELECT * FROM empresa WHERE nome LIKE %s", (f"%{nome}%",))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {"status": "ERRO", "mensagem": "Empresa não encontrada em nossa base oficial."}

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

        # Lógica de Status
        if not telefone or telefone.strip() == "":
            resposta.update({"status": "CANAIS", "mensagem": "Canais oficiais registrados."})
        elif telefone in telefones:
            resposta.update({"status": "OFICIAL", "mensagem": "Número verificado e seguro."})
        else:
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

@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None

    if request.method == "POST":
        # .strip() remove espaços extras; .replace() remove a máscara se necessário
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        if not nome_digitado and not telefone_digitado:
            erro_formulario = "Por favor, preencha pelo menos um campo."
            return render_template("index.html", erro_formulario=erro_formulario)

        # Chama a função real que consulta seu dicionário/banco
        resultado = verificar_empresa(nome_digitado, telefone_digitado)

        # Salva no histórico da sessão (máximo 5 itens)
        if resultado.get("status") != "ERRO":
            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []
            
            pesquisas = session['pesquisas_recentes']
            # Evita duplicados no histórico
            if resultado not in pesquisas:
                pesquisas.insert(0, resultado)
                session['pesquisas_recentes'] = pesquisas[:5]
                session.modified = True 

    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

# --- ROTA DO PAINEL DO USUÁRIO ---
@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
        
    resultado_local = None

    if request.method == "POST":
        nome_digitado = request.form.get("nome", "").strip()
        telefone_digitado = request.form.get("telefone", "").strip()

        if nome_digitado or telefone_digitado:
            # Chama a função de verificação real
            resultado_local = verificar_empresa(nome_digitado, telefone_digitado)

            # Só salva no histórico se for um resultado válido
            if resultado_local.get("status") != "ERRO":
                if 'pesquisas_recentes' not in session:
                    session['pesquisas_recentes'] = []
                
                pesquisas = session['pesquisas_recentes']
                pesquisas.insert(0, resultado_local)
                session['pesquisas_recentes'] = pesquisas[:5]
                session.modified = True 

    # Busca o histórico da sessão para exibir na tabela da página
    pesquisas_historico = session.get('pesquisas_recentes', [])
    
    return render_template("usuario.html", 
                           pesquisas=pesquisas_historico, 
                           resultado_modal=resultado_local)

# --- ROTAS DE ACESSO E UTILITÁRIOS ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))
    
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario")
        senha_digitada = request.form.get("senha")
        
        # Simulação de login
        if usuario_digitado == "admin" and senha_digitada == "123":
            session["usuario_logado"] = usuario_digitado
            return redirect(url_for('perfil_usuario'))
        else:
            erro = "Usuário ou senha incorretos."
            
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for('login'))

@app.route("/historico")
def historico():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("historico.html", pesquisas=pesquisas)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
