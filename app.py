from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_segura_acex")

# =========================
# CONEXÃO
# =========================
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

# =========================
# UTIL
# =========================
def limpar_telefone(tel):
    return ''.join(filter(str.isdigit, tel or ""))

# =========================
# VERIFICAÇÃO
# =========================
def verificar_empresa(nome=None, telefone=None):
    conn = conectar()

    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        telefone = limpar_telefone(telefone)

        # 🔍 BUSCA POR TELEFONE
        if telefone and not nome:
            cursor.execute("""
                SELECT e.nome, t.numero
                FROM telefone t
                JOIN empresa e ON t.empresa_id = e.id
                WHERE regexp_replace(t.numero, '\\D', '', 'g') = %s
            """, (telefone,))
            
            resultado = cursor.fetchone()

            conn.close()

            if resultado:
                return {
                    "empresa": resultado["nome"],
                    "telefone": telefone,
                    "status": "ENCONTRADO",
                    "mensagem": "Telefone vinculado a uma empresa."
                }
            else:
                return {
                    "empresa": None,
                    "telefone": telefone,
                    "status": "NAO_ENCONTRADO",
                    "mensagem": "Telefone não encontrado."
                }

        empresa = None

        # 🔍 BUSCA POR NOME
        if nome:
            cursor.execute("""
                SELECT * FROM empresa
                WHERE nome ILIKE %s
            """, (f"%{nome}%",))
            
            empresa = cursor.fetchone()

            if not empresa:
                conn.close()
                return {
                    "empresa": nome,
                    "status": "NAO_CADASTRADA",
                    "mensagem": "Empresa não encontrada."
                }

        telefones = []

        if empresa:
            cursor.execute("""
                SELECT id, numero FROM telefone
                WHERE empresa_id = %s
            """, (empresa["id"],))
            
            dados_tel = cursor.fetchall()
            telefones = [limpar_telefone(t["numero"]) for t in dados_tel]

        resposta = {
            "empresa": empresa["nome"] if empresa else None,
            "telefones": telefones,
            "telefone": telefone if telefone else "Não informado"
        }

        # 📊 SÓ EMPRESA
        if nome and not telefone:
            resposta.update({
                "status": "CANAIS",
                "mensagem": "Canais oficiais da empresa."
            })

        # 📊 EMPRESA + TELEFONE
        elif nome and telefone:
            if telefone in telefones:
                resposta.update({
                    "status": "OFICIAL",
                    "mensagem": "Número verificado e seguro."
                })
            else:
                cursor.execute("""
                    SELECT d.tipo
                    FROM denuncia d
                    JOIN telefone t ON d.telefone_id = t.id
                    WHERE regexp_replace(t.numero, '\\D', '', 'g') = %s
                """, (telefone,))
                
                denuncia = cursor.fetchone()

                if denuncia:
                    resposta.update({
                        "status": "ALERTA",
                        "mensagem": "Número possui denúncias!"
                    })
                else:
                    resposta.update({
                        "status": "NAO_OFICIAL",
                        "mensagem": "Número não é oficial."
                    })

        else:
            resposta.update({
                "status": "ERRO",
                "mensagem": "Informe nome ou telefone."
            })

        conn.close()
        return resposta

    except Exception as e:
        if conn:
            conn.close()
        return {"status": "ERRO", "mensagem": str(e)}

# =========================
# ROTAS
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()

        if not nome and not telefone:
            erro_formulario = "Informe nome ou telefone"
        else:
            resultado = verificar_empresa(nome, telefone)

    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session:
        return redirect(url_for('perfil_usuario'))

    erro = None

    if request.method == "POST":
        if request.form.get("usuario") == "admin" and request.form.get("senha") == "123":
            session["usuario_logado"] = "admin"
            return redirect(url_for('perfil_usuario'))
        else:
            erro = "Usuário ou senha incorretos."

    return render_template("login.html", erro=erro)

# =========================
# PROTEÇÃO SIMPLES
# =========================
def proteger():
    return "usuario_logado" in session

# =========================
# ROTAS ADMIN (PROTEGIDAS)
# =========================
@app.route("/add-empresa")
def add_empresa():
    if not proteger():
        return "Acesso negado"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO empresa (nome) VALUES ('Banco do Brasil')")
    conn.commit()
    conn.close()

    return "Empresa adicionada!"
