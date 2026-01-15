import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="SGF Treino - Elite", layout="wide", page_icon="💪")

# --- CONEXÃO ---
@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def enviar_email_cadastro(nome, email_destino, username, senha):
    corpo = f"<html><body><h3>Olá, {nome}! 💪</h3><p>Seu acesso ao <b>SGF Treino</b> foi criado.</p><p>Usuário: {username}<br>Senha: {senha}</p></body></html>"
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "🏋️ Seu Acesso ao SGF Treino"
        msg.attach(MIMEText(corpo, 'html'))
        with smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"]) as server:
            server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        return True
    except: return False

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
            else: st.error("Usuário ou senha inválidos.")
    st.stop()

# --- MENU LATERAL ---
st.sidebar.title(f"Olá, {st.session_state.user_nome.split()[0]}!")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

opcoes = ["🏋️ Treinar Agora", "📝 Montar Treino", "⚙️ Biblioteca"]
if st.session_state.user_nivel == 'admin':
    opcoes.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Ir para:", opcoes)

# --- 1. TREINAR AGORA ---
if menu == "🏋️ Treinar Agora":
    st.header("🚀 Meu Treino")
    t_sel = st.selectbox("Escolha o treino:", ["Treino A", "Treino B", "Treino C", "Treino D"])
    query = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.grupo_muscular, e.url_imagem
        FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df_t = pd.read_sql(query, engine, params={"u": st.session_state.user_id, "t": t_sel})
    
    if df_t.empty:
        st.info("Nenhum exercício nesta ficha.")
    else:
        for _, row in df_t.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    img = row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150?text=SGF+Treino"
                    st.image(img, use_container_width=True)
                with col2:
                    st.subheader(row['nome'])
                    st.write(f"**{row['series']}x{row['repeticoes']}** | Carga: {row['carga_atual']}kg")
                st.divider()

# --- 2. MONTAR TREINO ---
elif menu == "📝 Montar Treino":
    st.header("📝 Nova Ficha")
    alunos = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user'", engine)
    exs = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    with st.form("ficha"):
        aluno_id = st.selectbox("Para qual aluno?", alunos['nome'].tolist())
        t_nome = st.selectbox("Treino", ["Treino A", "Treino B", "Treino C", "Treino D"])
        ex_nome = st.selectbox("Exercício", exs['nome'].tolist())
        c1, c2 = st.columns(2)
        ser = c1.number_input("Séries", 1, 10, 3)
        rep = c2.text_input("Reps", "12")
        dias = st.slider("Validade da ficha (dias)", 30, 90, 60)
        
        if st.form_submit_button("Adicionar à Ficha"):
            id_a = alunos[alunos['nome'] == aluno_id]['id'].values[0]
            id_e = exs[exs['nome'] == ex_nome]['id'].values[0]
            dt_venc = datetime.now().date() + timedelta(days=dias)
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, data_vencimento)
                    VALUES (:u, :t, :e, :s, :r, :v)
                """), {"u": int(id_a), "t": t_nome, "e": int(id_e), "s": ser, "r": rep, "v": dt_venc})
            st.success("Exercício adicionado com sucesso!")

# --- 3. BIBLIOTECA ---
elif menu == "⚙️ Biblioteca":
    st.header("📚 Biblioteca de Exercícios")
    with st.form("add_lib", clear_on_submit=True):
        n = st.text_input("Nome do Exercício")
        g = st.selectbox("Grupo", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"])
        img_url = st.text_input("URL da Imagem (GIF ou JPG)")
        if st.form_submit_button("Salvar"):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :i)"),
                             {"n": n, "g": g, "i": img_url})
            st.success("Cadastrado!")

# --- 4. GESTÃO DE USUÁRIOS ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("👥 Alunos")
    with st.form("cad_user", clear_on_submit=True):
        n = st.text_input("Nome Completo")
        em = st.text_input("Email")
        us = st.text_input("Username (nome.sobrenome)")
        se = st.text_input("Senha")
        if st.form_submit_button("Cadastrar e Notificar"):
            us_l = us.lower().strip().replace(" ", ".")
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :em, :u, :s, 'user')"),
                             {"n":n, "em":em, "u":us_l, "s":se})
            enviar_email_cadastro(n, em, us_l, se)
            st.success("Aluno cadastrado!")
