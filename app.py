# =========================
# VERIFICAÇÃO (ATUALIZADA PARA MÚLTIPLOS RESULTADOS POR NOME)
# =========================
def verificar_empresa(nome=None, telefone=None):
    conn = conectar()
    if conn is None:
        return {"status": "ERRO", "mensagem": "Erro ao conectar ao banco"}

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        telefone_limpo = limpar_telefone(telefone)

        # 1. BUSCA POR TELEFONE (Mantém a lógica original de resultado único)
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

        # 2. BUSCA POR NOME (Alterada para retornar lista de empresas)
        if nome:
            # Se houver telefone junto, primeiro verificamos se o telefone bate com a empresa sugerida
            # mas para buscar pelo nome "Bar", queremos a lista:
            cursor.execute("""
                SELECT nome_fantasia, ddd1, telefone1, ddd2, telefone2, uf 
                FROM estabelecimentos_raw 
                WHERE nome_fantasia ILIKE %s 
                ORDER BY nome_fantasia ASC
                LIMIT 30
            """, (f"%{nome}%",))
            
            empresas_encontradas = cursor.fetchall()

            if not empresas_encontradas:
                conn.close()
                return {
                    "empresa": nome,
                    "status": "NAO_CADASTRADA",
                    "mensagem": "Empresa não encontrada."
                }

            # Caso tenha nome E telefone, mantemos sua lógica de validar se o número é OFICIAL
            if telefone:
                # Pegamos a primeira correspondência para validar o número específico digitado
                empresa = empresas_encontradas[0]
                telefones_brutos = []
                if empresa['ddd1'] and empresa['telefone1']:
                    telefones_brutos.append(empresa['ddd1'] + empresa['telefone1'])
                if empresa['ddd2'] and empresa['telefone2']:
                    telefones_brutos.append(empresa['ddd2'] + empresa['telefone2'])

                resposta = {
                    "empresa": empresa["nome_fantasia"],
                    "telefones": [formatar_telefone(empresa['ddd1'], empresa['telefone1']) if empresa['ddd1'] else ""],
                    "telefone": telefone,
                    "uf": empresa["uf"]
                }
                
                if telefone_limpo in telefones_brutos:
                    resposta.update({"status": "OFICIAL", "mensagem": "Número verificado e seguro."})
                else:
                    resposta.update({"status": "NAO_OFICIAL", "mensagem": "Número não consta como oficial."})
                
                conn.close()
                return resposta

            # CASO SEJA APENAS BUSCA POR NOME: Retorna a lista completa
            lista_resultados = []
            for emp in empresas_encontradas:
                tels = []
                if emp['ddd1'] and emp['telefone1']:
                    tels.append(formatar_telefone(emp['ddd1'], emp['telefone1']))
                if emp['ddd2'] and emp['telefone2']:
                    tels.append(formatar_telefone(emp['ddd2'], emp['telefone2']))
                
                lista_resultados.append({
                    "empresa": emp["nome_fantasia"],
                    "telefones": tels,
                    "uf": emp["uf"]
                })

            conn.close()
            return {
                "status": "LISTA",
                "resultados": lista_resultados,
                "mensagem": f"Foram encontradas {len(lista_resultados)} empresas correspondentes.",
                "nome_buscado": nome
            }

        return {"status": "ERRO", "mensagem": "Informe nome ou telefone."}

    except Exception as e:
        if conn: conn.close()
        return {"status": "ERRO", "mensagem": str(e)}
