import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
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

# --- LOGIN (Simplificado, mantenha sua lógica) ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    # ... (Seu formulário de login aqui) ...
    st.stop()

# --- MENU LATERAL ---
st.sidebar.title(f"👋 {st.session_state.user_nome.split()[0]}")
opcoes = ["📊 Dashboard", "🏋️ Treinar Agora"]
if st.session_state.user_nivel == 'admin':
    opcoes.extend(["📝 Montar Treino", "⚙️ Biblioteca", "🛡️ Gestão de Usuários"])

menu = st.sidebar.radio("Navegação:", opcoes)

# --- 2. TREINAR AGORA (COM LÓGICA DE BI-SET) ---
if menu == "🏋️ Treinar Agora":
    query_meus_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
    meus_treinos = pd.read_sql(query_meus_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()
    
    if not meus_treinos:
        st.warning("Nenhuma ficha encontrada.")
    else:
        t_sel = st.selectbox("Selecione o Treino:", meus_treinos)
        
        # Cronômetro de Treino
        if 'treino_andamento' not in st.session_state: st.session_state.treino_andamento = False
        if not st.session_state.treino_andamento:
            if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
                st.session_state.treino_andamento = True
                st.session_state.inicio_t = datetime.now()
                st.rerun()
        else:
            if st.button("🏁 FINALIZAR TREINO", use_container_width=True):
                # ... (lógica de salvar log que já temos) ...
                st.session_state.treino_andamento = False
                st.rerun()

        # Busca Exercícios
        query_ex = text("""
            SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, 
                   f.tempo_descanso, f.tipo_meta, f.observacao, f.exercicio_combinado_id
            FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC
        """)
        df_ex = pd.read_sql(query_ex, engine, params={"u": st.session_state.user_id, "t": t_sel})
        
        # Lista para saber quem é o "primeiro" de um Bi-set
        ids_segundos = df_ex['exercicio_combinado_id'].dropna().tolist()

        for idx, row in df_ex.iterrows():
            # Estilo visual para Bi-set
            is_bi_set = row['exercicio_combinado_id'] is not None
            border_color = "#ff4b4b" if is_bi_set else "#f0f2f6"
            
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    if is_bi_set: st.caption("🔗 COMBINADO COM O ANTERIOR")
                    st.subheader(row['nome'])
                    st.write(f"🎯 **{row['series']}x {row['repeticoes']}** ({row['tipo_meta']}) | ⚖️ {row['carga_atual']}kg")
                    if row['observacao']: st.info(f"💡 {row['observacao']}")
                    
                    if st.session_state.get('treino_andamento'):
                        # Se este exercício é apontado por outro como combinado, ele não tem descanso próprio
                        if row['id'] in ids_segundos:
                            st.error("🚫 SEM DESCANSO! Faça o próximo exercício imediatamente.")
                        else:
                            if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                                p = st.empty()
                                for t in range(int(row['tempo_descanso']), -1, -1):
                                    p.metric("Descanso", f"{t}s"); time.sleep(1)
                                p.success("VAI!")

# --- 3. MONTAR TREINO (COM RESET E BI-SET) ---
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever Treino")
    if 'form_count' not in st.session_state: st.session_state.form_count = 0

    alunos = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    exs = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    with st.form(key=f"montar_{st.session_state.form_count}"):
        aluno_sel = st.selectbox("Aluno", alunos['nome'].tolist())
        id_aluno = alunos[alunos['nome'] == aluno_sel]['id'].values[0]
        t_nome = st.selectbox("Treino", ["Treino A", "Treino B", "Treino C", "Treino D"])
        
        # Busca exercícios já na ficha para combinar
        atuais = pd.read_sql(text("SELECT f.id, e.nome FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t"), 
                             engine, params={"u": int(id_aluno), "t": t_nome})
        
        ex_sel = st.selectbox("Exercício", exs['nome'].tolist())
        combinar = st.selectbox("Combinar com anterior (Bi-set)?", ["Não"] + atuais['nome'].tolist())
        
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("Tipo", ["Repetições", "Tempo (s)", "Pirâmide"])
        rep = c2.text_input("Meta", "12")
        ser = c3.number_input("Séries", 1, 10, 3)
        
        cg = st.text_input("Carga (kg)", "10")
        desc = st.number_input("Descanso (s)", 0, 300, 60)
        obs = st.text_area("Observação")
        
        if st.form_submit_button("✅ Adicionar"):
            id_ex = exs[exs['nome'] == ex_sel]['id'].values[0]
            id_comb = atuais[atuais['nome'] == combinar]['id'].values[0] if combinar != "Não" else None
            
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao, exercicio_combinado_id)
                    VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :ob, :cb)
                """), {"u":int(id_aluno), "t":t_nome, "e":int(id_ex), "s":ser, "r":rep, "cg":cg, "td":desc, "tm":tipo, "ob":obs, "cb":id_comb})
            
            st.session_state.form_count += 1
            st.success("Adicionado!")
            time.sleep(1); st.rerun()
