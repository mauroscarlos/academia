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
    corpo = f"<html><body><h3>Olá, {nome}! 💪</h3><p>Link: <a href='{url_sistema}'>{url_sistema}</a><br>User: {username}<br>Senha: {senha}</p></body></html>"
    try:
        msg = MIMEMultipart(); msg['From'] = st.secrets["email"]["usuario"]; msg['To'] = email_destino; msg['Subject'] = "🏋️ Acesso SGF Treino"
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
if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear(); st.rerun()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📈 Evolução")
    df_logs = pd.read_sql(text("SELECT data_execucao, duracao_minutos, treino_nome FROM logs_treino WHERE usuario_id = :u ORDER BY data_execucao ASC"), engine, params={"u": st.session_state.user_id})
    if not df_logs.empty:
        st.plotly_chart(px.line(df_logs, x="data_execucao", y="duracao_minutos", title="Tempo por Treino (min)"), use_container_width=True)
    else: st.info("Sem treinos registrados para este perfil ainda.")

# --- 2. TREINAR AGORA ---
elif menu == "🏋️ Treinar Agora":
    query_meus_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
    meus_treinos = pd.read_sql(query_meus_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()
    
    if not meus_treinos:
        st.warning("Nenhuma ficha cadastrada.")
    else:
        t_sel = st.selectbox("Escolha o Treino:", meus_treinos)
        if 'treino_andamento' not in st.session_state: st.session_state.treino_andamento = False
        
        if not st.session_state.treino_andamento:
            if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
                st.session_state.treino_andamento = True; st.session_state.inicio_t = datetime.now(); st.rerun()
        else:
            tempo = datetime.now() - st.session_state.inicio_t
            st.success(f"⏱️ Tempo: {str(tempo).split('.')[0]}")
            if st.button("🏁 FINALIZAR TREINO", use_container_width=True):
                minutos = int(tempo.total_seconds() / 60)
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"), {"u": st.session_state.user_id, "t": t_sel, "d": minutos})
                st.session_state.treino_andamento = False; st.balloons(); time.sleep(1); st.rerun()

        df_ex = pd.read_sql(text("SELECT f.*, e.nome, e.url_imagem FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC"), engine, params={"u": st.session_state.user_id, "t": t_sel})
        nomes_no_par = df_ex['exercicio_combinado_id'].dropna().unique().tolist()

        for _, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    st.subheader(row['nome'])
                    if row['exercicio_combinado_id']: st.caption(f"🔗 BI-SET COM: {row['exercicio_combinado_id']}")
                    st.write(f"🎯 {row['series']}x {row['repeticoes']} | ⚖️ {row['carga_atual']}kg")
                    if st.session_state.get('treino_andamento'):
                        if row['nome'] in nomes_no_par:
                            st.error("🚫 SEM DESCANSO! Vá para o próximo.")
                        else:
                            if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                                p = st.empty()
                                for t in range(int(row['tempo_descanso']), -1, -1):
                                    p.metric("Descanso", f"{t}s"); time.sleep(1)
                                p.success("VAI!")

# --- 3. MONTAR TREINO ---
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever Treino")
    st.cache_data.clear()
    alunos_df = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    bib_df = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    col_al, col_tr = st.columns(2)
    al_sel = col_al.selectbox("Aluno:", alunos_df['nome'].tolist())
    id_al = int(alunos_df[alunos_df['nome'] == al_sel]['id'].values[0])
    tr_sel = col_tr.selectbox("Treino:", ["Treino A", "Treino B", "Treino C", "Treino D"])

    lista_bib = bib_df['nome'].tolist()
    if 'form_token' not in st.session_state: st.session_state.form_token = 0

    with st.container(border=True):
        ex_p = st.selectbox("1. Exercício Principal:", lista_bib, key=f"ex_{st.session_state.form_token}")
        comb = st.selectbox("2. Combinar com (Bi-set):", ["Não"] + lista_bib, key=f"cb_{st.session_state.form_token}")
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("Tipo", ["Repetições", "Tempo (s)", "Pirâmide"], key=f"tp_{st.session_state.form_token}")
        meta = c2.text_input("Reps/Meta", "12", key=f"mt_{st.session_state.form_token}")
        ser = c3.number_input("Séries", 1, 10, 3, key=f"sr_{st.session_state.form_token}")
        cg = st.text_input("Carga (kg)", "10", key=f"cg_{st.session_state.form_token}")
        ds = st.number_input("Descanso (s)", 0, 300, 60, key=f"ds_{st.session_state.form_token}")
        ob = st.text_area("Observações", key=f"ob_{st.session_state.form_token}")
        
        if st.button("✅ ADICIONAR À FICHA", use_container_width=True, type="primary"):
            id_ex = int(bib_df[bib_df['nome'] == ex_p]['id'].values[0])
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao, exercicio_combinado_id) VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :ob, :cb)"),
                             {"u": id_al, "t": tr_sel, "e": id_ex, "s": ser, "r": meta, "cg": cg, "td": ds, "tm": tipo, "ob": ob, "cb": comb if comb != "Não" else None})
            st.session_state.form_token += 1; st.rerun()

    st.divider()
    df_f = pd.read_sql(text("SELECT f.id, e.nome, f.repeticoes, f.exercicio_combinado_id FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC"), engine, params={"u": id_al, "t": tr_sel})
    if not df_f.empty:
        for _, r in df_f.iterrows():
            c1, c2 = st.columns([4, 1])
            txt = f"🔹 **{r['nome']}** - {r['repeticoes']} reps"
            if r['exercicio_combinado_id']: txt += f" (Par: {r['exercicio_combinado_id']})"
            c1.write(txt)
            if c2.button("🗑️", key=f"del_{r['id']}"):
                with engine.begin() as conn: conn.execute(text("DELETE FROM fichas_treino WHERE id = :id"), {"id": r['id']})
                st.rerun()
        if st.button("🔥 EXCLUIR TREINO COMPLETO"):
            with engine.begin() as conn: conn.execute(text("DELETE FROM fichas_treino WHERE usuario_id = :u AND treino_nome = :t"), {"u": id_al, "t": tr_sel})
            st.rerun()

# --- 4. BIBLIOTECA ---
elif menu == "⚙️ Biblioteca":
    st.header("⚙️ Biblioteca")
    with st.form("bib_f", clear_on_submit=True):
        n = st.text_input("Nome"); g = st.selectbox("Grupo", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"]); u = st.text_input("URL Imagem")
        if st.form_submit_button("Cadastrar"):
            with engine.begin() as conn: conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :u)"), {"n":n, "g":g, "u":u})
            st.success("Salvo!"); time.sleep(1); st.rerun()
    df_b = pd.read_sql("SELECT nome, grupo_muscular FROM exercicios_biblioteca ORDER BY nome", engine); st.dataframe(df_b, use_container_width=True)

# --- 5. GESTÃO DE USUÁRIOS ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("🛡️ Gestão de Alunos")
    with st.form("u_f", clear_on_submit=True):
        nome, email, user, senha = st.text_input("Nome"), st.text_input("Email"), st.text_input("Usuário"), st.text_input("Senha")
        if st.form_submit_button("Cadastrar Aluno"):
            u_l = user.lower().strip().replace(" ", ".")
            with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :e, :u, :s, 'user')"), {"n":nome, "e":email, "u":u_l, "s":senha})
            enviar_email_cadastro(nome, email, u_l, senha); st.success("Cadastrado com sucesso!")
    st.dataframe(pd.read_sql("SELECT nome, email, username FROM usuarios WHERE nivel = 'user'", engine), use_container_width=True)import streamlit as st
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
