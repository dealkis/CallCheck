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
    URL_EXTERNA = "postgresql://banco_de_dados_callcheck_user:evZM58eGjtd0qMGoDveRi1DGTvOyd2d7@dpg-d7sdccd0lvsc73ae488g-a.oregon-postgres.render.com/banco_de_dados_callcheck"
    try:
        return psycopg2.connect(URL_EXTERNA)
    except Exception as e:
        print("Erro ao conectar:", e)
        return None

# =========================
# UTIL
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
# VERIFICAÇÃO (OTIMIZADA PARA OS 3 CENÁRIOS DE BUSCA)
# =========================
def verificar_empresa(nome=None, telefone=None, pagina=1, uf=None):
    conn = conectar()
    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        telefone_limpo = limpar_telefone(telefone)

        # -------------------------------------------------------------
        # CENÁRIO 1: BUSCA POR NOME E TELEFONE JUNTOS (Match Exato)
        # -------------------------------------------------------------
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

            query += " LIMIT 1"
            
            cursor.execute(query, tuple(parametros))
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                return {
                    "empresa": resultado["nome_fantasia"],
                    "telefone": formatar_telefone(resultado["ddd1"], resultado["telefone1"]),
                    "telefones": [formatar_telefone(resultado["ddd1"], resultado["telefone1"])],
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

        # -------------------------------------------------------------
        # CENÁRIO 2: BUSCA APENAS POR TELEFONE
        # -------------------------------------------------------------
        elif telefone_limpo and not nome:
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

        # -------------------------------------------------------------
        # CENÁRIO 3: BUSCA APENAS POR NOME (Com paginação)
        # -------------------------------------------------------------
        elif nome and not telefone_limpo:
            if len(nome) < 3:
                conn.close()
                return {"status": "ERRO", "mensagem": "Digite pelo menos 3 caracteres para buscar por nome."}

            por_pagina = 10
            offset = (pagina - 1) * por_pagina
            limite_busca = por_pagina + 1 
            
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
            """, tuple(parametros + [limite_busca, offset]))
            
            empresas_encontradas = cursor.fetchall()
            conn.close()

            if not empresas_encontradas and pagina == 1:
                return {"status": "NAO_CADASTRADA", "mensagem": "Nenhuma empresa encontrada com este nome."}

            tem_proxima = len(empresas_encontradas) > por_pagina
            if tem_proxima:
                empresas_encontradas = empresas_encontradas[:por_pagina]

            lista_resultados = []
            for emp in empresas_encontradas:
                tels = []
                if emp['ddd1'] and emp['telefone1']: tels.append(formatar_telefone(emp['ddd1'], emp['telefone1']))
                if emp['ddd2'] and emp['telefone2']: tels.append(formatar_telefone(emp['ddd2'], emp['telefone2']))
                lista_resultados.append({"empresa": emp["nome_fantasia"], "telefones": tels, "uf": emp["uf"]})

            return {
                "status": "LISTA",
                "resultados": lista_resultados,
                "pagina_atual": pagina,
                "tem_proxima": tem_proxima,
                "nome_buscado": nome,
                "uf_buscada": uf,
                "mensagem": f"Resultados para a busca '{nome}'."
            }

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
    nome = request.form.get("nome") or request.args.get("nome", "").strip()
    telefone = request.form.get("telefone") or request.args.get("telefone", "").strip()
    uf = request.form.get("uf") or request.args.get("uf", "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    if request.method == "POST" or (request.method == "GET" and nome):
        if not nome and not telefone:
            if request.method == "POST": erro_formulario = "Informe nome ou telefone"
        else:
            resultado = verificar_empresa(nome, telefone, pagina, uf)
    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

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
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("usuario.html", pesquisas=pesquisas, resultado_modal=resultado_local)

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session: return redirect(url_for('perfil_usuario'))
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
@app.route("/admin/empresas")
def listar_empresas():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    uf_filtro = request.args.get('uf', '').upper()
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = 100
    offset = (pagina - 1) * por_pagina
    conn = conectar()
    if not conn: return "Erro banco", 500
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        base_where = "WHERE nome_fantasia IS NOT NULL AND nome_fantasia != ''"
        params = []
        if uf_filtro:
            base_where += " AND uf = %s"
            params.append(uf_filtro)
        cursor.execute(f"SELECT COUNT(*) FROM estabelecimentos_raw {base_where}", params)
        total_reg = cursor.fetchone()['count']
        total_pag = (total_reg + por_pagina - 1) // por_pagina
        cursor.execute(f"SELECT cnpj_base, nome_fantasia, ddd1, telefone1, uf FROM estabelecimentos_raw {base_where} ORDER BY nome_fantasia ASC LIMIT %s OFFSET %s", params + [por_pagina, offset])
        empresas = cursor.fetchall()
        for emp in empresas: emp['telefone_formatado'] = formatar_telefone(emp.get('ddd1'), emp.get('telefone1'))
        conn.close()
        return render_template("empresas.html", empresas=empresas, pagina=pagina, total_paginas=total_pag, total_registros=total_reg, uf_atual=uf_filtro)
    except Exception as e:
        return str(e), 500

@app.route("/admin/empresa/<cnpj_base>")
def visualizar_empresa(cnpj_base):
    if "usuario_logado" not in session: return redirect(url_for('login'))
    conn = conectar()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM estabelecimentos_raw WHERE cnpj_base = %s LIMIT 1", (str(cnpj_base),))
    empresa = cursor.fetchone()
    conn.close()
    return render_template("detalhes_empresa.html", empresa=empresa)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

#  _____   ______         _        _  __ _____  _____ 
# |  __ \ |  ____|   /\   | |      | |/ /|_   _|/ ____|
# | |  | || |__     /  \  | |      | ' /   | | | (___  
# | |  | ||  __|   / /\ \ | |      |  <    | |  \___ \ 
# | |__| || |____ / ____ \| |____  | . \  _| |_ ____) |
# |_____/ |______/_/    \_\______| |_|\_\|_____|_____/
