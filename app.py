# --- Dentro do menu "📝 Montar Treino" ---

# 1. Primeiro, buscamos os exercícios que já foram adicionados para este aluno hoje
query_atuais = text("""
    SELECT f.id, e.nome 
    FROM fichas_treino f 
    JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
    WHERE f.usuario_id = :u AND f.treino_nome = :t
    ORDER BY f.id DESC LIMIT 5
""")
df_recentes = pd.read_sql(query_atuais, engine, params={"u": int(id_a) if 'id_a' in locals() else 0, "t": t_nome})

# 2. No formulário, adicionamos a opção de combinar
combinar_com = st.selectbox("Combinar com exercício anterior? (Bi-set)", 
                             ["Não"] + df_recentes['nome'].tolist())

if st.form_submit_button("✅ Adicionar à Ficha"):
    # ... (lógica de insert normal) ...
    
    # Se escolheu combinar, pegamos o ID do exercício selecionado
    id_comb = None
    if combinar_com != "Não":
        id_comb = int(df_recentes[df_recentes['nome'] == combinar_com]['id'].values[0])
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO fichas_treino 
            (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao, exercicio_combinado_id) 
            VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :obs, :comb)
        """), {
            "u": int(id_a), "t": t_nome, "e": int(id_e), "s": s, "r": r, 
            "cg": cg, "td": desc, "tm": tipo_meta, "obs": obs, "comb": id_comb
        })
