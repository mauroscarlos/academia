import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="SGF Treino", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    conn_url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(conn_url, pool_pre_ping=True)

engine = get_engine()

# --- FUNÇÃO DE NOTIFICAÇÃO ---
def enviar_email_treino(nome, email_destino, username, senha):
    msg_corpo = f"""
    <html><body>
        <h2>Bem-vindo à academia, {nome}! 🏋️</h2>
        <p>Sua ficha de treino já está disponível no sistema.</p>
        <p><b>Seus dados de acesso:</b><br>
        Usuário: {username}<br>
        Senha: {senha}</p>
        <p><a href="https://share.streamlit.io/">Acessar Meu Treino</a></p>
    </body></html>
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = email_destino
        msg['Subject'] = "💪 Seu acesso ao SGF Treino chegou!"
        msg.attach(MIMEText(msg_corpo, 'html'))
        server = smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], st.secrets["email"]["smtp_port"])
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        return True
    except: return False

# --- (Aqui entra sua lógica de login que já funciona) ---
# ... [Código de Login] ...

# --- 4. GESTÃO DE USUÁRIOS (ADMIN) ---
if "logado" in st.session_state and st.session_state.user_nivel == 'admin':
    if menu == "🛡️ Gestão de Usuários":
        st.header("🛡️ Gerenciar Alunos")
        
        with st.expander("➕ Cadastrar Novo Aluno", expanded=False):
            with st.form("cad_aluno", clear_on_submit=True):
                nome_a = st.text_input("Nome Completo")
                email_a = st.text_input("E-mail do Aluno")
                user_a = st.text_input("Username (nome.sobrenome)")
                pass_a = st.text_input("Senha", type="password")
                
                if st.form_submit_button("Salvar e Notificar"):
                    user_limpo = user_a.lower().strip().replace(" ", ".")
                    if nome_a and email_a and user_limpo:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO usuarios (nome, email, username, senha, nivel, status) 
                                    VALUES (:n, :e, :u, :s, 'user', 'ativo')
                                """), {"n": nome_a, "e": email_a, "u": user_limpo, "s": pass_a})
                            
                            if enviar_email_treino(nome_a, email_a, user_limpo, pass_a):
                                st.success("Aluno cadastrado e notificado!")
                            else:
                                st.warning("Aluno cadastrado, mas falha no envio do e-mail.")
                        except Exception as e: st.error(f"Erro: {e}")

# --- LÓGICA DE VALIDADE DE TREINO ---
if menu == "🏋️ Treinar Agora":
    st.header("🚀 Meu Treino")
    
    # Verifica validade do treino
    query_validade = text("""
        SELECT MIN(data_vencimento) as vencimento 
        FROM fichas_treino WHERE usuario_id = :u
    """)
    res_v = pd.read_sql(query_validade, engine, params={"u": st.session_state.user_id})
    
    if not res_v.empty and res_v.iloc[0]['vencimento']:
        vencimento = pd.to_datetime(res_v.iloc[0]['vencimento']).date()
        hoje = datetime.now().date()
        dias_restantes = (vencimento - hoje).days
        
        if dias_restantes <= 7 and dias_restantes > 0:
            st.warning(f"⚠️ Seu treino vence em {dias_restantes} dias! Solicite uma nova ficha.")
        elif dias_restantes <= 0:
            st.error("🚨 Seu treino expirou! Fale com o instrutor para renovar.")

# --- 2. MONTAR TREINO (COM VALIDADE) ---
elif menu == "📝 Montar Treino":
    st.header("📝 Configurar Ficha")
    # ... [Busca de exercícios anterior] ...
    with st.form("f_ficha"):
        # Campos anteriores...
        val_dias = st.slider("Validade do Treino (Dias)", 30, 90, 60)
        if st.form_submit_button("Salvar"):
            data_venc = datetime.now().date() + timedelta(days=val_dias)
            # No INSERT, adicione: data_vencimento = :dv
