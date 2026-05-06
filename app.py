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
    # Recebe uma string de telefone e remove tudo que não for número
    return ''.join(filter(str.isdigit, tel or ""))

def formatar_telefone(ddd, num):
    """
    Transforma 11988887777 em (11) 9 8888-7777
    Ou 1133334444 em (11) 3333-4444
    """
    if not ddd or not num:
        return "Não informado"
    
    # Garante que temos apenas números
    num = "".join(filter(str.isdigit, num))
    ddd = "".join(filter(str.isdigit, ddd))
    
    # Celular (9 dígitos): (XX) 9 XXXX-XXXX
    if len(num) == 9:
        return f"({ddd}) {num[0]} {num[1:5]}-{num[5:]}"
    
    # Fixo (8 dígitos): (XX) XXXX-XXXX
    elif len(num) == 8:
        return f"({ddd}) {num[0:4]}-{num[4:]}"
    
    # Caso o número tenha um formato inesperado, retorna (DD) NUMERO
    else:
        return f"({ddd}) {num}"

# =========================
# VERIFICAÇÃO (AJUSTADA PARA A NOVA TABELA)
# =========================
def verificar_empresa(nome=None, telefone=None):
    conn = conectar()
    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        telefone_limpo = limpar_telefone(telefone)

        # 1. BUSCA POR TELEFONE
        if telefone_limpo and not nome:
            cursor.execute("""
                SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, email, uf
                FROM estabelecimentos_raw 
                WHERE (ddd1 || telefone1) = %s OR (ddd2 || telefone2) = %s
                LIMIT 1
            """, (telefone_limpo, telefone_limpo))
            
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                nome_exibir = resultado["nome_fantasia"] if resultado["nome_fantasia"] else "Empresa Registrada"
                return {
                    "empresa": nome_exibir,
                    "telefone": formatar_telefone(resultado["ddd1"], resultado["telefone1"]),
                    "status": "ENCONTRADO",
                    "uf": resultado["uf"],
                    "mensagem": f"Telefone vinculado a uma empresa em {resultado['uf']}."
                }
            else:
                return {
                    "empresa": None,
                    "telefone": telefone,
                    "status": "NAO_ENCONTRADO",
                    "mensagem": "Telefone não encontrado na base oficial."
                }

        # 2. BUSCA POR NOME
        if nome:
            cursor.execute("""
                SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf 
                FROM estabelecimentos_raw 
                WHERE nome_fantasia ILIKE %s 
                LIMIT 1
            """, (f"%{nome}%",))
            empresa = cursor.fetchone()

            if not empresa:
                conn.close()
                return {
                    "empresa": nome,
                    "status": "NAO_CADASTRADA",
                    "mensagem": "Empresa não encontrada."
                }

            telefones_formatados = []
            telefones_brutos = []
            
            if empresa['ddd1'] and empresa['telefone1']:
                telefones_brutos.append(empresa['ddd1'] + empresa['telefone1'])
                telefones_formatados.append(formatar_telefone(empresa['ddd1'], empresa['telefone1']))
            
            if empresa['ddd2'] and empresa['telefone2']:
                telefones_brutos.append(empresa['ddd2'] + empresa['telefone2'])
                telefones_formatados.append(formatar_telefone(empresa['ddd2'], empresa['telefone2']))

            resposta = {
                "empresa": empresa["nome_fantasia"],
                "telefones": telefones_formatados,
                "telefone": telefone if telefone else "Não informado",
                "uf": empresa["uf"]
            }

            if nome and not telefone:
                resposta.update({"status": "CANAIS", "mensagem": "Canais oficiais encontrados."})
            elif nome and telefone:
                if telefone_limpo in telefones_brutos:
                    resposta.update({"status": "OFICIAL", "mensagem": "Número verificado e seguro."})
                else:
                    resposta.update({"status": "NAO_OFICIAL", "mensagem": "Número não consta como oficial."})
            
            conn.close()
            return resposta

        return {"status": "ERRO", "mensagem": "Informe nome ou telefone."}

    except Exception as e:
        if conn: conn.close()
        return {"status": "ERRO", "mensagem": str(e)}

# =========================
# ROTAS PRINCIPAIS
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

@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))
    resultado_local = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        if nome or telefone:
            resultado_local = verificar_empresa(nome, telefone)
            pesquisas = session.get('pesquisas_recentes', [])
            pesquisas.insert(0, resultado_local)
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("usuario.html", pesquisas=pesquisas, resultado_modal=resultado_local)

# =========================
# LOGIN / LOGOUT
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

@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for('login'))

# =========================
# PÁGINAS ESTÁTICAS
# =========================
@app.route("/sobre")
def sobre(): return render_template("sobre.html")

@app.route("/contato")
def contato(): return render_template("contato.html")

@app.route("/historico")
def historico():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("em_obras.html", pesquisas=pesquisas)

@app.route("/denuncia")
def denuncia():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    return render_template("em_obras.html")

# =========================
# ADMIN
# =========================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    mensagem = None
    if request.method == "POST":
        mensagem = "Funcionalidade de cadastro manual em manutenção (Base Receita Ativa)."
    return render_template("admin.html", mensagem=mensagem)

@app.route("/admin/empresas")
def listar_empresas():
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    # Pega a página atual da URL (ex: ?pagina=2). Se não tiver, assume 1.
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 100
    offset = (pagina - 1) * por_pagina

    conn = conectar()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Busca as empresas da página atual
    cursor.execute("""
        SELECT nome_fantasia, ddd1, telefone1, uf 
        FROM estabelecimentos_raw 
        WHERE nome_fantasia IS NOT NULL AND nome_fantasia != ''
        ORDER BY nome_fantasia ASC 
        LIMIT %s OFFSET %s
    """, (por_pagina, offset))
    
    empresas_raw = cursor.fetchall()

    # 2. Formata os telefones
    for emp in empresas_raw:
        emp['telefone_formatado'] = formatar_telefone(emp['ddd1'], emp['telefone1'])

    conn.close()

    return render_template("empresas.html", 
                           empresas=empresas_raw, 
                           pagina=pagina)

@app.route("/admin/empresa/<cnpj>")
def visualizar_empresa(cnpj):
    if "usuario_logado" not in session:
        return redirect(url_for('login'))

    conn = conectar()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Busca absolutamente todas as colunas da empresa
    cursor.execute("SELECT * FROM estabelecimentos_raw WHERE cnpj = %s", (cnpj,))
    empresa = cursor.fetchone()
    conn.close()

    if not empresa:
        return "Empresa não encontrada", 404

    return render_template("detalhes_empresa.html", empresa=empresa)

#-----#

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
