import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SGF Treino Elite", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- LOGIN ---
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

# --- ESTADOS DO CRONÔMETRO ---
if 'treino_em_andamento' not in st.session_state:
    st.session_state.treino_em_andamento = False
if 'inicio_treino' not in st.session_state:
    st.session_state.inicio_treino = None

# --- BARRA LATERAL ---
st.sidebar.title(f"👋 {st.session_state.user_nome.split()[0]}")

query_meus_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
lista_treinos = pd.read_sql(query_meus_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()

st.sidebar.markdown("---")
aba_dashboard = st.sidebar.checkbox("📊 Ver Evolução", value=True)
treino_selecionado = st.sidebar.radio("📋 Meus Treinos:", lista_treinos if lista_treinos else ["Nenhum treino"])

if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

# --- ÁREA CENTRAL ---

# 1. DASHBOARD (EVOLUÇÃO REAL)
if aba_dashboard:
    st.title("📈 Minha Evolução")
    query_logs = text("SELECT data_execucao, duracao_minutos, treino_nome FROM logs_treino WHERE usuario_id = :u ORDER BY data_execucao ASC")
    df_logs = pd.read_sql(query_logs, engine, params={"u": st.session_state.user_id})
    
    if not df_logs.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.line(df_logs, x="data_execucao", y="duracao_minutos", title="Duração dos Treinos (min)", markers=True)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.pie(df_logs, names="treino_nome", title="Distribuição de Treinos")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Complete seu primeiro treino para ver os gráficos!")
    st.divider()

# 2. ÁREA DE TREINO
if treino_selecionado and treino_selecionado != "Nenhum treino":
    st.title(f"💪 {treino_selecionado}")

    # BOTÕES DE CONTROLE DO TEMPO
    if not st.session_state.treino_em_andamento:
        if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
            st.session_state.treino_em_andamento = True
            st.session_state.inicio_treino = datetime.now()
            st.rerun()
    else:
        duracao_atual = datetime.now() - st.session_state.inicio_treino
        st.success(f"⏱️ Tempo decorrido: {str(duracao_atual).split('.')[0]}")
        if st.button("🏁 ENCERRAR TREINO", use_container_width=True):
            st.session_state.confirmar_fim = True

    # EXIBIÇÃO DOS EXERCÍCIOS
    query_ex = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, f.tempo_descanso
        FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df_ex = pd.read_sql(query_ex, engine, params={"u": st.session_state.user_id, "t": treino_selecionado})

    for idx, row in df_ex.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                img = row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150"
                st.image(img, use_container_width=True)
            with c2:
                st.subheader(row['nome'])
                st.write(f"**{row['series']} séries x {row['repeticoes']}** | Carga: **{row['carga_atual']}kg**")
                
                if st.session_state.treino_em_andamento:
                    if st.button(f"⏱️ Descanso ({row['tempo_descanso']}s)", key=f"t_{row['id']}"):
                        placeholder = st.empty()
                        for t in range(int(row['tempo_descanso']), -1, -1):
                            placeholder.metric("Descansando...", f"{t}s")
                            time.sleep(1)
                        placeholder.success("Próxima série!")
                        if idx == len(df_ex) - 1:
                            st.balloons()
                            st.info("🎉 Treino concluído! Clique em ENCERRAR no topo.")

    # CONFIRMAÇÃO DE ENCERRAMENTO
    if st.session_state.get('confirmar_fim'):
        st.warning("### Confirmar encerramento?")
        cf1, cf2 = st.columns(2)
        if cf1.button("✅ Sim, Salvar"):
            duracao_min = int((datetime.now() - st.session_state.inicio_treino).total_seconds() / 60)
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"),
                             {"u": st.session_state.user_id, "t": treino_selecionado, "d": duracao_min})
            st.session_state.treino_em_andamento = False
            st.session_state.confirmar_fim = False
            st.success("Treino registrado!")
            time.sleep(2)
            st.rerun()
        if cf2.button("❌ Não, Voltar"):
            st.session_state.confirmar_fim = False
            st.rerun()
