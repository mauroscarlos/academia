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

# --- FUNÇÃO DE E-MAIL ---
def enviar_email_cadastro(nome, email_destino, username, senha):
    corpo = f"<html><body><h3>Olá, {nome}! 💪</h3><p>Seu acesso ao <b>SGF Treino</b> foi criado.</p><p>Usuário: {username}<br>Senha: {senha}</p></body></html>"
    try:
        msg = MIMEMultipart(); msg['From'] = st.secrets["email"]["usuario"]; msg['To'] = email_destino; msg['Subject'] = "🏋️ Acesso SGF Treino"
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
            else: st.error("Acesso negado.")
    st.stop()

# --- MENU LATERAL ---
st.sidebar.title(f"👋 {st.session_state.user_nome.split()[0]}")

# Define as opções baseado no nível
opcoes = ["📊 Dashboard", "🏋️ Treinar Agora"]
if st.session_state.user_nivel == 'admin':
    opcoes.extend(["📝 Montar Treino", "⚙️ Biblioteca", "🛡️ Gestão de Usuários"])

menu = st.sidebar.radio("Navegação:", opcoes)

if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📈 Evolução dos Treinos")
    query_logs = text("SELECT data_execucao, duracao_minutos, treino_nome FROM logs_treino WHERE usuario_id = :u ORDER BY data_execucao ASC")
    df_logs = pd.read_sql(query_logs, engine, params={"u": st.session_state.user_id})
    
    if not df_logs.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.line(df_logs, x="data_execucao", y="duracao_minutos", title="Tempo por Treino (min)", markers=True)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.pie(df_logs, names="treino_nome", title="Frequência por Treino")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Ainda não há logs de treino para este perfil.")

# --- 2. TREINAR AGORA ---
elif menu == "🏋️ Treinar Agora":
    query_meus_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
    meus_treinos = pd.read_sql(query_meus_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()
    
    if not meus_treinos:
        st.warning("Você ainda não tem uma ficha montada.")
    else:
        t_sel = st.selectbox("Selecione o Treino:", meus_treinos)
        
        # Cronômetro
        if 'treino_andamento' not in st.session_state: st.session_state.treino_andamento = False
        
        if not st.session_state.treino_andamento:
            if st.button("🚀 INICIAR", use_container_width=True, type="primary"):
                st.session_state.treino_andamento = True
                st.session_state.inicio_t = datetime.now()
                st.rerun()
        else:
            if st.button("🏁 FINALIZAR", use_container_width=True):
                minutos = int((datetime.now() - st.session_state.inicio_t).total_seconds() / 60)
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"),
                                 {"u": st.session_state.user_id, "t": t_sel, "d": minutos})
                st.session_state.treino_andamento = False
                st.success(f"Treino de {minutos} min salvo!")
                st.balloons(); time.sleep(2); st.rerun()

        # Exercícios
        query_ex = text("""SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, f.tempo_descanso 
                           FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
                           WHERE f.usuario_id = :u AND f.treino_nome = :t""")
        df_ex = pd.read_sql(query_ex, engine, params={"u": st.session_state.user_id, "t": t_sel})
        
        for idx, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    st.subheader(row['nome'])
                    st.write(f"**{row['series']}x{row['repeticoes']}** | Carga: {row['carga_atual']}kg")
                    if st.session_state.get('treino_andamento'):
                        if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                            p = st.empty()
                            for t in range(int(row['tempo_descanso']), -1, -1):
                                p.metric("Descanso", f"{t}s"); time.sleep(1)
                            p.success("VAI!")

# --- 3. MONTAR TREINO (ADMIN) ---
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever Treino")
    
    # Criamos um contador no session_state para resetar o form
    if 'form_reset_count' not in st.session_state:
        st.session_state.form_reset_count = 0

    alunos = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    exs = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    # A key muda toda vez que você salva, limpando tudo
    with st.form(key=f"montar_ficha_{st.session_state.form_reset_count}"):
        aluno_selecionado = st.selectbox("Aluno", alunos['nome'].tolist())
        t_nome = st.selectbox("Treino", ["Treino A", "Treino B", "Treino C", "Treino D"])
        exercicio_selecionado = st.selectbox("Exercício", exs['nome'].tolist())
        
        col1, col2, col3 = st.columns(3)
        tipo_meta = col1.selectbox("Tipo de Meta", ["Repetições", "Tempo (s)", "Pirâmide"])
        r = col2.text_input("Meta (ex: 12-10-8 ou 45s)", value="12")
        s = col3.number_input("Séries", 1, 10, 3)
        
        col_c, col_d = st.columns(2)
        cg = col_c.text_input("Carga (kg)", "10")
        desc = col_d.number_input("Descanso (segundos)", 30, 300, 60)
        
        obs = st.text_area("Observações Técnicas (ex: Postura, Drop-set, etc.)", placeholder="Dica para o aluno...")
        
        if st.form_submit_button("✅ Adicionar à Ficha"):
            id_a = alunos[alunos['nome'] == aluno_selecionado]['id'].values[0]
            id_e = exs[exs['nome'] == exercicio_selecionado]['id'].values[0]
            
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO fichas_treino 
                        (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao) 
                        VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :obs)
                    """), {
                        "u": int(id_a), "t": t_nome, "e": int(id_e), "s": s, "r": r, 
                        "cg": cg, "td": desc, "tm": tipo_meta, "obs": obs
                    })
                
                # SUCESSO: Incrementamos o contador para limpar a tela
                st.session_state.form_reset_count += 1
                st.success(f"Exercício '{exercicio_selecionado}' adicionado com sucesso!")
                time.sleep(1) # Pequena pausa para você ver a mensagem de sucesso
                st.rerun() # Recarrega a página com o form limpo
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- 4. BIBLIOTECA (ADMIN) ---
elif menu == "⚙️ Biblioteca":
    st.header("⚙️ Biblioteca de Exercícios")
    with st.form("lib"):
        nome = st.text_input("Nome")
        grupo = st.selectbox("Grupo", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"])
        url = st.text_input("URL da Imagem/GIF")
        if st.form_submit_button("Cadastrar"):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :u)"),
                             {"n":nome, "g":grupo, "u":url})
            st.success("Salvo!")

# --- 5. GESTÃO (ADMIN) ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("👥 Alunos")
    with st.form("user"):
        n = st.text_input("Nome"); em = st.text_input("Email"); us = st.text_input("Username"); se = st.text_input("Senha")
        if st.form_submit_button("Cadastrar"):
            us_l = us.lower().strip().replace(" ", ".")
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :em, :u, :s, 'user')"),
                             {"n":n, "em":em, "u":us_l, "s":se})
            enviar_email_cadastro(n, em, us_l, se)
            st.success("Cadastrado e Notificado!")
