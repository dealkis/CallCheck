from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
import os
import re
import unicodedata
import secrets
import hashlib
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

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
            
            tel_sem_55 = telefone_limpo[2:] if telefone_limpo.startswith('55') else telefone_limpo

            if telefone_limpo:
                try:
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
# ROTAS DA API
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

    tel_sem_55 = telefone_limpo[2:] if telefone_limpo.startswith('55') else telefone_limpo

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor()
            
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

# =========================================================================
# AUTENTICAÇÃO (LOGIN / LOGOUT) E ÁREA ADMINISTRATIVA
# =========================================================================
# Fluxo: /api/login devolve um token; o React envia esse token no header
# "Authorization: Bearer <token>" nas rotas /api/admin/*.
# Usamos token (e não cookie de sessão) porque front e API estão em domínios
# diferentes no Render. Só o SHA-256 do token é gravado na tabela "sessao".
SESSAO_HORAS = int(os.getenv("SESSAO_HORAS", "8"))
NIVEIS_ADMIN = ("admin",)  # para liberar moderadores: ("admin", "moderador")

# Hash falso usado para gastar o mesmo tempo quando o e-mail não existe
# (evita descobrir quais e-mails estão cadastrados pelo tempo de resposta).
HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-tempo")

def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _ip_cliente():
    # Atrás do proxy do Render, o IP real vem em X-Forwarded-For
    xff = request.headers.get("X-Forwarded-For", "")
    ip = xff.split(",")[0].strip() if xff else (request.remote_addr or "")
    return ip[:45]

def _senha_confere(hash_armazenado, senha):
    try:
        return check_password_hash(hash_armazenado, senha)
    except ValueError:
        return False

def registrar_acao(cursor, usuario_id, acao, descricao=None):
    """Grava em historico_acao usando o mesmo cursor (mesma transação)."""
    cursor.execute("""
        INSERT INTO historico_acao (usuario_id, acao, descricao, ip)
        VALUES (%s, %s, %s, %s)
    """, (usuario_id, acao, descricao, _ip_cliente()))

def _variantes_telefone(telefone):
    """'11 4979-3300' -> ('1149793300', '551149793300')."""
    limpo = limpar_telefone(telefone)
    if not limpo:
        return ()
    sem_55 = limpo[2:] if limpo.startswith("55") else limpo
    return tuple({sem_55, "55" + sem_55, limpo})

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"status": "ERRO", "mensagem": "Autenticação necessária."}), 401
        token = auth[7:].strip()

        usuario = None
        with conectar() as conn:
            if not conn:
                return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT u.id, u.nome, u.email, u.nivel, u.status
                    FROM sessao s
                    JOIN usuario u ON u.id = s.usuario_id
                    WHERE s.token = %s AND s.ativo = true AND s.expira_em > now()
                """, (_hash_token(token),))
                usuario = cursor.fetchone()
            except Exception as e:
                print("Erro ao validar sessão:", str(e))
                return jsonify({"status": "ERRO", "mensagem": "Falha ao validar a sessão."}), 500

        if not usuario or usuario["status"] != "ativo":
            return jsonify({"status": "ERRO", "mensagem": "Sessão inválida ou expirada."}), 401
        if usuario["nivel"] not in NIVEIS_ADMIN:
            return jsonify({"status": "ERRO", "mensagem": "Acesso restrito a administradores."}), 403

        g.usuario = usuario
        return f(*args, **kwargs)
    return wrapper


@app.route("/api/login", methods=["POST"])
def api_login():
    dados = request.get_json(silent=True) or {}
    email = str(dados.get("email") or "").strip().lower()
    senha = str(dados.get("senha") or "")

    if not email or not senha:
        return jsonify({"status": "ERRO", "mensagem": "Informe e-mail e senha."}), 400

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id, nome, email, senha_hash, nivel, status
                FROM usuario
                WHERE LOWER(email) = %s
            """, (email,))
            usuario = cursor.fetchone()

            senha_ok = _senha_confere(usuario["senha_hash"] if usuario else HASH_FALSO, senha)

            if not usuario or not senha_ok:
                return jsonify({"status": "ERRO", "mensagem": "E-mail ou senha inválidos."}), 401

            if usuario["status"] != "ativo":
                return jsonify({"status": "ERRO", "mensagem": "Esta conta está inativa ou foi banida."}), 403

            token = secrets.token_urlsafe(32)
            cursor.execute("""
                INSERT INTO sessao (usuario_id, token, ip, user_agent, expira_em)
                VALUES (%s, %s, %s, %s, now() + make_interval(hours => %s))
                RETURNING expira_em
            """, (usuario["id"], _hash_token(token), _ip_cliente(),
                  request.headers.get("User-Agent"), SESSAO_HORAS))
            expira_em = cursor.fetchone()["expira_em"]

            registrar_acao(cursor, usuario["id"], "login", "Login via API")
            conn.commit()

            return jsonify({
                "status": "SUCESSO",
                "mensagem": "Login realizado com sucesso.",
                "token": token,
                "expira_em": expira_em.isoformat(),
                "usuario": {
                    "id": usuario["id"],
                    "nome": usuario["nome"],
                    "email": usuario["email"],
                    "nivel": usuario["nivel"]
                }
            }), 200

        except Exception as e:
            if conn: conn.rollback()
            print("Erro no login:", str(e))
            return jsonify({"status": "ERRO", "mensagem": "Falha interna ao realizar o login."}), 500


@app.route("/api/logout", methods=["POST"])
def api_logout():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"status": "ERRO", "mensagem": "Autenticação necessária."}), 401
    token_hash = _hash_token(auth[7:].strip())

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessao SET ativo = false
                WHERE token = %s AND ativo = true
                RETURNING usuario_id
            """, (token_hash,))
            row = cursor.fetchone()
            if row:
                registrar_acao(cursor, row[0], "logout", "Logout via API")
            conn.commit()
            return jsonify({"status": "SUCESSO", "mensagem": "Sessão encerrada."}), 200
        except Exception as e:
            if conn: conn.rollback()
            print("Erro no logout:", str(e))
            return jsonify({"status": "ERRO", "mensagem": "Falha interna ao encerrar a sessão."}), 500


# -------------------------------------------------------------------------
# ADMIN: DENÚNCIAS
# -------------------------------------------------------------------------
def _desmarcar_suspeitos(cursor, telefone_ids):
    """Telefones que ficaram sem nenhuma denúncia deixam de ser 'suspeito'."""
    if not telefone_ids:
        return
    cursor.execute("""
        UPDATE telefone SET suspeito = false
        WHERE id = ANY(%s)
          AND NOT EXISTS (SELECT 1 FROM denuncia d WHERE d.telefone_id = telefone.id)
    """, (list(telefone_ids),))


@app.route("/api/admin/denuncias", methods=["GET"])
@admin_required
def api_admin_listar_denuncias():
    """Lista denúncias (opcionalmente de um número) para achar o id certo."""
    variantes = _variantes_telefone(request.args.get("telefone", ""))

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            filtro, params = "", []
            if variantes:
                filtro = r"WHERE REGEXP_REPLACE(t.numero, '\D', '', 'g') IN %s"
                params.append(variantes)

            cursor.execute(f"""
                SELECT d.id, t.numero AS telefone, d.tipo, d.descricao,
                       d.data_registro, d.usuario_id, e.nome AS empresa
                FROM denuncia d
                JOIN telefone t ON t.id = d.telefone_id
                LEFT JOIN empresa e ON e.id = t.empresa_id
                {filtro}
                ORDER BY d.data_registro DESC
                LIMIT 100
            """, params)

            denuncias = cursor.fetchall()
            for d in denuncias:
                d["data_registro"] = d["data_registro"].isoformat()
            return jsonify({"status": "SUCESSO", "total": len(denuncias), "denuncias": denuncias}), 200
        except Exception as e:
            print("Erro ao listar denúncias:", str(e))
            return jsonify({"status": "ERRO", "mensagem": "Falha ao listar denúncias."}), 500


@app.route("/api/admin/denuncias/<int:denuncia_id>", methods=["DELETE"])
@admin_required
def api_admin_deletar_denuncia(denuncia_id):
    """Remove UMA denúncia pelo id."""
    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM denuncia WHERE id = %s
                RETURNING telefone_id, tipo
            """, (denuncia_id,))
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                return jsonify({"status": "ERRO", "mensagem": "Denúncia não encontrada."}), 404

            telefone_id, tipo = row
            _desmarcar_suspeitos(cursor, [telefone_id])
            registrar_acao(cursor, g.usuario["id"], "removeu_denuncia",
                           f"Denúncia #{denuncia_id} ({tipo}) removida do telefone_id {telefone_id}")
            conn.commit()
            return jsonify({"status": "SUCESSO", "mensagem": f"Denúncia #{denuncia_id} removida."}), 200
        except Exception as e:
            if conn: conn.rollback()
            print("Erro ao deletar denúncia:", str(e))
            return jsonify({"status": "ERRO", "mensagem": "Falha interna ao remover a denúncia."}), 500


@app.route("/api/admin/denuncias", methods=["DELETE"])
@admin_required
def api_admin_deletar_denuncias_por_telefone():
    """Remove TODAS as denúncias de um número: DELETE /api/admin/denuncias?telefone=1149793300"""
    telefone = request.args.get("telefone", "")
    variantes = _variantes_telefone(telefone)

    # Trava de segurança: evita apagar denúncias por engano com um número curto/vazio
    if not variantes or len(limpar_telefone(telefone)) < 8:
        return jsonify({"status": "ERRO", "mensagem": "Informe um telefone válido (mín. 8 dígitos)."}), 400

    with conectar() as conn:
        if not conn:
            return jsonify({"status": "ERRO", "mensagem": "Erro de conexão com o banco de dados."}), 500
        try:
            cursor = conn.cursor()
            cursor.execute(r"""
                DELETE FROM denuncia
                WHERE telefone_id IN (
                    SELECT id FROM telefone
                    WHERE REGEXP_REPLACE(numero, '\D', '', 'g') IN %s
                )
                RETURNING id, telefone_id, tipo
            """, (variantes,))
            removidas = cursor.fetchall()
            if not removidas:
                conn.rollback()
                return jsonify({"status": "ERRO", "mensagem": "Nenhuma denúncia encontrada para este número."}), 404

            _desmarcar_suspeitos(cursor, {r[1] for r in removidas})
            ids = ", ".join(f"#{r[0]}" for r in removidas)
            registrar_acao(cursor, g.usuario["id"], "removeu_denuncia",
                           f"{len(removidas)} denúncia(s) removida(s) do número {limpar_telefone(telefone)}: {ids}")
            conn.commit()
            return jsonify({
                "status": "SUCESSO",
                "mensagem": f"{len(removidas)} denúncia(s) removida(s).",
                "removidas": [r[0] for r in removidas]
            }), 200
        except Exception as e:
            if conn: conn.rollback()
            print("Erro ao deletar denúncias por telefone:", str(e))
            return jsonify({"status": "ERRO", "mensagem": "Falha interna ao remover as denúncias."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
