from flask import Flask, render_template, request, redirect, url_for, session, jsonify # <-- Injetado jsonify aqui
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "chave_segura_acex")
CORS(app, resources={r"/api/*": {"origins": "https://callcheck-1.onrender.com"}})

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
    
    # Limpa tudo e garante que ddd e num sejam apenas dígitos
    num = "".join(filter(str.isdigit, num))
    ddd = "".join(filter(str.isdigit, ddd))
    
    # SE O DDD FOR "55", IGNORAMOS E PEGAMOS O PRÓXIMO COMO DDD REAL
    if ddd == "55" and len(num) >= 2:
        ddd = num[:2]
        num = num[2:]
        
    # Formatação final: +55 (DDD) XXXX-XXXX
    if len(num) == 9:
        return f"+55 ({ddd}) {num[0]} {num[1:5]}-{num[5:]}"
    elif len(num) == 8:
        return f"+55 ({ddd}) {num[0:4]}-{num[4:]}"
    else:
        return f"+55 ({ddd}) {num}"

def formatar_numero_completo(numero):
    """Aplica a formatação +55 (DDD) XXXX-XXXX"""
    if not numero: return "Não informado"
    limpo = limpar_telefone(numero)
    
    # Se for um número tipo 0800 ou muito curto, retorna sem o +55
    if limpo.startswith('0800') or len(limpo) < 10:
        return numero
    else:
        # Pega os 2 primeiros dígitos como DDD e o restante como número
        return formatar_telefone(limpo[:2], limpo[2:])

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
                    cursor.execute("""
                        SELECT d.descricao 
                        FROM denuncia d
                        JOIN telefone t ON d.telefone_id = t.id
                        WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') = %s 
                        LIMIT 1
                    """, (telefone_limpo,))
                    denuncia = cursor.fetchone()
                    if denuncia:
                        return {
                            "empresa": nome or "Número Desconhecido",
                            "telefone": telefone,
                            "status": "RISCO",
                            "uf": uf or "",
                            "mensagem": f"ALERTA: Este número possui denúncias registradas! Motivo: {denuncia.get('descricao', 'Atividades suspeitas')}."
                        }
                except Exception as e:
                    print("Aviso: Tabela de denúncias ou colunas podem estar indisponíveis.", e)

            # CENÁRIO 1: BUSCA POR NOME E TELEFONE JUNTOS
            if nome and telefone_limpo:
                termo_busca = f"%{nome}%"
                query = """
                    SELECT e.nome AS empresa_nome, t.numero, e.verificada
                    FROM (
                        SELECT id, nome, verificada, 'base_empresa' AS origem FROM empresa
                        UNION ALL
                        SELECT id, nome, false AS verificada, 'receita' AS origem FROM empresa_receita
                    ) e
                    JOIN telefone t ON t.empresa_id = e.id AND e.origem = 'base_empresa'
                    WHERE e.nome ILIKE %s 
                      AND REGEXP_REPLACE(t.numero, '\D', '', 'g') = %s
                    LIMIT 1
                """
                cursor.execute(query, (termo_busca, telefone_limpo))
                resultado = cursor.fetchone()

                if resultado:
                    return {
                        "empresa": resultado["empresa_nome"],
                        "telefone": formatar_numero_completo(resultado["numero"]),
                        "status": "OFICIAL" if resultado["verificada"] else "NAO_VERIFICADA",
                        "uf": uf or "",
                        "mensagem": "Número verificado e seguro!" if resultado["verificada"] else "Número encontrado, mas a empresa não possui selo de verificação."
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
                    SELECT e.nome AS empresa_nome, t.numero, e.verificada
                    FROM telefone t
                    LEFT JOIN empresa e ON t.empresa_id = e.id
                    WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') = %s
                    LIMIT 1
                """, (telefone_limpo,))
                resultado = cursor.fetchone()

                if resultado:
                    empresa_nome = resultado["empresa_nome"] or "Empresa Registrada"
                    return {
                        "empresa": empresa_nome,
                        "telefone": formatar_numero_completo(resultado["numero"]),
                        "status": "ENCONTRADO",
                        "uf": uf or "",
                        "mensagem": "Telefone vinculado a uma empresa."
                    }
                return {"empresa": None, "telefone": telefone, "status": "NAO_ENCONTRADO", "mensagem": "Telefone não encontrado."}

            # CENÁRIO 3: BUSCA APENAS POR NOME (PAGINADA)
            elif nome:
                por_pagina = 10
                offset = (pagina - 1) * por_pagina
                termo_busca = f"%{nome}%"
                
                cursor.execute("""
                    SELECT id, nome, verificada, 'base_empresa' AS origem, CAST(NULL AS VARCHAR) AS telefone
                    FROM empresa
                    WHERE nome ILIKE %s
                    
                    UNION ALL
                    
                    SELECT id, nome, false AS verificada, 'receita' AS origem, CAST(telefone_receitas AS VARCHAR) AS telefone
                    FROM empresa_receita
                    WHERE nome ILIKE %s OR telefone_receita ILIKE %s
                    
                    ORDER BY nome ASC 
                    LIMIT %s OFFSET %s
                """, (termo_busca, termo_busca, termo_busca, por_pagina + 1, offset))
                
                empresas = cursor.fetchall()
                tem_proxima = len(empresas) > por_pagina
                
                lista_resultados = []
                for emp in empresas[:por_pagina]:
                    if emp['origem'] == 'base_empresa':
                        cursor.execute("SELECT numero FROM telefone WHERE empresa_id = %s", (emp['id'],))
                        telefones = [formatar_numero_completo(row['numero']) for row in cursor.fetchall()]
                    else:
                        telefones = [formatar_numero_completo(emp['telefone'])] if emp.get('telefone') else []
                    
                    lista_resultados.append({
                        "empresa": emp["nome"], 
                        "telefones": telefones, 
                        "uf": uf or ""
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

# =========================================================================
# NOVA ROTA EXCLUSIVA PARA ATENDER O FRONTEND EM REACT (NÃO MEXE NAS OUTRAS)
# =========================================================================
@app.route("/api/validar", methods=["POST"])
def api_validar_telefone():
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "ERRO", "mensagem": "Nenhum dado enviado"}), 400
        
    # Proteção ativa para garantir que None/null vire string vazia antes do .strip()
    nome_bruto = dados.get("empresa") or dados.get("nome") or ""
    nome = str(nome_bruto).strip()
    
    telefone_bruto = dados.get("telefone") or ""
    telefone = str(telefone_bruto).strip()
    
    uf_bruto = dados.get("uf") or ""
    uf = str(uf_bruto).strip()
    
    pagina = dados.get("pagina", 1)
    if not isinstance(pagina, int):
        pagina = 1

    # Executa exatamente a sua função interna de banco de dados
    resposta_db = verificar_empresa(nome, telefone, pagina, uf)
    
    # Se a busca foi por texto e gerou uma estrutura de LISTA, tratamos para o card único do front-end
    if resposta_db.get("status") == "LISTA":
        resultados = resposta_db.get("resultados", [])
        if resultados:
            primeiro_registro = resultados[0]
            lista_tels = primeiro_registro.get("telefones", [])
            tel_exibir = lista_tels[0] if lista_tels else "Não informado"
            
            # Reconstrói os dados de forma compatível com a CallCheckPage.jsx
            dados_adaptados = {
                "status": "ENCONTRADO",
                "empresa": primeiro_registro.get("empresa"),
                "telefone": tel_exibir,
                "mensagem": f"✅ Registro encontrado com sucesso!"
            }
            return jsonify({"status": "valid", "dados": dados_adaptados})
        else:
            return jsonify({
                "status": "invalid", 
                "dados": {
                    "status": "NAO_ENCONTRADO", 
                    "mensagem": f"❌ Nenhuma empresa encontrada com o termo '{nome}'."
                }
            })
    
    # Mapeia as suas respostas estruturadas para o formato simples esperado pela CallCheckPage.jsx
    if resposta_db.get("status") in ["OFICIAL", "ENCONTRADO"]:
        return jsonify({"status": "valid", "dados": resposta_db})
    elif resposta_db.get("status") == "RISCO":
        return jsonify({"status": "invalid", "dados": resposta_db})
    else:
        # Casos NAO_OFICIAL, NAO_ENCONTRADO ou erros internos
        return jsonify({"status": "invalid", "dados": resposta_db})

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
                    cursor = conn.cursor() # Usamos o cursor padrão aqui
                    
                    # 1. Verifica se telefone existe na base 'telefone'
                    cursor.execute("""
                        SELECT id FROM telefone 
                        WHERE REGEXP_REPLACE(numero, '\D', '', 'g') = %s 
                        LIMIT 1
                    """, (telefone_limpo,))
                    tel_row = cursor.fetchone()
                    
                    if tel_row:
                        telefone_id = tel_row[0]
                    else:
                        # 2. Insere telefone se não existir (desconhecido, como suspeito)
                        cursor.execute("""
                            INSERT INTO telefone (numero, tipo, suspeito, principal) 
                            VALUES (%s, 'desconhecido', true, false) 
                            RETURNING id
                        """, (telefone,)) 
                        telefone_id = cursor.fetchone()[0]
                    
                    # 3. Insere a nova denúncia usando a chave estrangeira
                    cursor.execute("""
                        INSERT INTO denuncia (telefone_id, tipo, descricao) 
                        VALUES (%s, 'outros', %s)
                    """, (telefone_id, motivo))
                    
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
        usuario_input = request.form.get("usuario") # Capturamos do mesmo campo name="usuario" no template
        senha = request.form.get("senha")
        
        with conectar() as conn:
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    # Verifica login real buscando na nova tabela "usuario"
                    cursor.execute("""
                        SELECT id, nome, email 
                        FROM usuario 
                        WHERE email = %s AND senha = %s 
                        LIMIT 1
                    """, (usuario_input, senha))
                    user = cursor.fetchone()
                    
                    if user:
                        session["usuario_logado"] = user["nome"]
                        session["usuario_id"] = user["id"]
                        return redirect(url_for('perfil_usuario'))
                    else:
                        erro = "Usuário ou senha incorretos."
                except Exception as e:
                    print("Erro no DB durante o login:", e)
                    erro = "Ocorreu um erro ao processar o login."
            else:
                erro = "Erro de conexão ao banco de dados."

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
            
            # Conta o total para paginação usando a tabela 'empresa'
            cursor.execute("SELECT COUNT(*) FROM empresa WHERE nome IS NOT NULL AND nome != ''")
            total_reg = cursor.fetchone()['count']
            
            # Mapamento no SQL com apelidos para renderizar corretamente no "empresas.html"
            query = """
                SELECT 
                    e.cnpj AS cnpj_base, 
                    e.nome AS nome_fantasia, 
                    '' AS ddd1, 
                    t.numero AS telefone1, 
                    '' AS uf 
                FROM empresa e
                LEFT JOIN telefone t ON t.empresa_id = e.id AND t.principal = true
                WHERE e.nome IS NOT NULL AND e.nome != ''
                ORDER BY e.nome ASC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (por_pagina, offset))
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
            
            # Busca a empresa pelo CNPJ, forçando chave similar para compatibilidade de template
            cursor.execute("""
                SELECT id, nome AS nome_fantasia, cnpj, verificada 
                FROM empresa 
                WHERE cnpj = %s LIMIT 1
            """, (str(cnpj_base),))
            empresa = cursor.fetchone()
            
            if empresa:
                # Busca telefones vinculados a esta empresa
                cursor.execute("""
                    SELECT numero, tipo, suspeito, principal 
                    FROM telefone 
                    WHERE empresa_id = %s
                """, (empresa['id'],))
                telefones = cursor.fetchall()
                
                # Injeta dados de telefones dinamicamente no dict pra o loop for renderizar
                for idx, t in enumerate(telefones):
                    empresa[f"telefone_{idx+1}"] = t['numero']
                    empresa[f"tipo_{idx+1}"] = t['tipo']
                    empresa[f"suspeito_{idx+1}"] = "Sim" if t['suspeito'] else "Não"

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
            # Replicado o mapeamento "AS" para simular o modelo flat anterior perfeitamente
            cursor.execute("""
                SELECT 
                    e.cnpj AS cnpj_base, 
                    e.nome AS nome_fantasia, 
                    '' AS ddd1, 
                    t.numero AS telefone1, 
                    '' AS uf 
                FROM empresa e
                LEFT JOIN telefone t ON t.empresa_id = e.id AND t.principal = true
                WHERE e.nome IS NOT NULL AND e.nome != ''
                ORDER BY e.nome ASC
                LIMIT 100
            """)
            registros = cursor.fetchall()
            return render_template("database_view.html", registros=registros)
        except Exception as e:
            return f"Erro na consulta: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

'''
 _____  ______     _     _      __ __ ______ ______ 
|  __ \|  ____|   /\    | |    | |/ /|_   _|/ ____|
| |  | | |__     /  \   | |    | ' /   | | | (___  
| |  | |  __|   / /\ \  | |    |  <    | |  \___ \ 
| |__| | |____ / ____ \ | |____| . \  _| |_ ____) |
|_____/|______|/_/    \_\______|_|\_\|_____|_____/

'''
