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

# =========================
# VERIFICAÇÃO (AJUSTADA PARA A NOVA TABELA)
# =========================
def verificar_empresa(nome=None, telefone=None):
    conn = conectar()

    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        telefone = limpar_telefone(telefone)

        # 1. BUSCA POR TELEFONE (Prioridade)
        if telefone and not nome:
            # Busca usando a lógica do índice que criamos: concatenando DDD + Telefone
            cursor.execute("""
                SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, email, uf
                FROM estabelecimentos_raw 
                WHERE (ddd1 || telefone1) = %s OR (ddd2 || telefone2) = %s
                LIMIT 1
            """, (telefone, telefone))
            
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                # Se não houver nome_fantasia, usamos o E-mail ou um aviso
                nome_exibir = resultado["nome_fantasia"] if resultado["nome_fantasia"] else "Empresa (Nome não disponível)"
                return {
                    "empresa": nome_exibir,
                    "telefone": telefone,
                    "status": "ENCONTRADO",
                    "uf": resultado["uf"],
                    "mensagem": f"Telefone vinculado a uma empresa em {resultado['uf']}."
                }
            else:
                return {
                    "empresa": None,
                    "telefone": telefone,
                    "status": "NAO_ENCONTRADO",
                    "mensagem": "Telefone não encontrado na base da Receita Federal."
                }

        # 2. BUSCA POR NOME
        if nome:
            # Busca pelo Nome Fantasia
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
                    "mensagem": "Empresa não encontrada na base atual."
                }

            # Coletamos os telefones disponíveis (tel1 e tel2)
            telefones = []
            if empresa['ddd1'] and empresa['telefone1']:
                telefones.append(empresa['ddd1'] + empresa['telefone1'])
            if empresa['ddd2'] and empresa['telefone2']:
                telefones.append(empresa['ddd2'] + empresa['telefone2'])

            resposta = {
                "empresa": empresa["nome_fantasia"],
                "telefones": telefones,
                "telefone": telefone if telefone else "Não informado",
                "uf": empresa["uf"]
            }

            # Caso: Só Nome
            if nome and not telefone:
                resposta.update({
                    "status": "CANAIS",
                    "mensagem": f"Canais oficiais encontrados para esta empresa ({empresa['uf']})."
                })
            
            # Caso: Nome + Telefone (Verificação)
            elif nome and telefone:
                if telefone in telefones:
                    resposta.update({
                        "status": "OFICIAL",
                        "mensagem": "Número verificado na base oficial da Receita Federal."
                    })
                else:
                    # Aqui você pode manter sua lógica de denúncia se a tabela 'denuncia' ainda existir
                    resposta.update({
                        "status": "NAO_OFICIAL",
                        "mensagem": "Este número não consta como telefone oficial desta empresa."
                    })
            
            conn.close()
            return resposta

        else:
            conn.close()
            return {"status": "ERRO", "mensagem": "Informe nome ou telefone."}

    except Exception as e:
        if conn:
            conn.close()
        return {"status": "ERRO", "mensagem": str(e)}

# =========================
# ROTAS PRINCIPAIS (MANTIDAS)
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

# ... (Restante das rotas de Login, Usuário, Admin permanecem IGUAIS)
# Nota: As rotas de ADMIN (add-empresa, etc) ainda tentam salvar na tabela antiga 'empresa'. 
# Como agora você usa a base da Receita, essas rotas de "adicionar manual" precisarão 
# ser migradas para a tabela 'estabelecimentos_raw' no futuro se você quiser continuar usando.

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
