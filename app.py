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
    corpo = f"""
    <html><body>
        <h3>Olá, {nome}! 💪</h3>
        <p>Seu acesso ao <b>SGF Treino</b> foi criado com sucesso.</p>
        <p><b>Seus dados de login:</b><br>
        Usuário: <code>{username}</code><br>
        Senha: <code>{senha}</code></p>
        <hr>
        <p>Bons treinos!</p>
    </body></html>
    """
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
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

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

# --- MENU LATERAL (Define a variável 'menu') ---
st.sidebar.title(f"Olá, {st.session_state.user_nome.split()[0]}!")
opcoes = ["🏋️ Treinar Agora", "📝 Montar Treino", "⚙️ Biblioteca"]
if st.session_state.user_nivel == 'admin':
    opcoes.append("🛡️ Gestão de Usuários")

menu = st.sidebar.radio("Ir para:", opcoes)

# --- 3. BIBLIOTECA DE EXERCÍCIOS (COM IMAGEM) ---
elif menu == "⚙️ Biblioteca":
    st.header("📚 Biblioteca de Exercícios")
    
    with st.expander("➕ Cadastrar Novo Exercício", expanded=False):
        with st.form("form_lib", clear_on_submit=True):
            n_ex = st.text_input("Nome do Exercício (Ex: Supino Reto)")
            g_ex = st.selectbox("Grupo Muscular", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen", "Cardio", "Alongamento"])
            url_img = st.text_input("URL da Imagem de Execução (opcional)", 
                                    placeholder="Ex: https://exemplo.com/supino.jpg")
            
            if st.form_submit_button("Salvar Exercício"):
                if n_ex:
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) 
                                VALUES (:n, :g, :url)
                            """), {"n": n_ex, "g": g_ex, "url": url_img if url_img else None})
                        st.success("Exercício salvo na biblioteca!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else: st.error("O nome do exercício é obrigatório.")

    st.divider()
    st.subheader("Exercícios Cadastrados")
    
    # Exibe os exercícios com a imagem
    try:
        df_exs = pd.read_sql("SELECT id, nome, grupo_muscular, url_imagem FROM exercicios_biblioteca ORDER BY nome", engine)
        if not df_exs.empty:
            for idx, row in df_exs.iterrows():
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    if row['url_imagem']:
                        st.image(row['url_imagem'], width=100)
                    else:
                        st.image("https://via.placeholder.com/100?text=Sem+Imagem", width=100) # Imagem placeholder
                with col_info:
                    st.markdown(f"**{row['nome']}**")
                    st.text(f"Grupo: {row['grupo_muscular']}")
                    if st.button(f"Excluir {row['nome']}", key=f"del_ex_{row['id']}"):
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM exercicios_biblioteca WHERE id = :id"), {"id": row['id']})
                        st.success(f"Exercício '{row['nome']}' excluído.")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("Nenhum exercício cadastrado ainda. Use o formulário acima para adicionar.")
    except Exception as e:
        st.error(f"Erro ao carregar exercícios: {e}")

# --- 1. TREINAR AGORA ---
if menu == "🏋️ Treinar Agora":
    st.header("🚀 Meu Treino")
    
    # Validação de data
    check_venc = pd.read_sql(text("SELECT MIN(data_vencimento) as v FROM fichas_treino WHERE usuario_id = :u"), 
                             engine, params={"u": st.session_state.user_id})
    
    if not check_venc.empty and check_venc.iloc[0]['v']:
        venc = pd.to_datetime(check_venc.iloc[0]['v']).date()
        hoje = datetime.now().date()
        if venc < hoje:
            st.error(f"🚨 Sua ficha venceu em {venc.strftime('%d/%m/%Y')}. Peça uma nova!")
        elif (venc - hoje).days <= 7:
            st.warning(f"⚠️ Atenção: Sua ficha vence em {(venc - hoje).days} dias.")

    t_sel = st.selectbox("Escolha o treino:", ["Treino A", "Treino B", "Treino C", "Treino D"])
    query = text("""
        SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.grupo_muscular 
        FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
        WHERE f.usuario_id = :u AND f.treino_nome = :t
    """)
    df_t = pd.read_sql(query, engine, params={"u": st.session_state.user_id, "t": t_sel})
    
    for _, row in df_t.iterrows():
        st.info(f"**{row['nome']}** | {row['series']}x{row['repeticoes']} | Carga: {row['carga_atual']}kg")

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
        
        if st.form_submit_button("Adicionar"):
            id_a = alunos[alunos['nome'] == aluno_id]['id'].values[0]
            id_e = exs[exs['nome'] == ex_nome]['id'].values[0]
            dt_venc = datetime.now().date() + timedelta(days=dias)
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, data_vencimento)
                    VALUES (:u, :t, :e, :s, :r, :v)
                """), {"u": int(id_a), "t": t_nome, "e": int(id_e), "s": ser, "r": rep, "v": dt_venc})
            st.success("Adicionado!")

# --- 4. GESTÃO DE USUÁRIOS (ADMIN) ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("👥 Cadastro de Alunos")
    with st.form("cad"):
        n = st.text_input("Nome Completo")
        em = st.text_input("Email")
        us = st.text_input("Username (nome.sobrenome)")
        se = st.text_input("Senha")
        if st.form_submit_button("Salvar e Notificar"):
            us_l = us.lower().strip().replace(" ", ".")
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :em, :u, :s, 'user')"),
                             {"n":n, "em":em, "u":us_l, "s":se})
            if enviar_email_cadastro(n, em, us_l, se):
                st.success("Aluno cadastrado e e-mail enviado!")
            else: st.warning("Cadastrado, mas o e-mail falhou.")
