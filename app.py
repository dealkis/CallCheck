from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os
import re
import unicodedata

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
    
    num = "".join(filter(str.isdigit, num))
    ddd = "".join(filter(str.isdigit, ddd))
    
    if ddd == "55" and len(num) >= 2:
        ddd = num[:2]
        num = num[2:]
        
    if len(num) == 9:
        return f"+55 ({ddd}) {num[0]} {num[1:5]}-{num[5:]}"
    elif len(num) == 8:
        return f"+55 ({ddd}) {num[0:4]}-{num[4:]}"
    else:
        return f"+55 ({ddd}) {num}"

def formatar_numero_completo(numero):
    if not numero: return "Não informado"
    limpo = limpar_telefone(numero)
    
    if limpo.startswith('0800') or len(limpo) < 10:
        return numero
    else:
        return formatar_telefone(limpo[:2], limpo[2:])

def normalizar_nome(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8').lower()
    texto = re.sub(r'[^a-z0-9\s]', '', texto)
    texto = texto.replace(' sa ', ' ').replace(' ltda ', ' ').replace(' s a ', ' ')
    if texto.endswith(' sa'): texto = texto[:-3]
    if texto.endswith(' s a'): texto = texto[:-4]
    if texto.endswith(' ltda'): texto = texto[:-5]
    return texto.strip()

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
            
            # Movido para cima para ser usado no PASSO 1 também (evita falha na verificação de denúncia)
            tel_sem_55 = telefone_limpo[2:] if telefone_limpo.startswith('55') else telefone_limpo

            # ==============================================================
            # PASSO 1: VERIFICAÇÃO DE DENÚNCIAS (PRIORIDADE MÁXIMA PARA BUSCA POR TEL)
            # ==============================================================
            if telefone_limpo:
                try:
                    # Agora verifica o número com e sem o 55
                    cursor.execute("""
                        SELECT d.tipo, d.descricao 
                        FROM denuncia d
                        JOIN telefone t ON d.telefone_id = t.id
                        WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') IN (%s, %s)
                        LIMIT 1
                    """, (telefone_limpo, tel_sem_55))
                    denuncia = cursor.fetchone()
                    if denuncia:
                        desc = denuncia.get('descricao')
                        if not desc:
                            desc = denuncia.get('tipo', 'Atividades suspeitas')
                            
                        return {
                            "empresa": nome or "Número Desconhecido",
                            "telefone": formatar_numero_completo(telefone),
                            "status": "RISCO",
                            "uf": uf or "",
                            "mensagem": f"ALERTA: Este número possui denúncias registradas! Motivo: {desc}."
                        }
                except Exception as e:
                    print("Aviso: Falha ao consultar denúncias.", e)


            # ==============================================================
            # CENÁRIO 1: BUSCA POR NOME + TELEFONE
            # ==============================================================
            if nome and telefone_limpo:
                cursor.execute("""
                    SELECT empresa_nome, numero, verificada
                    FROM (
                        SELECT e.nome AS empresa_nome, t.numero, e.verificada
                        FROM telefone t
                        LEFT JOIN empresa e ON t.empresa_id = e.id
                        WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') IN (%s, %s)
                        
                        UNION ALL
                        
                        SELECT er.nome AS empresa_nome, CAST(tr.telefone1 AS VARCHAR) AS numero, false AS verificada
                        FROM telefone_receita tr
                        LEFT JOIN empresa_receita er ON er.cnpj_basico = tr.cnpj_basico
                        WHERE tr.telefone1 IS NOT NULL AND REGEXP_REPLACE(tr.telefone1, '\D', '', 'g') IN (%s, %s)
                        
                        UNION ALL
                        
                        SELECT er.nome AS empresa_nome, CAST(tr.telefone2 AS VARCHAR) AS numero, false AS verificada
                        FROM telefone_receita tr
                        LEFT JOIN empresa_receita er ON er.cnpj_basico = tr.cnpj_basico
                        WHERE tr.telefone2 IS NOT NULL AND REGEXP_REPLACE(tr.telefone2, '\D', '', 'g') IN (%s, %s)
                    ) sub
                    LIMIT 1
                """, (telefone_limpo, tel_sem_55, telefone_limpo, tel_sem_55, telefone_limpo, tel_sem_55))
                
                resultado = cursor.fetchone()

                if resultado:
                    nome_banco_norm = normalizar_nome(resultado["empresa_nome"])
                    nome_input_norm = normalizar_nome(nome)

                    if nome_input_norm in nome_banco_norm or nome_banco_norm in nome_input_norm:
                        mensagem_final = "Número verificado e seguro!" if resultado["verificada"] else "Verificado pela base da Receita Federal."
                        return {
                            "empresa": resultado["empresa_nome"],
                            "telefone": formatar_numero_completo(resultado["numero"]),
                            "status": "OFICIAL",
                            "uf": uf or "",
                            "mensagem": mensagem_final
                        }
                    else:
                        return {
                            "empresa": nome,
                            "telefone": formatar_numero_completo(telefone),
                            "status": "NAO_OFICIAL",
                            "mensagem": f"ALERTA: Este número pertence a OUTRA empresa ({resultado['empresa_nome']})."
                        }
                else:
                    return {
                        "empresa": nome,
                        "telefone": formatar_numero_completo(telefone),
                        "status": "NAO_OFICIAL",
                        "mensagem": "Número não consta como vinculado a esta empresa."
                    }

            # ==============================================================
            # CENÁRIO 2: BUSCA APENAS POR TELEFONE
            # ==============================================================
            elif telefone_limpo and not nome:
                cursor.execute("""
                    SELECT empresa_nome, numero, verificada
                    FROM (
                        SELECT e.nome AS empresa_nome, t.numero, e.verificada
                        FROM telefone t
                        LEFT JOIN empresa e ON t.empresa_id = e.id
                        WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') IN (%s, %s)
                        
                        UNION ALL
                        
                        SELECT er.nome AS empresa_nome, CAST(tr.telefone1 AS VARCHAR) AS numero, false AS verificada
                        FROM telefone_receita tr
                        LEFT JOIN empresa_receita er ON er.cnpj_basico = tr.cnpj_basico
                        WHERE tr.telefone1 IS NOT NULL AND REGEXP_REPLACE(tr.telefone1, '\D', '', 'g') IN (%s, %s)
                        
                        UNION ALL
                        
                        SELECT er.nome AS empresa_nome, CAST(tr.telefone2 AS VARCHAR) AS numero, false AS verificada
                        FROM telefone_receita tr
                        LEFT JOIN empresa_receita er ON er.cnpj_basico = tr.cnpj_basico
                        WHERE tr.telefone2 IS NOT NULL AND REGEXP_REPLACE(tr.telefone2, '\D', '', 'g') IN (%s, %s)
                    ) sub
                    LIMIT 1
                """, (telefone_limpo, tel_sem_55, telefone_limpo, tel_sem_55, telefone_limpo, tel_sem_55))
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
                return {"empresa": None, "telefone": formatar_numero_completo(telefone), "status": "NAO_ENCONTRADO", "mensagem": "Telefone não encontrado."}

            # ==============================================================
            # CENÁRIO 3: BUSCA APENAS POR NOME
            # ==============================================================
            elif nome:
                por_pagina = 10
                offset = (pagina - 1) * por_pagina
                termo_busca_lista = f"%{nome}%" 
                
                cursor.execute("""
                    SELECT id, nome, verificada, 'base_empresa' AS origem, CAST(NULL AS VARCHAR) AS tel1, CAST(NULL AS VARCHAR) AS tel2
                    FROM empresa
                    WHERE nome ILIKE %s
                    
                    UNION ALL
                    
                    SELECT empresa_receita.id, empresa_receita.nome, false AS verificada, 'receita' AS origem, 
                           CAST(telefone_receita.telefone1 AS VARCHAR) AS tel1, 
                           CAST(telefone_receita.telefone2 AS VARCHAR) AS tel2
                    FROM empresa_receita
                    LEFT JOIN telefone_receita ON telefone_receita.cnpj_basico = empresa_receita.cnpj_basico
                    WHERE empresa_receita.nome ILIKE %s 
                    
                    ORDER BY nome ASC 
                    LIMIT %s OFFSET %s
                """, (termo_busca_lista, termo_busca_lista, por_pagina + 1, offset))
                
                empresas = cursor.fetchall()
                tem_proxima = len(empresas) > por_pagina
                
                lista_resultados = []
                for emp in empresas[:por_pagina]:
                    telefones = []
                    denuncia_msg = None 
                    
                    if emp['origem'] == 'base_empresa':
                        cursor.execute("""
                            SELECT t.numero, d.tipo, d.descricao 
                            FROM telefone t
                            LEFT JOIN denuncia d ON d.telefone_id = t.id
                            WHERE t.empresa_id = %s
                        """, (emp['id'],))
                        
                        for row in cursor.fetchall():
                            if row['numero']:
                                telefones.append(formatar_numero_completo(row['numero']))
                            if row['tipo'] is not None and not denuncia_msg:
                                desc = row['descricao'] if row['descricao'] else row['tipo']
                                denuncia_msg = f"Motivo: {desc}"
                    else:
                        if emp.get('tel1'): telefones.append(formatar_numero_completo(emp['tel1']))
                        if emp.get('tel2'): telefones.append(formatar_numero_completo(emp['tel2']))
                    
                    lista_resultados.append({
                        "empresa": emp["nome"], 
                        "telefones": telefones, 
                        "uf": uf or "",
                        "denuncias": denuncia_msg 
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
            print("Erro detalhado no banco de dados:", str(e))
            return {"status": "ERRO", "mensagem": "Falha na comunicação com o banco de dados."}


# =========================================================================
# ROTA EXCLUSIVA PARA ATENDER O FRONTEND EM REACT
# =========================================================================
@app.route("/api/validar", methods=["POST"])
def api_validar_telefone():
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "ERRO", "mensagem": "Nenhum dado enviado"}), 400
        
    nome_bruto = dados.get("empresa") or dados.get("nome") or ""
    nome = str(nome_bruto).strip()
    
    telefone_bruto = dados.get("telefone") or ""
    telefone = str(telefone_bruto).strip()
    
    uf_bruto = dados.get("uf") or ""
    uf = str(uf_bruto).strip()
    
    pagina = dados.get("pagina", 1)
    if not isinstance(pagina, int):
        pagina = 1

    resposta_db = verificar_empresa(nome, telefone, pagina, uf)
    
    # =====================================================
    # SE FOR UMA LISTA (BUSCA POR NOME)
    # =====================================================
    if resposta_db.get("status") == "LISTA":
        resultados = resposta_db.get("resultados", [])
        if resultados:
            dados_adaptados = []
            tem_denuncia_na_lista = False
            
            for reg in resultados:
                lista_tels = reg.get("telefones", [])
                tel_exibir = lista_tels[0] if lista_tels else "Não informado"
                denuncia_item = reg.get("denuncias")
                
                if denuncia_item:
                    tem_denuncia_na_lista = True
                    
                dados_adaptados.append({
                    "empresa": reg.get("empresa"),
                    "telefone": tel_exibir,
                    "status": "RISCO" if denuncia_item else "ENCONTRADO",
                    "denuncias": denuncia_item
                })
                
            status_global = "RISCO" if tem_denuncia_na_lista else "ENCONTRADO"
            msg_global = "⚠️ Atenção: Encontramos registros com alertas vinculados a esta empresa!" if tem_denuncia_na_lista else f"✅ {len(dados_adaptados)} registros encontrados!"
            
            return jsonify({
                "status": status_global, 
                "mensagem": msg_global,
                "dados": dados_adaptados,
                "pagina_atual": resposta_db.get("pagina_atual", 1),
                "tem_proxima": resposta_db.get("tem_proxima", False)
            })
        else:
            return jsonify({
                "status": "invalid", 
                "dados": {
                    "status": "NAO_ENCONTRADO", 
                    "mensagem": f"❌ Nenhuma empresa encontrada com o termo '{nome}'."
                }
            })
    
    if resposta_db.get("status") in ["OFICIAL", "ENCONTRADO"]:
        return jsonify({"status": "valid", "dados": resposta_db})
    elif resposta_db.get("status") == "RISCO":
        return jsonify({"status": "invalid", "dados": resposta_db})
    else:
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


@app.route("/api/denuncias", methods=["POST"])
def api_registrar_denuncia():
    dados = request.get_json()
    
    if not dados:
        return jsonify({"status": "ERRO", "mensagem": "Nenhum dado enviado do formulário."}), 400
        
    telefone_limpo = dados.get("telefone", "").strip()
    tipo_denuncia = dados.get("tipo", "").strip()
    descricao = dados.get("descricao", "").strip()
    
    if not telefone_limpo:
        return jsonify({"status": "ERRO", "mensagem": "O número de telefone não foi informado ou é inválido."}), 400
        
    if not tipo_denuncia:
        return jsonify({"status": "ERRO", "mensagem": "Selecione o motivo da denúncia (Golpe, Spam, etc)."}), 400

    # Blindagem para associar corretamente independentemente de como o front manda
    tel_sem_55 = telefone_limpo[2:] if telefone_limpo.startswith('55') else telefone_limpo

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor()
            
            # Verifica com e sem o 55 para achar o telefone base
            cursor.execute("""
                SELECT id FROM telefone 
                WHERE REGEXP_REPLACE(numero, '\D', '', 'g') IN (%s, %s)
                LIMIT 1
            """, (telefone_limpo, tel_sem_55))
            tel_row = cursor.fetchone()
            
            if tel_row:
                telefone_id = tel_row[0]
            else:
                cursor.execute("""
                    INSERT INTO telefone (numero, tipo, suspeito, principal) 
                    VALUES (%s, 'desconhecido', true, false) 
                    RETURNING id
                """, (telefone_limpo,)) 
                telefone_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO denuncia (telefone_id, tipo, descricao) 
                VALUES (%s, %s, %s)
            """, (telefone_id, tipo_denuncia, descricao))
            
            conn.commit()
            return jsonify({"status": "SUCESSO", "mensagem": "✅ Denúncia registrada com sucesso!"}), 200
            
        except psycopg2.errors.InvalidTextRepresentation as e:
            if conn: conn.rollback()
            print("Erro de ENUM detectado:", str(e))
            return jsonify({
                "status": "ERRO", 
                "mensagem": f"O banco recusou o valor enviado. Verifique se os ENUMs estão certos no Postgres. Erro: {str(e)}"
            }), 400
            
        except psycopg2.IntegrityError as e:
            if conn: conn.rollback()
            print("Erro de restrição/duplicidade:", str(e))
            return jsonify({
                "status": "ERRO", 
                "mensagem": "Este número já possui uma denúncia registrada por você ou viola regras de integridade."
            }), 409
            
        except Exception as e:
            if conn: conn.rollback()
            print("Erro geral no salvamento da denúncia:", str(e))
            return jsonify({
                "status": "ERRO", 
                "mensagem": f"Falha interna no banco de dados: {str(e)}"
            }), 500


@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/contato")
def contato():
    return render_template("contato.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_logado" in session: return redirect(url_for('perfil_usuario'))
    erro = None
    if request.method == "POST":
        usuario_input = request.form.get("usuario") 
        senha = request.form.get("senha")
        
        with conectar() as conn:
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
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

@app.route("/historico")
def historico():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    pesquisas = session.get('pesquisas_recentes', [])
    return render_template("em_obras.html", pesquisas=pesquisas)

@app.route("/denuncia")
def denuncia():
    if "usuario_logado" not in session: return redirect(url_for('login'))
    return render_template("em_obras.html")

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
            
            cursor.execute("SELECT COUNT(*) FROM empresa WHERE nome IS NOT NULL AND nome != ''")
            total_reg = cursor.fetchone()['count']
            
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
            
            cursor.execute("""
                SELECT id, nome AS nome_fantasia, cnpj, verificada 
                FROM empresa 
                WHERE cnpj = %s LIMIT 1
            """, (str(cnpj_base),))
            empresa = cursor.fetchone()
            
            if empresa:
                cursor.execute("""
                    SELECT numero, tipo, suspeito, principal 
                    FROM telefone 
                    WHERE empresa_id = %s
                """, (empresa['id'],))
                telefones = cursor.fetchall()
                
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
 _____  ______     _     _       __ __ ______ ______ 
|  __ \|  ____|   /\    | |     | |/ /|_   _|/ ____|
| |  | | |__     /  \   | |     | ' /   | | | (___  
| |  | |  __|   / /\ \  | |     |  <    | |  \___ \ 
| |__| | |____ / ____ \ | |____| . \  _| |_ ____) |
|_____/|______|/_/    \_\______|_|\_\|_____|_____/

'''
