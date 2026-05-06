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
# VERIFICAÇÃO (PAGINAÇÃO ADICIONADA)
# =========================
def verificar_empresa(nome=None, telefone=None, pagina=1):
    conn = conectar()
    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        telefone_limpo = limpar_telefone(telefone)

        # 1. BUSCA POR TELEFONE (Mantida Original)
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

        # 2. BUSCA POR NOME (COM PAGINAÇÃO PARA NÃO TRAVAR)
        if nome:
            por_pagina = 10
            offset = (pagina - 1) * por_pagina

            # Conta total de ocorrências
            cursor.execute("SELECT COUNT(*) FROM estabelecimentos_raw WHERE nome_fantasia ILIKE %s", (f"%{nome}%",))
            total_resultados = cursor.fetchone()['count']

            if total_resultados == 0:
                conn.close()
                return {"status": "NAO_CADASTRADA", "mensagem": "Empresa não encontrada."}

            # Busca limitada com OFFSET
            cursor.execute("""
                SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf 
                FROM estabelecimentos_raw 
                WHERE nome_fantasia ILIKE %s 
                ORDER BY nome_fantasia ASC 
                LIMIT %s OFFSET %s
            """, (f"%{nome}%", por_pagina, offset))
            
            empresas_encontradas = cursor.fetchall()
            total_paginas = (total_resultados + por_pagina - 1) // por_pagina

            # Caso tenha Telefone junto (Validação Oficial)
            if telefone:
                empresa = empresas_encontradas[0]
                telefones_brutos = []
                if empresa['ddd1'] and empresa['telefone1']:
                    telefones_brutos.append(empresa['ddd1'] + empresa['telefone1'])
                if empresa['ddd2'] and empresa['telefone2']:
                    telefones_brutos.append(empresa['ddd2'] + empresa['telefone2'])

                resposta = {
                    "empresa": empresa["nome_fantasia"],
                    "telefones": [formatar_telefone(empresa['ddd1'], empresa['telefone1'])],
                    "telefone": telefone,
                    "uf": empresa["uf"]
                }
                if telefone_limpo in telefones_brutos:
                    resposta.update({"status": "OFICIAL", "mensagem": "Número verificado e seguro."})
                else:
                    resposta.update({"status": "NAO_OFICIAL", "mensagem": "Número não consta como oficial."})
                conn.close()
                return resposta

            # Retorno da Lista formatada
            lista_resultados = []
            for emp in empresas_encontradas:
                tels = []
                if emp['ddd1'] and emp['telefone1']: tels.append(formatar_telefone(emp['ddd1'], emp['telefone1']))
                if emp['ddd2'] and emp['telefone2']: tels.append(formatar_telefone(emp['ddd2'], emp['telefone2']))
                lista_resultados.append({"empresa": emp["nome_fantasia"], "telefones": tels, "uf": emp["uf"]})

            conn.close()
            return {
                "status": "LISTA",
                "resultados": lista_resultados,
                "total_resultados": total_resultados,
                "pagina_atual": pagina,
                "total_paginas": total_paginas,
                "nome_buscado": nome,
                "mensagem": f"Encontradas {total_resultados} empresas."
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
    
    # Captura dados tanto de POST (form) quanto GET (paginação)
    nome = request.form.get("nome") or request.args.get("nome", "").strip()
    telefone = request.form.get("telefone") or request.args.get("telefone", "").strip()
    pagina = request.args.get("pagina", 1, type=int)

    if request.method == "POST" or (request.method == "GET" and nome):
        if not nome and not telefone:
            if request.method == "POST": erro_formulario = "Informe nome ou telefone"
        else:
            resultado = verificar_empresa(nome, telefone, pagina)
            
    return render_template("index.html", resultado=resultado, erro_formulario=erro_formulario)

@app.route("/usuario", methods=["GET", "POST"])
def perfil_usuario():
    if "usuario_logado" not in session: return redirect(url_for('login'))
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
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    mensagem = None
    if request.method == "POST": mensagem = "Funcionalidade em manutenção."
    return render_template("admin.html", mensagem=mensagem)

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
