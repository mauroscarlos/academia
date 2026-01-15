import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SGF Treino - Gestão de Academia", layout="wide", page_icon="💪")

# --- FUNÇÃO DE CONEXÃO REVISADA ---
@st.cache_resource
def get_engine():
    # Puxa os dados das secrets separadamente (conforme configuramos no último passo)
    creds = st.secrets["connections"]["postgresql"]
    
    # Monta a URL de forma segura
    user = creds['username']
    pw = creds['password']
    host = creds['host']
    port = creds['port']
    db = creds['database']
    
    conn_url = f"postgresql://{user}:{pw}@{host}:{port}/{db}?pgbouncer=true"
    
    return create_engine(conn_url, pool_pre_ping=True)

# ESTA LINHA É ESSENCIAL: Ela cria a variável que o restante do código usa
engine = get_engine()

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
        .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
        .card-treino { 
            padding: 15px; 
            border-radius: 10px; 
            background-color: #f0f2f6; 
            margin-bottom: 10px; 
            border-left: 5px solid #ff4b4b;
            color: #1f1f1f;
        }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🏋️ SGF Treino")
    st.subheader("Acesso ao Sistema")
    
    with st.form("login_form"):
        u_input = st.text_input("Usuário (nome.sobrenome)", placeholder="ex: mauro.silva")
        senha_input = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar"):
            # Limpa o input do usuário
            u_limpo = u_input.lower().strip()
            query = text("SELECT * FROM usuarios WHERE username = :u AND senha = :s")
            user_df = pd.read_sql(query, engine, params={"u": u_limpo, "s": senha_input})
            
            if not user_df.empty:
                if user_df.iloc[0]['status'] == 'bloqueado':
                    st.error("❌ Conta bloqueada.")
                else:
                    st.session_state.logado = True
                    st.session_state.user_id = int(user_df.iloc[0]['id'])
                    st.session_state.user_nome = user_df.iloc[0]['nome']
                    st.session_state.user_nivel = user_df.iloc[0]['nivel']
                    st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- INTERFACE PRINCIPAL (PÓS-LOGIN) ---
st.sidebar.title(f"💪 Olá, {st.session_state.user_nome.split()[0]}!")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

opcoes = ["🏋️ Treinar Agora", "📝 Montar Treino", "⚙️ Biblioteca"]
if st.session_state.user_nivel == 'admin':
    opcoes.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Navegação", opcoes)

# --- 1. TREINAR AGORA ---
if menu == "🏋️ Treinar Agora":
    st.header("🚀 Meu Treino de Hoje")
    treino_selecionado = st.selectbox("Selecione a ficha:", ["Treino A", "Treino B", "Treino C", "Treino D"])
    
    query = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.grupo_muscular
        FROM fichas_treino f
        JOIN exercicios_biblioteca e ON f.exercicio_id = e.id
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df = pd.read_sql(query, engine, params={"u": st.session_state.user_id, "t": treino_selecionado})
    
    if df.empty:
        st.info(f"Você ainda não tem exercícios cadastrados no {treino_selecionado}.")
    else:
        for idx, row in df.iterrows():
            with st.container():
                st.markdown(f"""
                    <div class="card-treino">
                        <div style="font-size: 1.2rem; font-weight: bold;">{row['nome']}</div>
                        <div>{row['grupo_muscular']} | {row['series']} séries de {row['repeticoes']}</div>
                        <div style="color: #ff4b4b; font-weight: bold;">Carga Atual: {row['carga_atual']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Input de carga rápida
                nova_carga = st.text_input("Ajustar Peso (kg)", value=row['carga_atual'], key=f"c_{row['id']}")
                if nova_carga != row['carga_atual']:
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE fichas_treino SET carga_atual = :c WHERE id = :id"), {"c": nova_carga, "id": row['id']})
                st.divider()

# --- 2. MONTAR TREINO ---
elif menu == "📝 Montar Treino":
    st.header("📝 Configurar Ficha")
    
    try:
        exs_df = pd.read_sql("SELECT * FROM exercicios_biblioteca ORDER BY nome", engine)
        
        with st.form("form_ficha", clear_on_submit=True):
            t_nome = st.selectbox("Para qual treino?", ["Treino A", "Treino B", "Treino C", "Treino D"])
            ex_selecionado = st.selectbox("Escolha o Exercício", exs_df['nome'].tolist())
            col1, col2, col3 = st.columns(3)
            ser = col1.number_input("Séries", 1, 10, 3)
            rep = col2.text_input("Reps", "12")
            carga = col3.text_input("Carga (kg)", "10")
            
            if st.form_submit_button("Adicionar à Ficha"):
                ex_id = int(exs_df[exs_df['nome'] == ex_selecionado]['id'].values[0])
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual)
                        VALUES (:u, :tn, :ei, :s, :r, :c)
                    """), {"u": st.session_state.user_id, "tn": t_nome, "ei": ex_id, "s": ser, "r": rep, "c": carga})
                st.success("Adicionado!")
                st.rerun()
    except:
        st.error("Biblioteca de exercícios vazia ou erro no banco.")

# --- 3. BIBLIOTECA ---
elif menu == "⚙️ Biblioteca":
    st.header("📚 Biblioteca Global")
    with st.form("form_lib", clear_on_submit=True):
        n_ex = st.text_input("Nome do Exercício")
        g_ex = st.selectbox("Grupo Muscular", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"])
        if st.form_submit_button("Salvar Exercício"):
            if n_ex:
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular) VALUES (:n, :g)"), {"n": n_ex, "g": g_ex})
                st.success("Salvo!")
            else: st.error("Dê um nome ao exercício.")

# --- 4. GESTÃO DE USUÁRIOS (ADMIN) ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("🛡️ Gerenciar Alunos")
    
    with st.expander("➕ Cadastrar Novo Aluno", expanded=False):
        with st.form("cad_aluno", clear_on_submit=True):
            nome_a = st.text_input("Nome Completo")
            user_a = st.text_input("Username (nome.sobrenome)")
            pass_a = st.text_input("Senha", type="password")
            if st.form_submit_button("Salvar Aluno"):
                user_limpo = user_a.lower().strip().replace(" ", ".")
                # Verifica duplicidade
                check = pd.read_sql(text("SELECT id FROM usuarios WHERE username = :u"), engine, params={"u": user_limpo})
                if not check.empty:
                    st.error("❌ Username já existe!")
                else:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO usuarios (nome, username, senha, nivel, status) 
                            VALUES (:n, :u, :s, 'user', 'ativo')
                        """), {"n": nome_a, "u": user_limpo, "s": pass_a})
                    st.success("Aluno cadastrado!")
                    st.rerun()

    st.divider()
    df_users = pd.read_sql("SELECT id, nome, username, status FROM usuarios ORDER BY nome", engine)
    st.write("### Lista de Alunos")
    st.dataframe(df_users, use_container_width=True)
