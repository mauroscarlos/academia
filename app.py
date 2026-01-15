import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
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

# --- LOGIN (Simplificado para o exemplo, mantenha o seu original) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

# ... (Mantenha seu bloco de login aqui) ...

if st.session_state.logado:
    # --- BARRA LATERAL: MEUS TREINOS ---
    st.sidebar.title(f"👋 Olá, {st.session_state.user_nome.split()[0]}")
    
    # Busca os nomes dos treinos que o aluno possui
    query_treinos = text("SELECT DISTINCT treino_nome FROM fichas_treino WHERE usuario_id = :u")
    meus_treinos = pd.read_sql(query_treinos, engine, params={"u": st.session_state.user_id})['treino_nome'].tolist()
    
    st.sidebar.markdown("### 📋 Meus Treinos")
    treino_selecionado = st.sidebar.radio("Selecione para treinar:", ["Dashboard"] + meus_treinos)
    
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # --- DASHBOARD DE EVOLUÇÃO ---
    if treino_selecionado == "Dashboard":
        st.title("📊 Minha Evolução")
        col1, col2 = st.columns(2)
        
        # Simulação de dados para o gráfico (Pode ser expandido com tabela de histórico futuramente)
        dados_evolucao = pd.DataFrame({
            'Data': pd.date_range(start='2025-12-01', periods=10, freq='D'),
            'Volume de Carga (kg)': [1200, 1250, 1220, 1300, 1350, 1320, 1400, 1450, 1480, 1550]
        })
        
        with col1:
            fig = px.line(dados_evolucao, x='Data', y='Volume de Carga (kg)', title='Evolução de Carga Total')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig2 = px.bar(dados_evolucao, x='Data', y='Volume de Carga (kg)', title='Consistência Diária')
            st.plotly_chart(fig2, use_container_width=True)

        

    # --- ÁREA DE TREINO ---
    else:
        st.title(f"💪 {treino_selecionado}")
        
        query = text("""
            SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, f.tempo_descanso
            FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t
        """)
        df_t = pd.read_sql(query, engine, params={"u": st.session_state.user_id, "t": treino_selecionado})
        
        for idx, row in df_t.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    img = row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150"
                    st.image(img, use_container_width=True)
                with c2:
                    st.subheader(row['nome'])
                    st.write(f"**{row['series']} séries x {row['repeticoes']} reps**")
                    st.write(f"Carga prescrita: **{row['carga_atual']} kg**")
                    
                    # --- CRONÔMETRO DE DESCANSO ---
                    if st.button(f"⏱️ Iniciar Descanso ({row['tempo_descanso']}s)", key=f"btn_{row['id']}"):
                        tempo = row['tempo_descanso']
                        placeholder = st.empty()
                        while tempo > 0:
                            placeholder.metric("Descanse!", f"{tempo}s")
                            time.sleep(1)
                            tempo -= 1
                        placeholder.success("🔥 Próxima série!")
                        st.balloons()
            st.divider()

    # --- ABA ADMIN: MONTAR TREINO (Ajustada para incluir descanso) ---
    if st.session_state.user_nivel == 'admin' and "📝 Montar Treino" in opcoes:
        # No seu form de montagem de treino, adicione:
        # tempo_d = st.number_input("Descanso (segundos)", value=60)
        # E inclua no INSERT: tempo_descanso = :td
        pass
