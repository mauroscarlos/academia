import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import plotly.express as px
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="SGF Treino Elite", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- FUNÇÃO DE E-MAIL ---
def enviar_email_cadastro(nome, email_destino, username, senha):
    url_sistema = "https://seu-app-de-treino.streamlit.app/" 
    corpo = f"<html><body><h3>Olá, {nome}! 💪</h3><p>Acesse o sistema: <a href='{url_sistema}'>{url_sistema}</a><br>Usuário: {username}<br>Senha: {senha}</p></body></html>"
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "🏋️ Seu Acesso ao SGF Treino chegou!"
        msg.attach(MIMEText(corpo, 'html'))
        with smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
            server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        return True
    except: return False

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
    st.session_state.clear()
    st.rerun()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📈 Evolução")
    df_logs = pd.read_sql(text("SELECT data_execucao, duracao_minutos, treino_nome FROM logs_treino WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
    if not df_logs.empty:
        st.plotly_chart(px.line(df_logs, x="data_execucao", y="duracao_minutos", title="Tempo (min)"), use_container_width=True)
    else: st.info("Sem treinos registrados.")

# --- 2. TREINAR AGORA ---
elif menu == "🏋️ Treinar Agora":
    # Variável padronizada: t_sel
    meus_treinos = pd.read_sql(text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()
    if not meus_treinos:
        st.warning("Nenhuma ficha cadastrada.")
    else:
        t_sel = st.selectbox("Escolha o Treino:", meus_treinos)
        
        if 'treino_andamento' not in st.session_state: st.session_state.treino_andamento = False
        if not st.session_state.treino_andamento:
            if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
                st.session_state.treino_andamento = True
                st.session_state.inicio_t = datetime.now()
                st.rerun()
        else:
            tempo = datetime.now() - st.session_state.inicio_t
            st.success(f"⏱️ Tempo: {str(tempo).split('.')[0]}")
            if st.button("🏁 FINALIZAR"):
                minutos = int(tempo.total_seconds() / 60)
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"), {"u": st.session_state.user_id, "t": t_sel, "d": minutos})
                st.session_state.treino_andamento = False
                st.balloons(); time.sleep(1); st.rerun()

        # Busca exercícios
        df_ex = pd.read_sql(text("SELECT f.*, e.nome, e.url_imagem FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC"), engine, params={"u": st.session_state.user_id, "t": t_sel})
        # Lógica para saber quem é o "primeiro" do bi-set
        nomes_combinados = df_ex['exercicio_combinado_id'].dropna().unique().tolist()

        for _, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150")
                with c2:
                    st.subheader(
