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
    corpo = f"""
    <html>
        <body style="font-family: sans-serif; line-height: 1.6;">
            <h3 style="color: #ff4b4b;">Olá, {nome}! 💪</h3>
            <p>Seu acesso ao <b>SGF Treino Elite</b> foi criado com sucesso.</p>
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ddd;">
                <b>Seus dados de login:</b><br>
                🔗 <b>Link:</b> <a href="{url_sistema}">{url_sistema}</a><br>
                👤 <b>Usuário:</b> <code>{username}</code><br>
                🔑 <b>Senha:</b> <code>{senha}</code>
            </div>
            <p>Bons treinos!</p>
        </body>
    </html>
    """
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
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

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

# --- BARRA LATERAL ---
st.sidebar.title(f"👋 {st.session_state.user_nome.split()[0]}")
opcoes = ["📊 Dashboard", "🏋️ Treinar Agora"]
if st.session_state.user_nivel == 'admin':
    opcoes.extend(["📝 Montar Treino", "⚙️ Biblioteca", "🛡️ Gestão de Usuários"])

menu = st.sidebar.radio("Navegação:", opcoes)

st.sidebar.divider()
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
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
        st.warning("Nenhuma ficha encontrada.")
    else:
        t_sel = st.selectbox("Selecione o Treino:", meus_treinos)
        
        if 'treino_andamento' not in st.session_state: st.session_state.treino_andamento = False
        
        if not st.session_state.treino_andamento:
            if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
                st.session_state.treino_andamento = True
                st.session_state.inicio_t = datetime.now()
                st.rerun()
        else:
            tempo_atual = datetime.now() - st.session_state.inicio_t
            st.success(f"⏱️ Tempo de Treino: {str(tempo_atual).split('.')[0]}")
            if st.button("🏁 FINALIZAR TREINO", use_container_width=True):
                minutos = int(tempo_atual.total_seconds() / 60)
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos) VALUES (:u, :t, :d)"),
                                 {"u": st.session_state.user_id, "t": t_sel, "d": minutos})
                st.session_state.treino_andamento = False
                st.success(f"Treino salvo! Duração: {minutos} min")
                st.balloons(); time.sleep(2); st.rerun()

        query_ex = text("""
            SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, 
                   f.tempo_descanso, f.tipo_meta, f.observacao, f.exercicio_combinado_id
            FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC
        """)
        df_ex = pd.read_sql(query_ex, engine, params={"u": st.session_state.user_id, "t": t_sel})
        
        # Lógica Bi-set: Identifica quem é o primeiro da dupla
        nomes_que_tem_combinado = df_ex['exercicio_combinado_id'].dropna().unique().tolist()

        for idx, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    is_primeiro = row['nome'] in nomes_que_tem_combinado
                    is_segundo = row['exercicio_combinado_id'] is not None and row['exercicio_combinado_id'] != "Não"
                    
                    if is_segundo: st.caption(f"🔗 COMBINADO COM: {row['exercicio_combinado_id']}")
                    st.subheader(row['nome'])
                    st.write(f"🎯 **{row['series']}x {row['repeticoes']}** ({row['tipo_meta']}) | ⚖️ {row['carga_atual']}kg")
                    if row['observacao']: st.info(f"💡 {row['observacao']}")
                    
                    if st.session_state.get('treino_andamento'):
                        if is_primeiro:
                            st.error("🚫 SEM DESCANSO! Vá direto para o próximo.")
                        else:
                            if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                                p = st.empty()
                                for t in range(int(row['tempo_descanso']), -1, -1):
                                    p.metric("Descanso", f"{t}s"); time.sleep(1)
                                p.success("VAI!")

# --- 3. MONTAR TREINO
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever e Editar Treino")
    
    # 1. Dados Base
    st.cache_data.clear()
    alunos_df = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    biblioteca_df = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    col_al, col_tr = st.columns(2)
    aluno_escolhido = col_al.selectbox("Selecione o Aluno:", alunos_df['nome'].tolist())
    id_aluno_atual = int(alunos_df[alunos_df['nome'] == aluno_escolhido]['id'].values[0])
    nome_do_treino = col_tr.selectbox("Selecione o Treino:", ["Treino A", "Treino B", "Treino C", "Treino D"])

    # 2. Preparamos as listas IGUAIS (Ambas com tudo da biblioteca)
    lista_completa = biblioteca_df['nome'].tolist()
    lista_combinar = ["Não"] + lista_completa

    # 3. CONTAINER DE CADASTRO
    if 'form_token' not in st.session_state: st.session_state.form_token = 0

    with st.container(border=True):
        st.subheader(f"Adicionar Exercício")
        
        # AQUI AS DUAS LISTAS VOLTAM A APARECER COMPLETAS!
        ex_principal = st.selectbox("1. Exercício Principal:", lista_completa, key=f"ex_{st.session_state.form_token}")
        combinar_com = st.selectbox("2. Combinar com (Bi-set):", lista_combinar, key=f"comb_{st.session_state.form_token}")
        
        c1, c2, c3 = st.columns(3)
        tipo_m = c1.selectbox("Tipo de Meta", ["Repetições", "Tempo (s)", "Pirâmide"], key=f"tipo_{st.session_state.form_token}")
        meta_v = st.text_input("Meta/Reps (ex: 12 ou 10-8-6)", "12", key=f"meta_{st.session_state.form_token}")
        series_v = st.number_input("Séries", 1, 10, 3, key=f"ser_{st.session_state.form_token}")
        
        col_cg, col_ds = st.columns(2)
        carga_v = col_cg.text_input("Carga (kg)", "10", key=f"cg_{st.session_state.form_token}")
        desc_v = col_ds.number_input("Descanso (s)", 0, 300, 60, key=f"desc_{st.session_state.form_token}")
        
        obs_v = st.text_area("Observações (Ex: 'Fazer até a falha')", key=f"obs_{st.session_state.form_token}")
        
        if st.button("✅ ADICIONAR À FICHA", use_container_width=True, type="primary"):
            id_modelo = int(biblioteca_df[biblioteca_df['nome'] == ex_principal]['id'].values[0])
            
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao, exercicio_combinado_id)
                    VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :ob, :cb)
                """), {
                    "u": id_aluno_atual, "t": nome_do_treino, "e": id_modelo, 
                    "s": series_v, "r": meta_v, "cg": carga_v, "td": desc_v, 
                    "tm": tipo_m, "ob": obs_v, "cb": combinar_com if combinar_com != "Não" else None
                })
            
            st.session_state.form_token += 1
            st.success("Adicionado!")
            time.sleep(0.5)
            st.rerun()

    # 4. LISTA DE GERENCIAMENTO (ABAIXO DO FORMULÁRIO)
    st.divider()
    with engine.connect() as conn:
        df_atuais = pd.read_sql(text("""
            SELECT f.id, e.nome, f.repeticoes, f.exercicio_combinado_id 
            FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.id ASC
        """), conn, params={"u": id_aluno_atual, "t": nome_do_treino})

    st.subheader(f"📋 Resumo do {nome_do_treino}")
    if not df_atuais.empty:
        for _, r in df_atuais.iterrows():
            c1, c2 = st.columns([4, 1])
            info = f"🔹 **{r['nome']}** - {r['repeticoes']} reps"
            if r['exercicio_combinado_id']:
                info += f" 🔥 (Bi-set com: {r['exercicio_combinado_id']})"
            c1.write(info)
            if c2.button("🗑️", key=f"del_{r['id']}"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM fichas_treino WHERE id = :id"), {"id": r['id']})
                st.rerun()

# --- 4. BIBLIOTECA ---
elif menu == "⚙️ Biblioteca":
    st.header("⚙️ Biblioteca de Exercícios")
    with st.form("lib", clear_on_submit=True):
        n = st.text_input("Nome"); g = st.selectbox("Grupo", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"]); u = st.text_input("URL Imagem")
        if st.form_submit_button("Cadastrar"):
            with engine.begin() as conn: conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :u)"), {"n":n, "g":g, "u":u})
            st.success("Salvo!"); time.sleep(1); st.rerun()
    st.divider()
    df_lib = pd.read_sql("SELECT nome, grupo_muscular as grupo FROM exercicios_biblioteca ORDER BY nome", engine)
    st.dataframe(df_lib, use_container_width=True)

# --- 5. GESTÃO DE USUÁRIOS ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("🛡️ Gestão de Alunos")
    with st.form("cad_user", clear_on_submit=True):
        nome, email, user, senha = st.text_input("Nome"), st.text_input("Email"), st.text_input("Usuário"), st.text_input("Senha")
        if st.form_submit_button("Cadastrar"):
            u_limpo = user.lower().strip().replace(" ", ".")
            with engine.begin() as conn: conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :e, :u, :s, 'user')"), {"n":nome, "e":email, "u":u_limpo, "s":senha})
            enviar_email_cadastro(nome, email, u_limpo, senha)
            st.success(f"Aluno {nome} cadastrado!")
    df_u = pd.read_sql("SELECT nome, email, username FROM usuarios WHERE nivel = 'user'", engine)
    st.dataframe(df_u, use_container_width=True)
