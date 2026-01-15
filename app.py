import io
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
import time
import plotly.express as px

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="SGF Treino Elite", layout="wide", page_icon="💪")

@st.cache_resource
def get_engine():
    creds = st.secrets["connections"]["postgresql"]
    url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

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

with st.sidebar:
    st.title("SGF Elite")
    st.write(f"👤 {st.session_state.user_nome}")
    
    # Lista de menus baseada no nível de acesso
    opcoes_menu = ["🏋️ Treinar Agora", "📊 Relatórios"]
    
    # SÓ ADICIONA "TREINOS" SE FOR ADMIN
    if st.session_state.user_nivel == "admin":
        opcoes_menu.insert(1, "⚙️ Treinos")
    
    menu = st.radio("Navegação", opcoes_menu)
    
    st.divider()
    
    # --- BOTÃO DE SAIR REAL (FORA DA SELEÇÃO) ---
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- LÓGICA DE EXIBIÇÃO ---

# 1. GESTÃO DE TREINOS (PROTEGIDA)
if menu == "⚙️ Treinos":
    if st.session_state.user_nivel != "admin":
        st.error("Acesso negado. Esta área é apenas para professores.")
        st.stop()
    
    st.header("⚙️ Gestão de Treinos")
    tab_montar, tab_editar = st.tabs(["🆕 Montar Novo Treino", "✏️ Editar/Reordenar Treinos"])
    # ... (restante do código das abas que já tens)
    with tab_montar:
        st.subheader("📝 Prescrever Treino")
        st.cache_data.clear()
        
        alunos = pd.read_sql(text("SELECT id, nome FROM usuarios WHERE nivel = 'user' ORDER BY nome"), engine)
        bib = pd.read_sql(text("SELECT id, nome FROM exercicios_biblioteca ORDER BY nome"), engine)
        
        c_al, c_tr = st.columns(2)
        al_sel = c_al.selectbox("Aluno:", alunos['nome'].tolist(), key="n_al")
        id_al = int(alunos[alunos['nome'] == al_sel]['id'].values[0])
        tr_sel = c_tr.selectbox("Ficha:", ["Treino A", "Treino B", "Treino C", "Treino D", "Treino E"], key="n_tr")

        # Grupos Musculares
        if 'lista_grupos_ficha' not in st.session_state: st.session_state.lista_grupos_ficha = ["Peito"]
        grupos_disponiveis = ["Peito", "Costas", "Pernas", "Ombros", "Bíceps", "Tríceps", "Abdomen", "Cardio", "Glúteos", "Antebraço"]

        for i, grupo_atual in enumerate(st.session_state.lista_grupos_ficha):
            st.session_state.lista_grupos_ficha[i] = st.selectbox(f"Grupo {i+1}", grupos_disponiveis, key=f"g_{i}")

        c_b1, c_b2, _ = st.columns([1, 1, 2])
        if c_b1.button("➕ Adicionar Grupo"): 
            st.session_state.lista_grupos_ficha.append("Peito")
            st.rerun()
        if c_b2.button("🗑️ Remover Último") and len(st.session_state.lista_grupos_ficha) > 1:
            st.session_state.lista_grupos_ficha.pop()
            st.rerun()

        with st.container(border=True):
            ex1 = st.selectbox("1. Exercício Principal:", bib['nome'].tolist(), key="ex1")
            ex2_chk = st.selectbox("2. Bi-set?", ["Não", "Sim"], key="ex2_c")
            ex2 = st.selectbox("Selecione o segundo:", bib['nome'].tolist(), key="ex2") if ex2_chk == "Sim" else None
            
            # Linha de comandos (Séries, Reps, etc)
            c_tp, c_sr, c_rp, c_ds, c_cg = st.columns([1.5, 0.8, 2, 0.8, 0.8])
            tipo_m = c_tp.selectbox("Tipo", ["Reps", "Tempo", "Pirâmide"], key="tm")
            series = c_sr.number_input("Séries", 1, 12, 3)
            reps = c_rp.text_input("Reps/Tempo", "12")
            desc = c_ds.number_input("Desc.", 0, 300, 60)
            carga = c_cg.text_input("Kg", "10")

            if st.button("✅ SALVAR NA FICHA", type="primary", use_container_width=True):
                id_ex1 = int(bib[bib['nome'] == ex1]['id'].values[0])
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO fichas_treino (usuario_id, treino_nome, exercicio_id, series, repeticoes, carga_atual, tempo_descanso, tipo_meta, exercicio_combinado_id) VALUES (:u, :t, :e, :s, :r, :cg, :td, :tm, :cb)"),
                                {"u": id_al, "t": tr_sel, "e": id_ex1, "s": series, "r": reps, "cg": carga, "td": desc, "tm": tipo_m, "cb": ex2})
                st.success("Salvo!")
                st.rerun()

    with tab_editar:
        st.subheader("✏️ Editar ou Reordenar")
        al_ed = st.selectbox("Aluno para gerir:", alunos['nome'].tolist(), key="ed_al")
        id_ed = int(alunos[alunos['nome'] == al_ed]['id'].values[0])
        
        df_tr_ed = pd.read_sql(text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u"), engine, params={"u": id_ed})
        if not df_tr_ed.empty:
            tr_ed = st.selectbox("Ficha:", df_tr_ed['treino_nome'].tolist(), key="ed_tr")
            df_f = pd.read_sql(text("SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, f.ordem FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.ordem ASC, f.id ASC"), engine, params={"u":id_ed, "t":tr_ed})
            
            with st.form("ed_lote"):
                upds = []
                for _, r in df_f.iterrows():
                    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
                    with c1: st.write(f"**{r['nome']}**")
                    with c2: o = st.number_input("Ordem", value=int(r['ordem']), key=f"o{r['id']}")
                    with c3: rp = st.text_input("Reps", value=r['repeticoes'], key=f"r{r['id']}")
                    with c4: cg = st.number_input("Kg", value=int(r['carga_atual']), key=f"k{r['id']}")
                    with c5: d = st.checkbox("🗑️", key=f"d{r['id']}")
                    upds.append({"id": r['id'], "o": o, "r": rp, "k": cg, "d": d})
                
                if st.form_submit_button("💾 SALVAR ALTERAÇÕES"):
                    with engine.begin() as conn:
                        for i in upds:
                            if i['d']: conn.execute(text("DELETE FROM fichas_treino WHERE id = :id"), {"id": i['id']})
                            else: conn.execute(text("UPDATE fichas_treino SET ordem=:o, repeticoes=:r, carga_atual=:c WHERE id=:id"), {"o":i['o'], "r":i['r'], "c":i['k'], "id":i['id']})
                    st.rerun()

# --- 🏋️ TREINAR AGORA (ALUNO) ---
elif menu == "🏋️ Treinar Agora":
    df_t = pd.read_sql(text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u"), engine, params={"u": st.session_state.user_id})
    if df_t.empty: st.warning("Sem fichas.")
    else:
        t_sel = st.selectbox("Escolha o Treino:", df_t['treino_nome'].tolist())
        df_ex = pd.read_sql(text("SELECT f.*, e.nome, e.url_imagem FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id WHERE f.usuario_id = :u AND f.treino_nome = :t ORDER BY f.ordem ASC, f.id ASC"), engine, params={"u": st.session_state.user_id, "t": t_sel})
        
        if not df_ex.empty:
            with st.expander("📲 Exportar treino"):
                txt = f"TREINO: {t_sel}\n" + "\n".join([f"{r['nome']} - {r['series']}x{r['repeticoes']}" for _, r in df_ex.iterrows()])
                st.components.v1.html(f'<button onclick="navigator.clipboard.writeText(\'{txt.encode("unicode_escape").decode()}\'); alert(\'Copiado!\')" style="width:100%; padding:10px; background:#25D366; color:white; border:none; border-radius:5px; cursor:pointer;">📋 COPIAR TREINO</button>', height=50)
                st.text(txt)

        st.divider()
        if st.button("🚀 INICIAR TREINO" if 'iniciado' not in st.session_state else "🏁 FINALIZAR"):
            st.session_state.iniciado = True
            st.rerun()

        for _, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                c1.image(row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150")
                c2.subheader(row['nome'])
                c2.write(f"🎯 {row['series']}x {row['repeticoes']} | ⚖️ {row['carga_atual']}kg")

# --- OUTROS MENUS ---
elif menu == "📊 Relatórios":
    st.title("📈 Relatórios em breve")
