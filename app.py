import io
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import time
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="SGF Treino Elite", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🏋️ SGF Treino")
    with st.form("login"):
        u = st.text_input("Usuário").lower().strip()
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            df = pd.read_sql(text("SELECT * FROM usuarios WHERE username = :u AND senha = :s"), engine, params={"u":u, "s":s})
            if not df.empty:
                st.session_state.logado = True
                st.session_state.user_id = int(df.iloc[0]['id'])
                st.session_state.user_nome = df.iloc[0]['nome']
                st.session_state.user_nivel = df.iloc[0]['nivel']
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title(f"👋 {st.session_state.user_nome.split()[0]}")
opcoes = ["📊 Dashboard", "🏋️ Treinar Agora"]
if st.session_state.user_nivel == 'admin':
    opcoes.extend(["📝 Montar Treino", "⚙️ Biblioteca", "🛡️ Gestão de Usuários"])

menu = st.sidebar.radio("Navegação:", opcoes)
if st.sidebar.button("🚪 Sair"):
    st.session_state.clear(); st.rerun()

# --- 2. TREINAR AGORA (ALUNO) ---
if menu == "🏋️ Treinar Agora":
    df_t = pd.read_sql(text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
    if df_t.empty:
        st.warning("Nenhuma ficha encontrada.")
    else:
        t_sel = st.selectbox("Escolha o Treino:", df_t['treino_nome'].tolist())

        # --- EXPORTAÇÃO BLINDAGEM DE AÇO (FOCO ACENTOS BRASIL) ---
        df_ex = pd.read_sql(text("SELECT f.*, e.nome, e.url_imagem FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC"), engine, params={"u": st.session_state.user_id, "t": t_sel})
        
        if not df_ex.empty:
            with st.expander("📥 ACESSAR FICHA OFFLINE / EXPORTAR"):
                st.markdown(f"### 📋 Resumo: {t_sel}")
                
                # Tabela no app (Aqui sempre fica bonito)
                tabela_html = "| Exercício | Séries | Reps | Descanso |\n| :--- | :--- | :--- | :--- |\n"
                for _, r in df_ex.iterrows():
                    tabela_html += f"| **{r['nome']}** | {r['series']} | {r['repeticoes']} | {r['tempo_descanso']}s |\n"
                st.markdown(tabela_html)
                
                st.divider()

                # 1. Preparando os dados
                df_export = df_ex[['nome', 'series', 'repeticoes', 'tempo_descanso']].copy()
                
                # Proteção contra 2006 repetições (Data)
                df_export['repeticoes'] = df_export['repeticoes'].apply(lambda x: f"'{x}")
                
                # Nomes das colunas sem acento para garantir que a 1ª linha não quebre
                df_export.columns = ['Exercicio', 'Series', 'Reps', 'Descanso']

                # 2. A MUDANÇA REAL: ISO-8859-1 (Latin-1)
                # Esse é o formato 'raiz' do Windows Brasil.
                # Se o Excel não ler isso, a gente chama o padre!
                csv_excel = df_export.to_csv(index=False, sep=';', encoding='iso-8859-1')

                st.download_button(
                    label="📥 BAIXAR PARA EXCEL (Blindagem de Aço)",
                    data=csv_excel,
                    file_name=f'Treino_{t_sel}.csv',
                    mime='text/csv',
                    use_container_width=True
                )

        st.divider()

        if 'treino_andamento' not in st.session_state: 
            st.session_state.treino_andamento = False
        
        if st.session_state.treino_andamento:
            tempo = datetime.now() - st.session_state.inicio_t
            st.success(f"⏱️ Tempo de Treino: {str(tempo).split('.')[0]}")
            if st.button("🏁 FINALIZAR TREINO"):
                minutos = int(tempo.total_seconds() / 60)
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"), {"u": st.session_state.user_id, "t": t_sel, "d": minutos})
                st.session_state.treino_andamento = False
                st.rerun()
        else:
            if st.button("🚀 INICIAR TREINO", type="primary"):
                st.session_state.treino_andamento = True
                st.session_state.inicio_t = datetime.now()
                st.rerun()

        # Continuação do código de exibição dos exercícios...
        nomes_no_par = df_ex['exercicio_combinado_id'].dropna().unique().tolist()

        for _, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: 
                    st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    st.subheader(row['nome'])
                    if row['exercicio_combinado_id']: 
                        st.caption(f"🔗 BI-SET COM: {row['exercicio_combinado_id']}")
                    st.write(f"🎯 {row['series']}x {row['repeticoes']} | ⚖️ {row['carga_atual']}kg")
                    
                    if st.session_state.treino_andamento:
                        if row['nome'] in nomes_no_par:
                            st.error("🚫 SEM DESCANSO! Vá para o próximo exercício.")
                        else:
                            if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                                p = st.empty()
                                for t_cnt in range(int(row['tempo_descanso']), -1, -1):
                                    p.metric("Descanso", f"{t_cnt}s")
                                    time.sleep(1)
                                p.success("VAI!")

# --- 3. MONTAR TREINO (COM GRUPOS MUSCULARES) ---
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever Treino")
    st.cache_data.clear()
    
    alunos = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    bib = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    c_al, c_tr = st.columns(2)
    al_sel = c_al.selectbox("Aluno:", alunos['nome'].tolist())
    id_al = int(alunos[alunos['nome'] == al_sel]['id'].values[0])
    tr_sel = c_tr.selectbox("Ficha:", ["Treino A", "Treino B", "Treino C", "Treino D", "Treino E"])

    # --- NOVO: LÓGICA DE GRUPOS DINÂMICOS ---
    st.subheader("🎯 Grupos Musculares da Ficha")
    
    # Inicializa a lista de grupos no estado da sessão se não existir
    if 'lista_grupos_ficha' not in st.session_state:
        st.session_state.lista_grupos_ficha = ["Peito"] # Começa com um padrão

    grupos_disponiveis = ["Peito", "Costas", "Pernas", "Ombros", "Bíceps", "Tríceps", "Abdomen", "Cardio", "Glúteos", "Antebraço"]

    # Renderiza os seletores baseados no que está na lista
    col_g1, col_g2 = st.columns([3, 1])
    
    for i, grupo_atual in enumerate(st.session_state.lista_grupos_ficha):
        st.session_state.lista_grupos_ficha[i] = st.selectbox(
            f"Grupo {i+1}", 
            grupos_disponiveis, 
            index=grupos_disponiveis.index(grupo_atual) if grupo_atual in grupos_disponiveis else 0,
            key=f"grupo_sel_{i}"
        )

    # Botões para adicionar ou remover campos
    c_btn1, c_btn2, _ = st.columns([1, 1, 2])
    if c_btn1.button("➕ Adicionar Grupo"):
        st.session_state.lista_grupos_ficha.append("Peito")
        st.rerun()
    
    if c_btn2.button("🗑️ Remover Último") and len(st.session_state.lista_grupos_ficha) > 1:
        st.session_state.lista_grupos_ficha.pop()
        st.rerun()

    # Cria o texto final que será exibido (ex: "Peito + Tríceps")
    foco_texto = " + ".join(list(set(st.session_state.lista_grupos_ficha))) # 'set' remove duplicados acidentais
    st.info(f"**Foco do {tr_sel}:** {foco_texto}")

    lista_bib = bib['nome'].tolist()
    if 'form_token' not in st.session_state: st.session_state.form_token = 0

    with st.container(border=True):
        st.subheader("Configurar Exercício(s)")
        
        # Seleção de Exercícios (Campos de busca costumam ser largos, mantidos em destaque)
        ex1 = st.selectbox("1. Exercício Principal:", lista_bib, key=f"ex1_{st.session_state.form_token}")
        ex2_check = st.selectbox("2. Combinar com outro (Bi-set)?", ["Não", "Sim"], key=f"ex2_check_{st.session_state.form_token}")
        
        ex2 = "Não"
        if ex2_check == "Sim":
            ex2 = st.selectbox("Selecione o segundo exercício:", lista_bib, key=f"ex2_{st.session_state.form_token}")
        
        st.divider()

        # --- A LINHA ÚNICA DEFINITIVA ---
        if ex2_check == "Sim":
            # Layout Bi-set: Tipo, Séries, R1, R2, Desc, Kg
            c_tp, c_sr, c_r1, c_r2, c_ds, c_cg = st.columns([1.5, 0.8, 1.2, 1.2, 0.8, 0.8])
            tipo_meta_v = c_tp.selectbox("Tipo", ["Reps", "Tempo", "Pirâmide"], key=f"tp_{st.session_state.form_token}")
            series = c_sr.number_input("Séries", 1, 12, 3, key=f"sr_{st.session_state.form_token}")
            
            label_din = "Tempo" if tipo_meta_v == "Tempo" else "Reps"
            final_reps1 = c_r1.text_input(f"{label_din} 1", "12", key=f"r1_{st.session_state.form_token}")
            final_reps2 = c_r2.text_input(f"{label_din} 2", "10", key=f"r2_{st.session_state.form_token}")
            descanso = c_ds.number_input("Desc.", 0, 300, 60, key=f"ds_{st.session_state.form_token}")
            carga = c_cg.text_input("Kg", "10", key=f"cg_{st.session_state.form_token}")
        
        else:
            # Layout Simples: Tipo, Séries, Reps/Tempo, Descanso, Carga
            c_tp, c_sr, c_rp, c_ds, c_cg = st.columns([1.5, 0.8, 2, 0.8, 0.8])
            tipo_meta_v = c_tp.selectbox("Tipo", ["Reps", "Tempo", "Pirâmide"], key=f"tp_{st.session_state.form_token}")
            series = c_sr.number_input("Séries", 1, 12, 3, key=f"sr_{st.session_state.form_token}")
            
            label_din = "Tempo" if tipo_meta_v == "Tempo" else "Reps"
            final_reps1 = c_rp.text_input(label_din, "12", key=f"r1_{st.session_state.form_token}")
            final_reps2 = "12"
            descanso = c_ds.number_input("Desc.", 0, 300, 60, key=f"ds_{st.session_state.form_token}")
            carga = c_cg.text_input("Kg", "10", key=f"cg_{st.session_state.form_token}")

        # Se for Pirâmide, os campos de reps aparecem logo abaixo da linha principal
        if tipo_meta_v == "Pirâmide":
            st.write(f"🔢 Reps da Pirâmide ({series} séries):")
            cols_p = st.columns(series)
            reps_list = []
            for i in range(series):
                r_val = cols_p[i].text_input(f"S{i+1}", "12", key=f"p1_s{i}_{st.session_state.form_token}", label_visibility="collapsed")
                reps_list.append(r_val)
            final_reps1 = " - ".join(reps_list)

        st.write("") 
        if st.button("✅ SALVAR NA FICHA", use_container_width=True, type="primary"):
            id_ex1 = int(bib[bib['nome'] == ex1]['id'].values[0])
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, exercicio_combinado_id) 
                    VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :cb)
                """), {
                    "u": id_al, "t": tr_sel, "e": id_ex1, "s": series, "r": final_reps1, 
                    "cg": carga, "td": 0 if ex2_check == "Sim" else descanso, "tm": tipo_meta_v, "cb": ex2 if ex2_check == "Sim" else None
                })
                
                if ex2_check == "Sim":
                    id_ex2 = int(bib[bib['nome'] == ex2]['id'].values[0])
                    conn.execute(text("""
                        INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, exercicio_combinado_id) 
                        VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :cb)
                    """), {
                        "u": id_al, "t": tr_sel, "e": id_ex2, "s": series, "r": final_reps2 if final_reps2 else final_reps1, 
                        "cg": carga, "td": descanso, "tm": tipo_meta_v, "cb": None
                    })
            
            st.session_state.form_token += 1
            st.success("Salvo!")
            time.sleep(0.5)
            st.rerun()

    st.divider()
    df_ficha = pd.read_sql(text("SELECT f.id, e.nome, f.repeticoes, f.exercicio_combinado_id FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC"), engine, params={"u": id_al, "t": tr_sel})
    if not df_ficha.empty:
        st.subheader(f"📋 Resumo do {tr_sel}")
        for _, r in df_ficha.iterrows():
            c1, c2 = st.columns([4, 1])
            txt = f"🔹 **{r['nome']}** - {r['repeticoes']} reps"
            if r['exercicio_combinado_id']: txt += f" (Bi-set com {r['exercicio_combinado_id']})"
            c1.write(txt)
            if c2.button("🗑️", key=f"del_{r['id']}"):
                with engine.begin() as conn: conn.execute(text("DELETE FROM fichas_treino WHERE id = :id"), {"id": r['id']})
                st.rerun()

# --- ESPAÇO PARA EXPORTAÇÃO ---
    if not df_ficha.empty:
        st.divider()
        st.subheader("📤 Exportar para o Aluno")
        
        # 1. Gerar Texto Formatado para WhatsApp/Offline
        texto_treino = f"🏠 *FICHA DE TREINO: {tr_sel}*\n"
        texto_treino += f"👤 Aluno: {al_sel}\n"
        texto_treino += "--------------------------\n"
        
        for _, r in df_ficha.iterrows():
            # Busca descanso na ficha para o texto
            detalhe = pd.read_sql(text("SELECT tempo_descanso FROM fichas_treino WHERE id = :id"), engine, params={"id": r['id']})
            desc = detalhe.iloc[0]['tempo_descanso'] if not detalhe.empty else 60
            
            texto_treino += f"✅ *{r['nome']}*\n"
            texto_treino += f"   Set: {r['repeticoes']} reps\n"
            if r['exercicio_combinado_id']:
                texto_treino += f"   🔗 Bi-set com: {r['exercicio_combinado_id']}\n"
            texto_treino += f"   ⏱️ Descanso: {desc}s\n\n"

        texto_treino += "--------------------------\n"
        texto_treino += "💪 Bons treinos! Gerado por SGF Elite."

        # Botões de Exportação
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            st.text_area("Copiar para WhatsApp:", texto_treino, height=200)
            st.caption("Selecione o texto acima e envie para o aluno.")
            
        with col_exp2:
            # Exportar CSV (Excel/Offline)
            csv = df_ficha[['nome', 'repeticoes']].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Planilha (Excel)",
                data=csv,
                file_name=f'Treino_{al_sel}_{tr_sel}.csv',
                mime='text/csv',
                use_container_width=True
            )

# --- 4. BIBLIOTECA / 5. GESTÃO (Estrutura básica para manter o app rodando) ---
elif menu == "⚙️ Biblioteca":
    st.header("⚙️ Biblioteca")
    with st.form("bib"):
        n = st.text_input("Nome"); g = st.selectbox("Grupo", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"]); u = st.text_input("URL Imagem")
        if st.form_submit_button("Salvar"):
            with engine.begin() as conn: conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :u)"), {"n":n, "g":g, "u":u})
            st.rerun()
    st.dataframe(pd.read_sql("SELECT nome, grupo_muscular FROM exercicios_biblioteca ORDER BY nome", engine), use_container_width=True)

elif menu == "🛡️ Gestão de Usuários":
    st.header("🛡️ Alunos")
    with st.form("user"):
        nome, email, user, senha = st.text_input("Nome"), st.text_input("Email"), st.text_input("Usuário"), st.text_input("Senha")
        if st.form_submit_button("Cadastrar"):
            u_l = user.lower().strip().replace(" ", ".")
            with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :e, :u, :s, 'user')"), {"n":nome, "e":email, "u":u_l, "s":senha})
            st.rerun()
    st.dataframe(pd.read_sql("SELECT nome, email, username FROM usuarios WHERE nivel = 'user'", engine), use_container_width=True)

elif menu == "📊 Dashboard":
    st.title("📈 Dashboard")
    st.info("Logs de evolução aparecerão aqui conforme os treinos forem finalizados.")
