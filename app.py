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

from flask import Flask, render_template, request, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = 'chave_secreta_projeto_acex' # Necessário para usar session

# --- FUNÇÃO DE LÓGICA (O "CÉREBRO" DO APP) ---
def verificar_empresa(nome, telefone):
    """
    Lógica para o Projeto ACEX:
    1. Se não houver telefone: Retorna dados da empresa.
    2. Se telefone começar com (11): Retorna Não Oficial (Simulação de Golpe).
    3. Caso contrário: Retorna Oficial.
    """
    # Se o usuário buscou apenas pelo nome
    if nome and not telefone:
        return {
            "status": "Oficial",
            "empresa": nome,
            "telefone": "Não informado",
            "mensagem": f"Informações oficiais encontradas para a empresa {nome}."
        }
    
    # Se houver telefone, verificamos o padrão de fraude (11)
    if telefone:
        if telefone.startswith("(11)"):
            return {
                "status": "Não Oficial",
                "empresa": nome if nome else "Empresa Desconhecida",
                "telefone": telefone,
                "mensagem": "⚠️ Atenção: Este número NÃO é um canal oficial. Evite fornecer dados!"
            }
        else:
            return {
                "status": "Oficial",
                "empresa": nome if nome else "Empresa Verificada",
                "telefone": telefone,
                "mensagem": "Este número é verificado e seguro para contato."
            }
    
    return {"status": "ERRO", "mensagem": "Dados insuficientes."}

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

        # Salva no histórico da sessão
        if resultado.get("status") != "ERRO":
            if 'pesquisas_recentes' not in session:
                session['pesquisas_recentes'] = []
            
            pesquisas = session['pesquisas_recentes']
            # Evita duplicados idênticos seguidos
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

            if resultado_local.get("status") != "ERRO":
                if 'pesquisas_recentes' not in session:
                    session['pesquisas_recentes'] = []
                
                pesquisas = session['pesquisas_recentes']
                pesquisas.insert(0, resultado_local)
                session['pesquisas_recentes'] = pesquisas[:5]
                session.modified = True 

    pesquisas_historico = session.get('pesquisas_recentes', [])
    # IMPORTANTE: Enviando como 'resultado' para bater com o HTML do idoso
    return render_template("usuario.html", pesquisas=pesquisas_historico, resultado=resultado_local)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))
    
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario", "").strip()
        senha_digitada = request.form.get("senha", "").strip()
        
        if usuario_digitado == "admin" and senha_digitada == "123":
            session["usuario_logado"] = usuario_digitado
            return redirect(url_for('perfil_usuario'))
        else:
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
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("historico.html", pesquisas=pesquisas)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
