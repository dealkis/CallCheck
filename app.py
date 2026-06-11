from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_segura_acex")

# =========================
# CONEXÃO COM POOL DE CONEXÕES
# =========================
MIN_CONNS = 1
MAX_CONNS = 20
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_o51wyEXnCMpg@ep-plain-morning-ac3tue24-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

pool = None
try:
    pool = ThreadedConnectionPool(MIN_CONNS, MAX_CONNS, DB_URL)
except Exception as e:
    print("Erro ao inicializar o pool de conexões:", e)

@contextmanager
def conectar():
    """Gerenciador de contexto que substitui a antiga conexão direta e utiliza o Pool"""
    if not pool:
        yield None
        return
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

# =========================
# UTILITÁRIOS
# =========================
def limpar_telefone(tel):
    return ''.join(filter(str.isdigit, tel or ""))

def formatar_telefone(ddd, num):
    if not ddd or not num:
        return "Não informado"
    num = "".join(filter(str.isdigit, num))
    ddd = "".join(filter(str.isdigit, ddd))
    if len(num) == 9:
        return f"({ddd}) {num[0]} {num[1:5]}-{num[5:]}"
    elif len(num) == 8:
        return f"({ddd}) {num[0:4]}-{num[4:]}"
    else:
        return f"({ddd}) {num}"

# =========================
# LÓGICA DE VERIFICAÇÃO (NOME + TELEFONE + DENÚNCIAS)
# =========================
def verificar_empresa(nome=None, telefone=None, pagina=1, uf=None):
    with conectar() as conn:
        if conn is None:
            return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            telefone_limpo = limpar_telefone(telefone)

            # CAMADA ADICIONAL DE SEGURANÇA: VERIFICAR DENÚNCIAS PRIMEIRO
            if telefone_limpo:
                try:
                    cursor.execute("SELECT * FROM denuncias WHERE telefone = %s LIMIT 1", (telefone_limpo,))
                    denuncia = cursor.fetchone()
                    if denuncia:
                        return {
                            "empresa": nome or "Número Desconhecido",
                            "telefone": telefone,
                            "status": "RISCO",
                            "uf": uf,
                            "mensagem": f"ALERTA: Este número possui denúncias registradas! Motivo: {denuncia.get('motivo', 'Atividades suspeitas')}."
                        }
                except Exception as e:
                    # Em caso de erro na tabela denuncias, continua o fluxo normal preventivamente
                    print("Aviso: Tabela de denúncias pode não existir ainda.", e)

            # CENÁRIO 1: BUSCA POR NOME E TELEFONE JUNTOS
            if nome and telefone_limpo:
                termo_busca = f"%{nome}%"
                query = """
                    SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf 

                    FROM estabelecimentos_raw 
                    WHERE nome_fantasia ILIKE %s 
                      AND ((ddd1 || telefone1) = %s OR (ddd2 || telefone2) = %s)
                """
                parametros = [termo_busca, telefone_limpo, telefone_limpo]
                if uf and uf.strip():
                    query += " AND uf = %s"
                    parametros.append(uf.strip().upper())

                cursor.execute(query + " LIMIT 1", tuple(parametros))


                resultado = cursor.fetchone()

                if resultado:
                    return {
                        "empresa": resultado["nome_fantasia"],
                        "telefone": formatar_telefone(resultado["ddd1"], resultado["telefone1"]),
                        "status": "OFICIAL",
                        "uf": resultado["uf"],
                        "mensagem": "Número verificado e seguro!"
                    }
                else:
                    return {
                        "empresa": nome,
                        "telefone": telefone,
                        "status": "NAO_OFICIAL",
                        "mensagem": "Número não consta como oficial para esta empresa."
                    }

            # CENÁRIO 2: BUSCA APENAS POR TELEFONE
            elif telefone_limpo and not nome:

                cursor.execute("""
                    SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf
                    FROM estabelecimentos_raw 
                    WHERE (ddd1 || telefone1) = %s OR (ddd2 || telefone2) = %s
                    LIMIT 1
                """, (telefone_limpo, telefone_limpo))
                resultado = cursor.fetchone()

                if resultado:
                    return {
                        "empresa": resultado["nome_fantasia"] or "Empresa Registrada",
                        "telefone": formatar_telefone(resultado["ddd1"], resultado["telefone1"]),
                        "status": "ENCONTRADO",
                        "uf": resultado["uf"],
                        "mensagem": f"Telefone vinculado a uma empresa em {resultado['uf']}."
                    }
                return {"empresa": None, "telefone": telefone, "status": "NAO_ENCONTRADO", "mensagem": "Telefone não encontrado."}

            # CENÁRIO 3: BUSCA APENAS POR NOME (PAGINADA)
            elif nome:
                por_pagina = 10
                offset = (pagina - 1) * por_pagina
                termo_busca = f"%{nome}%"
                query_base = "WHERE nome_fantasia ILIKE %s"
                parametros = [termo_busca]






                if uf and uf.strip():
                    query_base += " AND uf = %s"
                    parametros.append(uf.strip().upper())

                cursor.execute(f"""
                    SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf 
                    FROM estabelecimentos_raw 
                    {query_base}
                    ORDER BY nome_fantasia ASC 
                    LIMIT %s OFFSET %s
                """, tuple(parametros + [por_pagina + 1, offset]))
                
                empresas = cursor.fetchall()

                tem_proxima = len(empresas) > por_pagina
                lista_resultados = []
                for emp in empresas[:por_pagina]:
                    tels = []
                    if emp['ddd1'] and emp['telefone1']: tels.append(formatar_telefone(emp['ddd1'], emp['telefone1']))
                    lista_resultados.append({"empresa": emp["nome_fantasia"], "telefones": tels, "uf": emp["uf"]})

                return {
                    "status": "LISTA",
                    "resultados": lista_resultados,
                    "pagina_atual": pagina,
                    "tem_proxima": tem_proxima,
                    "nome_buscado": nome,
                    "mensagem": f"Resultados para a busca '{nome}'."
                }

            return {"status": "ERRO", "mensagem": "Informe nome ou telefone."}

        except Exception as e:
            return {"status": "ERRO", "mensagem": str(e)}

# =========================
# ROTAS PÚBLICAS E DENÚNCIAS
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    erro_formulario = None
    nome = (request.form.get("nome") or request.args.get("nome", "")).strip()
    telefone = (request.form.get("telefone") or request.args.get("telefone", "")).strip()
    uf = (request.form.get("uf") or request.args.get("uf", "")).strip()
    pagina = request.args.get("pagina", 1, type=int)

    if request.method == "POST" or (request.method == "GET" and nome):
        if not nome and not telefone:
            if request.method == "POST": erro_formulario = "Informe nome ou telefone"
        else:
            resultado = verificar_empresa(nome, telefone, pagina, uf)
    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

@app.route("/denunciar", methods=["POST"])
def enviar_denuncia():
    telefone = request.form.get("telefone", "").strip()
    motivo = request.form.get("motivo", "").strip()
    telefone_limpo = limpar_telefone(telefone)

    if telefone_limpo:
        with conectar() as conn:
            if conn:
                try:
                    cursor = conn.cursor()
                    # Cria a tabela se não existir (garantia de funcionamento)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS denuncias (
                            id SERIAL PRIMARY KEY,
                            telefone VARCHAR(20) NOT NULL,
                            motivo TEXT NOT NULL,
                            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute("INSERT INTO denuncias (telefone, motivo) VALUES (%s, %s)", (telefone_limpo, motivo))
                    conn.commit()
                except Exception as e:
                    print("Erro ao salvar denúncia:", e)

    return redirect(url_for('index', telefone=telefone))

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

# =========================
# LOGIN E PERFIL
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session: return redirect(url_for('perfil_usuario'))
    erro = None
    if request.method == "POST":
        if request.form.get("usuario") == "admin" and request.form.get("senha") == "123":
            session["usuario_logado"] = "admin"
            return redirect(url_for('perfil_usuario'))
        erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    resultado_local = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        uf = request.form.get("uf", "").strip()
        if nome or telefone:
            resultado_local = verificar_empresa(nome, telefone, 1, uf)
            pesquisas = session.get('pesquisas_recentes', [])
            pesquisas.insert(0, resultado_local)
            session['pesquisas_recentes'] = pesquisas[:5]
            session.modified = True
    return render_template("usuario.html", pesquisas=session.get('pesquisas_recentes', []), resultado_modal=resultado_local)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================
# ROTAS ESPECÍFICAS (PRESERVADAS)
# =========================
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
# ADMINISTRAÇÃO
# =========================
@app.route("/admin")
def admin():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    return render_template("admin.html")

@app.route("/admin/empresas")
def listar_empresas():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    uf_filtro = request.args.get('uf', '').upper()
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 100
    offset = (pagina - 1) * por_pagina

    with conectar() as conn:
        if not conn: return "Erro de conexão ao banco", 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            where = "WHERE nome_fantasia IS NOT NULL AND nome_fantasia != ''"
            params = []
            if uf_filtro:
                where += " AND uf = %s"; params.append(uf_filtro)

            cursor.execute(f"SELECT COUNT(*) FROM estabelecimentos_raw {where}", params)
            total_reg = cursor.fetchone()['count']
            cursor.execute(f"SELECT cnpj_base, nome_fantasia, ddd1, telefone1, uf FROM estabelecimentos_raw {where} ORDER BY nome_fantasia ASC LIMIT %s OFFSET %s", params + [por_pagina, offset])
            empresas = cursor.fetchall()
            return render_template("empresas.html", empresas=empresas, pagina=pagina, total_paginas=(total_reg // por_pagina) + 1, total_registros=total_reg, uf_atual=uf_filtro)
        except Exception as e:
            return str(e), 500

@app.route("/admin/empresa/<cnpj_base>")
def visualizar_empresa(cnpj_base):
    if "usuario_logado" not in session: return redirect(url_for('login'))
    with conectar() as conn:
        if not conn: return "Erro de conexão", 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM estabelecimentos_raw WHERE cnpj_base = %s LIMIT 1", (str(cnpj_base),))
            empresa = cursor.fetchone()
            return render_template("detalhes_empresa.html", empresa=empresa)
        except Exception as e:
            return str(e), 500

@app.route("/database_view")
def database_view():
    if "usuario_logado" not in session: return redirect(url_for('login'))

    with conectar() as conn:
        if conn is None: return "Erro ao conectar ao banco de dados.", 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT cnpj_base, nome_fantasia, ddd1, telefone1, uf 
                FROM estabelecimentos_raw 
                WHERE nome_fantasia IS NOT NULL AND nome_fantasia != ''
                LIMIT 100
            """)
            registros = cursor.fetchall()
            return render_template("database_view.html", registros=registros)
        except Exception as e:
            return f"Erro na consulta: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

'''
_____  ______          _      _  __ _____  _____ 
|  __ \|  ____|   /\   | |    | |/ /|_   _|/ ____|
| |  | | |__     /  \  | |    | ' /   | | | (___  
| |  | |  __|   / /\ \ | |    |  <    | |  \___ \ 
| |__| | |____ / ____ \| |____| . \  _| |_ ____) |
|_____/|______/_/    \_\______|_|\_\|_____|_____/

'''
