from flask import Flask, render_template, request
import mysql.connector
import os

app = Flask(__name__)

# =========================
# CONFIGURAÇÃO DE CONEXÃO
# =========================
def conectar():
    """
    Tenta conectar ao banco de dados usando variáveis de ambiente.
    Se falhar (como no caso do Render sem banco configurado), 
    retorna None para evitar o erro 500.
    """
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
# LÓGICA DE VERIFICAÇÃO
# =========================
def verificar_empresa(nome, telefone=None):
    conn = conectar()

    # MODO DE SEGURANÇA: Se o banco de dados não estiver disponível, 
    # retorna uma simulação para o site não cair no Render.
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

        # 1. Busca a Empresa
        cursor.execute("SELECT * FROM empresa WHERE nome = %s", (nome,))
        empresa = cursor.fetchone()

        if not empresa:
            conn.close()
            return {
                "status": "ERRO",
                "mensagem": "Empresa não encontrada em nossa base de dados oficial."
            }

        # 2. Busca Telefones Oficiais
        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (empresa["id"],))
        telefones = [t["numero"] for t in cursor.fetchall()]

        # 3. Tratamento de Emails (Tabela não encontrada no SQL original)
        # Aqui deixamos uma lista padrão para evitar erro de consulta em tabela inexistente.
        emails = ["atendimento@oficial.com.br"]

        # 4. Busca Denúncias (se um telefone foi informado)
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

        # Resposta Base
        resposta = {
            "empresa": empresa["nome"],
            "telefones": telefones,
            "emails": emails
        }

        # Regras de Status
        if not telefone:
            resposta["status"] = "CANAIS"
            resposta["mensagem"] = "Estes são os canais oficiais registrados para esta empresa."
            return resposta

        if telefone in telefones:
            resposta["status"] = "OFICIAL"
            resposta["mensagem"] = "Este é um número verificado e pertence à empresa."
            return resposta

        if denuncias:
            resposta["status"] = "ALERTA"
            resposta["mensagem"] = "Atenção! Este número possui denúncias de atividades suspeitas."
            resposta["denuncias"] = denuncias
            return resposta

        # Caso não seja oficial e não tenha denúncias
        resposta["status"] = "NAO_OFICIAL"
        resposta["mensagem"] = "Este número NÃO consta na lista oficial da empresa."
        return resposta

    except Exception as e:
        if conn: conn.close()
        return {
            "status": "ERRO",
            "mensagem": f"Erro interno no processamento: {str(e)}"
        }

# =========================
# ROTAS DO SITE
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None

    if request.method == "POST":
        nome_empresa = request.form.get("nome")
        numero_tel = request.form.get("telefone")

        # Limpa o telefone removendo espaços
        if numero_tel:
            numero_tel = numero_tel.strip()
            if numero_tel == "":
                numero_tel = None

        resultado = verificar_empresa(nome_empresa, numero_tel)

    return render_template("index.html", resultado=resultado)

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    # Em produção (Render), o host deve ser 0.0.0.0
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
