import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SGF Treino - Meu Personal", layout="wide", page_icon="💪")

# --- CONEXÃO COM O NOVO PROJETO SUPABASE ---
@st.cache_resource
def get_engine():
    # Certifique-se de que a secret 'url' aponta para o novo projeto
    url = st.secrets["connections"]["postgresql"]["url"]
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- ESTILIZAÇÃO PARA CELULAR ---
st.markdown("""
    <style>
        .stButton button { width: 100%; border-radius: 10px; height: 3rem; font-weight: bold; }
        .card-treino { padding: 15px; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 10px; border-left: 5px solid #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIN SIMPLIFICADO (Mesma lógica que você já domina) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🏋️ SGF Treino")
    with st.form("login"):
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            query = text("SELECT * FROM usuarios WHERE email = :e AND senha = :s")
            user_df = pd.read_sql(query, engine, params={"e": email, "s": senha})
            if not user_df.empty:
                st.session_state.logado = True
                st.session_state.user_id = int(user_df.iloc[0]['id'])
                st.session_state.user_nome = user_df.iloc[0]['nome']
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- MENU ---
menu = st.sidebar.selectbox("Ir para:", ["🏋️ Treinar Agora", "📝 Montar Treino", "⚙️ Biblioteca"])

# --- ABA 1: BIBLIOTECA (Popular exercícios) ---
if menu == "⚙️ Biblioteca":
    st.header("📚 Biblioteca de Exercícios")
    with st.form("add_ex"):
        n = st.text_input("Nome do Exercício (Ex: Supino Reto)")
        g = st.selectbox("Grupo Muscular", ["Peito", "Costas", "Pernas", "Braços", "Ombros", "Abdominais"])
        if st.form_submit_button("Cadastrar na Base"):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular) VALUES (:n, :g)"), {"n":n, "g":g})
            st.success("Cadastrado!")

# --- ABA 2: MONTAR TREINO ---
elif menu == "📝 Montar Treino":
    st.header("📝 Montar Minha Ficha")
    
    try:
        exs = pd.read_sql("SELECT * FROM exercicios_biblioteca ORDER BY nome", engine)
        if exs.empty:
            st.warning("Cadastre exercícios na biblioteca primeiro!")
        else:
            with st.form("ficha"):
                t_nome = st.selectbox("Qual Treino?", ["Treino A", "Treino B", "Treino C"])
                ex_id = st.selectbox("Selecione o Exercício", exs['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                ser = c1.number_input("Séries", 1, 10, 3)
                rep = c2.text_input("Reps", "12")
                carga = c3.text_input("Peso (kg)", "0")
                
                if st.form_submit_button("Adicionar à Ficha"):
                    # Pega o ID real do exercício
                    id_real = exs[exs['nome'] == ex_id]['id'].values[0]
                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual)
                            VALUES (:u, :tn, :ei, :s, :r, :c)
                        """), {"u":st.session_state.user_id, "tn":t_nome, "ei":int(id_real), "s":ser, "r":rep, "c":carga})
                    st.success("Adicionado!")
    except: st.error("Erro ao carregar banco de dados.")

# --- ABA 3: TREINAR AGORA ---
elif menu == "🏋️ Treinar Agora":
    st.title(f"💪 Bora, {st.session_state.user_nome}!")
    treino_hj = st.selectbox("Qual treino hoje?", ["Treino A", "Treino B", "Treino C"])
    
    query = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.grupo_muscular
        FROM fichas_treino f
        JOIN exercicios_biblioteca e ON f.exercicio_id = e.id
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df = pd.read_sql(query, engine, params={"u":st.session_state.user_id, "t":treino_hj})
    
    if df.empty:
        st.info("Nenhum exercício na ficha para hoje.")
    else:
        for _, row in df.iterrows():
            st.markdown(f"""
                <div class="card-treino">
                    <b>{row['nome']}</b><br>
                    <small>{row['grupo_muscular']} | {row['series']}x{row['repeticoes']} | Carga: {row['carga_atual']}kg</small>
                </div>
            """, unsafe_allow_html=True)
            # Botão para marcar como feito ou ajustar carga
            if st.button(f"Concluir {row['nome']}", key=row['id']):
                st.toast(f"Boa! {row['nome']} concluído!")
