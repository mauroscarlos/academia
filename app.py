import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import plotly.express as px

# ... (Mantenha suas funções get_engine e login como estão) ...

if st.session_state.logado:
    # --- BARRA LATERAL ---
    # (Mantenha sua lógica de busca de treinos aqui)
    # ...
    
    # --- LÓGICA DO CRONÔMETRO GLOBAL ---
    if 'treino_em_andamento' not in st.session_state:
        st.session_state.treino_em_andamento = False
    if 'inicio_treino' not in st.session_state:
        st.session_state.inicio_treino = None

    # --- ÁREA DE TREINO ---
    if aba_dashboard:
    st.title("📈 Minha Evolução")
    
    # Busca os logs reais do aluno
    query_logs = text("""
        SELECT data_execucao, duracao_minutos, treino_nome 
        FROM logs_treino 
        WHERE usuario_id = :u 
        ORDER BY data_execucao ASC
    """)
    df_logs = pd.read_sql(query_logs, engine, params={"u": st.session_state.user_id})
    
    if not df_logs.empty:
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Gráfico de duração por dia
            fig1 = px.line(df_logs, x="data_execucao", y="duracao_minutos", 
                          title="Duração dos Treinos (Minutos)", markers=True)
            st.plotly_chart(fig1, use_container_width=True)
            
        with col_graf2:
            # Frequência por tipo de treino
            fig2 = px.pie(df_logs, names="treino_nome", title="Distribuição de Treinos Realizados")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Complete o seu primeiro treino para visualizar os gráficos de evolução!")

        # BOTÃO INICIAR / STATUS DO TREINO
        if not st.session_state.treino_em_andamento:
            if st.button("🚀 INICIAR TREINO", use_container_width=True, type="primary"):
                st.session_state.treino_em_andamento = True
                st.session_state.inicio_treino = datetime.now()
                st.rerun()
        else:
            # Calcula tempo decorrido
            tempo_decorrido = datetime.now() - st.session_state.inicio_treino
            horas, resto = divmod(tempo_decorrido.seconds, 3600)
            minutos, segundos = divmod(resto, 60)
            
            st.success(f"⏱️ Tempo de Treino: {horas:02d}:{minutos:02d}:{segundos:02d}")
            
            if st.button("🏁 ENCERRAR TREINO", use_container_width=True):
                st.session_state.treino_finalizado = True # Gatilho para o modal ou mensagem

        # Busca exercícios
        query_ex = text("""
            SELECT f.id, e.nome, f.series, f.repeticoes, f.carga_atual, e.url_imagem, f.tempo_descanso
            FROM fichas_treino f JOIN exercicios_biblioteca e ON f.exercicio_id = e.id 
            WHERE f.usuario_id = :u AND f.treino_nome = :t
        """)
        df_ex = pd.read_sql(query_ex, engine, params={"u": st.session_state.user_id, "t": treino_selecionado})

        for idx, row in df_ex.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    img = row['url_imagem'] if row['url_imagem'] else "https://via.placeholder.com/150"
                    st.image(img, use_container_width=True)
                with c2:
                    st.subheader(row['nome'])
                    st.write(f"**{row['series']} séries x {row['repeticoes']} reps** | {row['carga_atual']}kg")
                    
                    # Se o treino estiver em andamento, mostra o botão de descanso
                    if st.session_state.treino_em_andamento:
                        if st.button(f"⏱️ Descanso ({row['tempo_descanso']}s)", key=f"t_{row['id']}"):
                            placeholder = st.empty()
                            for t in range(row['tempo_descanso'], -1, -1):
                                placeholder.metric("Descansando...", f"{t}s")
                                time.sleep(1)
                            placeholder.success("Próxima série!")
                            
                            # Se for o último exercício da lista, avisa
                            if idx == len(df_ex) - 1:
                                st.balloons()
                                st.info("🎉 Último exercício concluído! Não esqueça de encerrar o treino no botão acima.")

        # DIÁLOGO DE ENCERRAMENTO (MODAL SIMULADO)
        if 'treino_finalizado' in st.session_state and st.session_state.treino_finalizado:
    st.markdown("---")
    st.warning("### Deseja encerrar o treino agora?")
    col_fim1, col_fim2 = st.columns(2)
    
    if col_fim1.button("✅ Sim, Encerrar"):
        # 1. Calcula a duração em minutos
        agora = datetime.now()
        duracao = agora - st.session_state.inicio_treino
        minutos_totais = int(duracao.total_seconds() / 60)
        
        # 2. Grava no banco de dados
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO logs_treino (usuario_id, treino_nome, duracao_minutos, data_execucao)
                    VALUES (:u, :t, :d, :dt)
                """), {
                    "u": st.session_state.user_id,
                    "t": treino_selecionado,
                    "d": minutos_totais,
                    "dt": agora
                })
            
            # 3. Limpa o cronômetro e avisa o usuário
            st.session_state.treino_em_andamento = False
            st.session_state.inicio_treino = None
            st.session_state.treino_finalizado = False
            
            st.success(f"🏆 Treino de {minutos_totais} min registrado com sucesso!")
            st.balloons()
            time.sleep(3)
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao salvar log: {e}")

    if col_fim2.button("❌ Não, Continuar"):
        st.session_state.treino_finalizado = False
        st.rerun()
