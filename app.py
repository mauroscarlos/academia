import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SGF Treino Elite", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- LOGIN (Estrutura padrão que já usamos) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🏋️ SGF Treino")
    with st.form("login"):
        u = st.text_input("Usuário (nome.sobrenome)").lower().strip()
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

# --- BARRA LATERAL DINÂMICA ---
st.sidebar.title(f"👋 Olá, {st.session_state.user_nome.split()[0]}")

# 1. Busca os treinos específicos deste aluno
query_meus_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
lista_treinos = pd.read_sql(query_meus_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Evolução")
aba_dashboard = st.sidebar.checkbox("Visualizar Dashboard", value=True)

st.sidebar.subheader("📋 Meus Treinos")
treino_selecionado = st.sidebar.radio("Selecione para abrir:", lista_treinos)

if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

# --- ÁREA CENTRAL ---

# 1. DASHBOARD (Lado Esquerdo/Topo)
if aba_dashboard:
    st.title("📈 Minha Evolução")
    # Dados simulados (Podemos criar tabela de histórico depois)
    df_evolucao = pd.DataFrame({
        "Data": pd.date_range(start="2026-01-01", periods=10),
        "Carga Total (kg)": [1000, 1050, 1080, 1100, 1150, 1200, 1180, 1250, 1300, 1350]
    })
    
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        fig1 = px.line(df_evolucao, x="Data", y="Carga Total (kg)", title="Progressão de Carga")
        st.plotly_chart(fig1, use_container_width=True)
    with col_graf2:
        fig2 = px.bar(df_evolucao, x="Data", y="Carga Total (kg)", title="Volume por Sessão")
        st.plotly_chart(fig2, use_container_width=True)
    st.divider()

# 2. CONTEÚDO DO TREINO
if treino_selecionado:
    st.title(f"💪 {treino_selecionado}")
    
    query_exercicios = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, f.tempo_descanso
        FROM fichas_treino f 
        JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df_exercicios = pd.read_sql(query_exercicios, engine, params={"u": st.session_state.user_id, "t": treino_selecionado})
    
    if df_exercicios.empty:
        st.info("Nenhum exercício cadastrado para este treino.")
    else:
        for _, row in df_exercicios.iterrows():
            with st.container():
                col_img, col_txt = st.columns([1, 2])
                with col_img:
                    img = row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/200?text=SGF+Treino"
                    st.image(img, use_container_width=True)
                with col_txt:
                    st.subheader(row['nome'])
                    st.write(f"🔥 **{row['series']} séries x {row['repeticoes']} repetições**")
                    st.write(f"⚖️ Carga Prescrita: **{row['carga_atual']} kg**")
                    
                    # CONTADOR REGRESSIVO (TIMER)
                    tempo_descanso = row['tempo_descanso'] if row['tempo_descanso'] else 60
                    if st.button(f"⏱️ Iniciar Descanso ({tempo_descanso}s)", key=f"timer_{row['id']}"):
                        placeholder = st.empty()
                        for t in range(tempo_descanso, -1, -1):
                            placeholder.metric("⏰ Tempo de Descanso", f"{t}s")
                            time.sleep(1)
                        placeholder.success("👊 Próxima Série! Vamos!")
                        st.balloons()
            st.divider()

# --- ÁREA ADMIN (Apenas para nível 'admin') ---
if st.session_state.user_nivel == 'admin':
    with st.sidebar.expander("🛠️ Painel Admin"):
        # Aqui você pode adicionar links rápidos para as abas de Gestão/Biblioteca
        st.write("Acesse as abas de gestão no menu principal se necessário.")
