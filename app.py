from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__)

# =========================
# CONEXÃO
# =========================
def conectar():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except:
        return None


# =========================
# VERIFICAÇÃO PRINCIPAL
# =========================
def verificar_empresa(nome, telefone=None):

    conn = conectar()

    # 🔥 SE NÃO CONECTAR NO BANCO → NÃO QUEBRA
    if conn is None:
        return {
            "empresa": nome,
            "telefones": ["11999999999"],
            "emails": ["contato@empresa.com"],
            "status": "SIMULACAO",
            "mensagem": "Sistema em modo demonstração (sem banco de dados)"
        }

    try:
        cursor = conn.cursor(dictionary=True)

        # Empresa
        cursor.execute("SELECT * FROM empresa WHERE nome = %s", (nome,))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {
                "status": "ERRO",
                "mensagem": "Empresa não encontrada."
            }

        # Telefones
        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
        telefones = [t["numero"] for t in cursor.fetchall()]

        # ⚠️ REMOVIDO (não existe no seu banco)
        # cursor.execute("SELECT email FROM email WHERE empresa_id = %s", (empresa["id"],))
        # emails = [e["email"] for e in cursor.fetchall()]

        emails = ["contato@empresa.com"]  # fallback simples

        # Denúncias
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

        # Resposta base
        resposta = {
            "empresa": empresa["nome"],
            "telefones": telefones,
            "emails": emails
        }

        # Regras
        if not telefone:
            resposta["status"] = "CANAIS"
            resposta["mensagem"] = "Canais oficiais da empresa"
            return resposta

        if telefone in telefones:
            resposta["status"] = "OFICIAL"
            resposta["mensagem"] = "Número oficial"
            return resposta

        if denuncias:
            resposta["status"] = "ALERTA"
            resposta["mensagem"] = "Número com denúncias!"
            resposta["denuncias"] = denuncias
            return resposta

        resposta["status"] = "NAO_OFICIAL"
        resposta["mensagem"] = "Número não oficial"
        return resposta

    except Exception as e:
        return {
            "status": "ERRO",
            "mensagem": f"Erro interno: {str(e)}"
        }


# =========================
# ROTA
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None

    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")

        telefone = telefone.strip() if telefone and telefone.strip() != "" else None

        resultado = verificar_empresa(nome, telefone)

    return render_template("index.html", resultado=resultado)


# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(debug=True)
