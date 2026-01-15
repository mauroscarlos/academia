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
    # --- TROQUE PELO LINK DO SEU APP NO STREAMLIT CLOUD ---
    url_sistema = "https://seu-app-de-treino.streamlit.app/" 
    
    corpo = f"""
    <html>
        <body style="font-family: sans-serif; line-height: 1.6;">
            <h3 style="color: #ff4b4b;">Olá, {nome}! 💪</h3>
            <p>Seu acesso ao <b>SGF Treino Elite</b> foi criado com sucesso.</p>
            <p>Agora você pode acompanhar suas fichas, marcar tempos de descanso e ver sua evolução.</p>
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ddd;">
                <b>Seus dados de login:</b><br>
                🔗 <b>Link de Acesso:</b> <a href="{url_sistema}">{url_sistema}</a><br>
                👤 <b>Usuário:</b> <code>{username}</code><br>
                🔑 <b>Senha:</b> <code>{senha}</code>
            </div>
            <p>Bons treinos!</p>
            <hr style="border: 0; border-top: 1px solid #eee;">
            <small>Este é um e-mail automático, por favor não responda.</small>
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

# BOTÃO SAIR NO "RODAPÉ" DA LATERAL
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
            st.success(f"⏱️ Tempo: {str(tempo_atual).split('.')[0]}")
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
        ids_segundos = df_ex['exercicio_combinado_id'].dropna().tolist()

        for idx, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1: st.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150", use_container_width=True)
                with c2:
                    if row['exercicio_combinado_id']: st.caption("🔗 COMBINADO COM ANTERIOR (BI-SET)")
                    st.subheader(row['nome'])
                    st.write(f"🎯 **{row['series']}x {row['repeticoes']}** | {row['carga_atual']}kg")
                    if row['observacao']: st.info(f"💡 {row['observacao']}")
                    if st.session_state.get('treino_andamento'):
                        if row['id'] in ids_segundos:
                            st.error("🚫 SEM DESCANSO! Vá para o próximo.")
                        else:
                            if st.button(f"⏱️ Descanso {row['tempo_descanso']}s", key=f"d_{row['id']}"):
                                p = st.empty()
                                for t in range(int(row['tempo_descanso']), -1, -1):
                                    p.metric("Descanso", f"{t}s"); time.sleep(1)
                                p.success("VAI!")

# --- 3. MONTAR TREINO
elif menu == "📝 Montar Treino":
    st.header("📝 Prescrever Treino")
    
    # 1. Carregamento de dados base (sempre fresco)
    alunos = pd.read_sql("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome", engine)
    exs_biblioteca = pd.read_sql("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome", engine)
    
    if 'form_count' not in st.session_state: 
        st.session_state.form_count = 0

    # Seletores fora do form para garantir reatividade
    c_al, c_tr = st.columns(2)
    aluno_sel = c_al.selectbox("Selecione o Aluno:", alunos['nome'].tolist(), key="sel_aluno_montar")
    id_aluno = alunos[alunos['nome'] == aluno_sel]['id'].values[0]
    t_nome = c_tr.selectbox("Selecione o Treino:", ["Treino A", "Treino B", "Treino C", "Treino D"], key="sel_treino_montar")

    # 2. BUSCA EXERCÍCIOS JÁ LANÇADOS (Crucial para o Bi-set)
    # Usamos query directa para garantir que o exercício acabado de inserir apareça
    with engine.connect() as conn:
        query_bi = text("""
            SELECT f.id, e.nome 
            FROM fichas_treino f 
            JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t
            ORDER BY f.id DESC
        """)
        atuais_na_ficha = pd.read_sql(query_bi, conn, params={"u": int(id_aluno), "t": t_nome})

    # 3. FORMULÁRIO DE CADASTRO
    # A key do form muda a cada inserção (st.session_state.form_count) para resetar os campos
    with st.form(key=f"form_montagem_{id_aluno}_{t_nome}_{st.session_state.form_count}"):
        st.subheader(f"Adicionar ao {t_nome}")
        
        ex_sel = st.selectbox("1. Escolha o Exercício (da Biblioteca):", exs_biblioteca['nome'].tolist())
        
        # LISTA DE COMBINAÇÃO: Agora ela lê directamente o que 'atuais_na_ficha' encontrou
        lista_combinar = ["Não"] + atuais_na_ficha['nome'].tolist()
        combinar = st.selectbox("2. Combinar com algum exercício já na ficha?", lista_combinar)
        
        c1, c2, c3 = st.columns(3)
        tipo = c1.selectbox("Tipo de Meta", ["Repetições", "Tempo (s)", "Pirâmide"])
        rep = c2.text_input("Meta (ex: 12-10-8 ou 45s)", "12")
        ser = c3.number_input("Séries", 1, 10, 3)
        
        col_c, col_d = st.columns(2)
        cg = col_c.text_input("Carga (kg)", "10")
        desc = col_d.number_input("Descanso (s)", 0, 300, 60)
        
        obs = st.text_area("Observações (opcional)")
        
        if st.form_submit_button("✅ Gravar Exercício"):
            id_ex_base = exs_biblioteca[exs_biblioteca['nome'] == ex_sel]['id'].values[0]
            
            # Lógica para pegar o ID correcto da ficha para o Bi-set
            id_comb_ficha = None
            if combinar != "Não":
                # Selecionamos o ID do exercício que já está na ficha
                id_comb_ficha = int(atuais_na_ficha[atuais_na_ficha['nome'] == combinar]['id'].iloc[0])
            
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, observacao, exercicio_combinado_id)
                        VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :ob, :cb)
                    """), {
                        "u": int(id_aluno), "t": t_nome, "e": int(id_ex_base), "s": ser, "r": rep, 
                        "cg": cg, "td": desc, "tm": tipo, "ob": obs, "cb": id_comb_ficha
                    })
                
                st.success(f"Sucesso! '{ex_sel}' adicionado.")
                st.session_state.form_count += 1  # Força o reset do form
                time.sleep(0.5)
                st.rerun() # Recarrega a página para actualizar a lista de combinação
            except Exception as e:
                st.error(f"Erro ao gravar: {e}")

    # 4. TABELA DE VISUALIZAÇÃO (Para você ver a ficha a ser montada em tempo real)
    st.divider()
    st.subheader(f"📋 Exercícios actuais no {t_nome}")
    if not atuais_na_ficha.empty:
        # Mostra o que já está na ficha para dar segurança ao treinador
        st.table(atuais_na_ficha[['nome']])
    else:
        st.info("Nenhum exercício lançado para este treino.")

    # 4. TABELA DE CONFERÊNCIA (Opcional, mas ajuda muito)
    st.divider()
    st.subheader(f"📋 Resumo do {t_nome}")
    if not atuais_na_ficha.empty:
        st.dataframe(atuais_na_ficha[['nome']], use_container_width=True)
    else:
        st.info("Nenhum exercício neste treino ainda.")

# --- 4. BIBLIOTECA ---
elif menu == "⚙️ Biblioteca":
    st.header("⚙️ Biblioteca de Exercícios")
    
    # Formulário de Cadastro
    with st.form("lib", clear_on_submit=True):
        n = st.text_input("Nome do Exercício")
        g = st.selectbox("Grupo Muscular", ["Peito", "Costas", "Pernas", "Ombros", "Braços", "Abdomen"])
        u = st.text_input("URL da Imagem/GIF")
        
        if st.form_submit_button("Cadastrar Exercício"):
            if n:
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO exercicios_biblioteca (nome, grupo_muscular, url_imagem) VALUES (:n, :g, :u)"), 
                                 {"n":n, "g":g, "u":u})
                st.success(f"Exercício '{n}' salvo com sucesso!")
                time.sleep(1)
                st.rerun() # Isso força a atualização da lista em todas as abas
            else:
                st.error("O nome do exercício é obrigatório.")

    st.divider()
    st.subheader("Exercícios Cadastrados")
    
    # Busca e exibe a tabela de exercícios
    df_biblioteca = pd.read_sql("SELECT nome, grupo_muscular as grupo FROM exercicios_biblioteca ORDER BY nome", engine)
    st.dataframe(df_biblioteca, use_container_width=True)

# --- 5. GESTÃO DE USUÁRIOS ---
elif menu == "🛡️ Gestão de Usuários":
    st.header("🛡️ Gestão de Alunos")
    with st.form("cad_user", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        email = st.text_input("Email")
        username = st.text_input("Usuário (nome.sobrenome)")
        senha = st.text_input("Senha Temporária")
        if st.form_submit_button("Cadastrar e Notificar"):
            u_limpo = username.lower().strip().replace(" ", ".")
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO usuarios (nome, email, username, senha, nivel) VALUES (:n, :e, :u, :s, 'user')"),
                             {"n":nome, "e":email, "u":u_limpo, "s":senha})
            enviar_email_cadastro(nome, email, u_limpo, senha)
            st.success(f"Aluno {nome} cadastrado!")

    st.divider()
    st.subheader("Lista de Alunos")
    df_users = pd.read_sql("SELECT nome, email, username FROM usuarios WHERE nivel = 'user'", engine)
    st.dataframe(df_users, use_container_width=True)
