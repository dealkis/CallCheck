from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_segura_acex")

# =========================================
# CONEXÃO COM POOL DE CONEXÕES (PRESERVADO)
# =========================================
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
    """Gerenciador de contexto que gerencia o Pool de conexões"""
    if not pool:
        yield None
        return
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

# =========================================
# UTILITÁRIOS (PRESERVADOS)
# =========================================
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

# =========================================
# LÓGICA DE VERIFICAÇÃO ADAPTADA (JOINs)
# =========================================
def verificar_empresa(nome=None, telefone=None, pagina=1, uf=None):
    with conectar() as conn:
        if conn is None:
            return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            telefone_limpo = limpar_telefone(telefone)

            # CAMADA DE SEGURANÇA: VERIFICAR DENÚNCIAS VIA RELACIONAMENTO
            if telefone_limpo:
                cursor.execute("""
                    SELECT d.tipo, d.descricao, t.numero 
                    FROM denuncia d
                    JOIN telefone t ON d.telefone_id = t.id
                    WHERE t.numero = %s 
                    LIMIT 1
                """, (telefone_limpo,))
                denuncia = cursor.fetchone()
                if denuncia:
                    return {
                        "empresa": nome or "Número Desconhecido",
                        "telefone": telefone,
                        "status": "RISCO",
                        "uf": "N/A",  # Novo esquema não possui coluna UF
                        "mensagem": f"ALERTA: Este número possui denúncias registradas! Motivo: {denuncia.get('descricao') or denuncia.get('tipo', 'Atividades suspeitas')}."
                    }

            # CENÁRIO 1: BUSCA POR NOME E TELEFONE JUNTOS
            if nome and telefone_limpo:
                termo_busca = f"%{nome}%"
                query = """
                    SELECT e.nome AS nome_fantasia, t.numero, e.verificada
                    FROM empresa e
                    JOIN telefone t ON e.id = t.empresa_id
                    WHERE e.nome ILIKE %s AND t.numero = %s
                """
                cursor.execute(query + " LIMIT 1", (termo_busca, telefone_limpo))
                resultado = cursor.fetchone()

                if resultado:
                    return {
                        "empresa": resultado["nome_fantasia"],
                        "telefone": resultado["numero"],
                        "status": "OFICIAL",
                        "uf": "N/A",
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
                    SELECT e.nome AS nome_fantasia, t.numero
                    FROM empresa e
                    JOIN telefone t ON e.id = t.empresa_id
                    WHERE t.numero = %s
                    LIMIT 1
                """, (telefone_limpo,))
                resultado = cursor.fetchone()

                if resultado:
                    return {
                        "empresa": resultado["nome_fantasia"] or "Empresa Registrada",
                        "telefone": resultado["numero"],
                        "status": "ENCONTRADO",
                        "uf": "N/A",
                        "mensagem": "Telefone vinculado a uma empresa cadastrada."
                    }
                return {"empresa": None, "telefone": telefone, "status": "NAO_ENCONTRADO", "mensagem": "Telefone não encontrado."}

            # CENÁRIO 3: BUSCA APENAS POR NOME (PAGINADA)
            elif nome:
                por_pagina = 10
                offset = (pagina - 1) * por_pagina
                termo_busca = f"%{nome}%"

                cursor.execute("""
                    SELECT e.nome AS nome_fantasia, t.numero
                    FROM empresa e
                    LEFT JOIN telefone t ON e.id = t.empresa_id AND t.principal = TRUE
                    WHERE e.nome ILIKE %s
                    ORDER BY e.nome ASC 
                    LIMIT %s OFFSET %s
                """, (termo_busca, por_pagina + 1, offset))
                
                empresas = cursor.fetchall()
                tem_proxima = len(empresas) > por_pagina
                lista_resultados = []
                
                for emp in empresas[:por_pagina]:
                    tels = [emp['numero']] if emp['numero'] else []
                    lista_resultados.append({
                        "empresa": emp["nome_fantasia"], 
                        "telefones": tels, 
                        "uf": "N/A"
                    })

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

# =========================================
# ROTAS PÚBLICAS E DENÚNCIAS
# =========================================
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
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # 1. Garante integridade: Procura ou cria Usuário de auditoria padrão
                    cursor.execute("SELECT id FROM usuario LIMIT 1")
                    user_row = cursor.fetchone()
                    usuario_id = user_row['id'] if user_row else 1
                    
                    # 2. Procura ou cria o Telefone/Empresa base para amarrar a FK de denúncia
                    cursor.execute("SELECT id FROM telefone WHERE numero = %s LIMIT 1", (telefone_limpo,))
                    tel_row = cursor.fetchone()
                    
                    if tel_row:
                        telefone_id = tel_row['id']
                    else:
                        cursor.execute("INSERT INTO empresa (nome, cnpj, verificada) VALUES (%s, %s, FALSE) RETURNING id", ("Origem Desconhecida", "00000000000000"))
                        nova_emp_id = cursor.fetchone()['id']
                        cursor.execute("INSERT INTO telefone (numero, empresa_id, tipo, suspeito, principal) VALUES (%s, %s, 'desconhecido', TRUE, TRUE) RETURNING id", (telefone_limpo, nova_emp_id))
                        telefone_id = cursor.fetchone()['id']

                    # 3. Classifica o tipo de acordo com a regra ENUM informada
                    tipo_enum = 'spam'
                    motivo_lower = motivo.lower()
                    if 'golpe' in motivo_lower: tipo_enum = 'golpe'
                    elif 'fraude' in motivo_lower: tipo_enum = 'fraude'

                    # 4. Grava na nova tabela de denúncias relacionais
                    cursor.execute("""
                        INSERT INTO denuncia (telefone_id, tipo, descricao, data_registro, usuario_id) 
                        VALUES (%s, %s, %s, NOW(), %s)
                    """, (telefone_id, tipo_enum, motivo, usuario_id))
                    
                    # 5. Atualiza o status do telefone para suspeito
                    cursor.execute("UPDATE telefone SET suspeito = TRUE WHERE id = %s", (telefone_id,))
                    
                    # 6. Registra no histórico de ações
                    cursor.execute("""
                        INSERT INTO historico_acao (usuario_id, acao, descricao, ip, realizado_em) 
                        VALUES (%s, 'criou_denuncia', %s, %s, NOW())
                    """, (usuario_id, f"Denúncia cadastrada para o número: {telefone_limpo}", request.remote_addr))
                    
                    conn.commit()
                except Exception as e:
                    print("Erro ao salvar denúncia na estrutura relacional:", e)

    return redirect(url_for('index', telefone=telefone))

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

# =========================================
# LOGIN E PERFIL (PRESERVADOS E ADAPTADOS)
# =========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session: return redirect(url_for('perfil_usuario'))
    erro = None
    if request.method == "POST":
        # Mantém a autenticação mockada existente para não quebrar fluxos administrativos antigos
        if request.form.get("usuario") == "admin" and request.form.get("senha") == "123":
            session["usuario_logado"] = "admin"
            
            # Grava a sessão na tabela 'sessao' caso exista um usuário administrador básico na base
            with conectar() as conn:
                if conn:
                    try:
                        cursor = conn.cursor(cursor_factory=RealDictCursor)
                        cursor.execute("SELECT id FROM usuario WHERE nivel = 'admin' LIMIT 1")
                        user_admin = cursor.fetchone()
                        uid = user_admin['id'] if user_admin else 1
                        
                        cursor.execute("""
                            INSERT INTO sessao (usuario_id, token, ip, user_agent, criado_em, expira_em, ativo)
                            VALUES (%s, 'token_admin_mock', %s, %s, NOW(), NOW() + INTERVAL '1 day', TRUE)
                        """, (uid, request.remote_addr, request.headers.get('User-Agent', '')))
                        
                        cursor.execute("""
                            INSERT INTO historico_acao (usuario_id, acao, descricao, ip, realizado_em)
                            VALUES (%s, 'login', 'Administrador logou no sistema', %s, NOW())
                        """, (uid, request.remote_addr))
                        conn.commit()
                    except Exception as e:
                        print("Erro ao registrar metadados de sessão:", e)
                        
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

# =========================================
# ROTAS ESPECÍFICAS (PRESERVADAS)
# =========================================
@app.route("/historico")
def historico():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("em_obras.html", pesquisas=pesquisas)

@app.route("/denuncia")
def denuncia():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    return render_template("em_obras.html")

# =========================================
# ADMINISTRAÇÃO ADAPTADA COM SEGURANÇA
# =========================================
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
            
            cursor.execute("SELECT COUNT(*) FROM empresa")
            total_reg = cursor.fetchone()['count']
            
            # Mapeamento alias explicito para manter compatibilidade absoluta com os campos legados do template
            cursor.execute("""
                SELECT e.cnpj AS cnpj_base, e.nome AS nome_fantasia, '' AS ddd1, t.numero AS telefone1, 'N/A' AS uf 
                FROM empresa e
                LEFT JOIN telefone t ON e.id = t.empresa_id AND t.principal = TRUE
                ORDER BY e.nome ASC 
                LIMIT %s OFFSET %s
            """, (por_pagina, offset))
            
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
            # Reconstrução relacional para simular o dicionário plano esperado na tela de detalhes
            cursor.execute("""
                SELECT e.nome AS nome_fantasia, e.cnpj AS cnpj_base, '' AS ddd1, t.numero AS telefone1, 'N/A' AS uf, e.verificada
                FROM empresa e
                LEFT JOIN telefone t ON e.id = t.empresa_id AND t.principal = TRUE
                WHERE e.cnpj = %s 
                LIMIT 1
            """, (str(cnpj_base),))
            empresa = cursor.fetchone()
            return render_template("detalhes_empresa.html", empresa=empresa)
        except Exception as e:
            return str(e), 500

@app.route("/database_view", methods=["GET", "POST"])
def database_view():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    mensagem = None

    with conectar() as conn:
        if conn is None: return "Erro ao conectar ao banco de dados.", 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # PROCESSAMENTO DO FORMULÁRIO DE CADASTRO CONTIDO NO TEMPLATE
            if request.method == "POST":
                nome = request.form.get("nome", "").strip()
                telefone = request.form.get("telefone", "").strip()
                telefone_limpo = limpar_telefone(telefone)
                
                # Insere dados de maneira atômica respeitando restrições relacionais
                cursor.execute("INSERT INTO empresa (nome, cnpj, verificada) VALUES (%s, %s, TRUE) RETURNING id", (nome, telefone_limpo[:14] if telefone_limpo else "00000000000000"))
                nova_emp_id = cursor.fetchone()['id']
                
                if telefone_limpo:
                    cursor.execute("INSERT INTO telefone (numero, empresa_id, tipo, suspeito, principal) VALUES (%s, %s, 'oficial', FALSE, TRUE)", (telefone_limpo, nova_emp_id))
                
                # Grava no histórico administrativo
                cursor.execute("SELECT id FROM usuario LIMIT 1")
                u_row = cursor.fetchone()
                uid = u_row['id'] if u_row else 1
                cursor.execute("INSERT INTO historico_acao (usuario_id, acao, descricao, ip, realizado_em) VALUES (%s, 'cadastrou_empresa', %s, %s, NOW())", (uid, f"Empresa {nome} criada via painel.", request.remote_addr))
                
                conn.commit()
                mensagem = "Empresa e Telefone Oficial salvos com sucesso!"

            # CARREGAMENTO DA VIEW
            cursor.execute("""
                SELECT e.cnpj AS cnpj_base, e.nome AS nome_fantasia, '' AS ddd1, t.numero AS telefone1, 'N/A' AS uf 
                FROM empresa e
                LEFT JOIN telefone t ON e.id = t.empresa_id AND t.principal = TRUE
                WHERE e.nome IS NOT NULL AND e.nome != ''
                LIMIT 100
            """)
            registros = cursor.fetchall()
            return render_template("database_view.html", registros=registros, mensagem=mensagem)
        except Exception as e:
            if conn: conn.rollback()
            return f"Erro na operação: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
