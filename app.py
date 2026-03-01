"""
GymFlow — App do Professor
Cadastro de alunos, exercícios, planos e fichas de treino
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import db

TZ_BR = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title="GymFlow — Professor", page_icon="🏋️", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&family=Figtree:wght@300;400;500;600&display=swap');
html,body,[class*="css"],.stApp{font-family:'Figtree',sans-serif!important;background:#0e0f13!important;color:#e8eaf0!important}
.stApp,.main .block-container{background:#0e0f13!important;max-width:1200px}
section[data-testid="stSidebar"]{background:#16181f!important;border-right:1px solid #2a2d3a!important}
section[data-testid="stSidebar"] *{color:#e8eaf0!important}
section[data-testid="stSidebar"] label{color:#7a7f96!important;font-size:11px!important;text-transform:uppercase;letter-spacing:1.5px;font-family:'DM Mono',monospace!important}
section[data-testid="stSidebar"] [data-baseweb="select"]>div,section[data-testid="stSidebar"] input{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:8px!important}
[data-testid="metric-container"]{background:#16181f!important;border:1px solid #2a2d3a!important;border-radius:14px!important;padding:20px!important;border-top:3px solid #c8f564!important}
[data-testid="metric-container"] label{font-size:11px!important;text-transform:uppercase!important;letter-spacing:1.5px!important;color:#7a7f96!important;font-family:'DM Mono',monospace!important}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-family:'DM Mono',monospace!important;font-size:26px!important}
.stTabs [data-baseweb="tab-list"]{background:#16181f!important;border-radius:12px!important;padding:4px!important;border:1px solid #2a2d3a!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:#7a7f96!important;border-radius:9px!important;font-weight:600!important;font-size:14px!important;padding:10px 18px!important;border:none!important}
.stTabs [aria-selected="true"]{background:rgba(200,245,100,0.12)!important;color:#c8f564!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important}
.stButton>button,.stFormSubmitButton>button{background:#1e2029!important;color:#e8eaf0!important;border:1px solid #2a2d3a!important;border-radius:10px!important;font-family:'Figtree',sans-serif!important;font-weight:600!important}
.stButton>button:hover{background:#2a2d3a!important;border-color:#c8f564!important;color:#c8f564!important}
.stFormSubmitButton>button[kind="primaryFormSubmit"],button[kind="primary"]{background:#c8f564!important;color:#0e0f13!important;border:none!important}
input,textarea,[data-baseweb="input"] input{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:9px!important;color:#e8eaf0!important}
[data-baseweb="input"],[data-baseweb="base-input"]{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:9px!important}
[data-baseweb="select"]>div:first-child{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:9px!important;color:#e8eaf0!important}
[data-baseweb="popover"] ul,[data-baseweb="menu"]{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:10px!important}
[data-baseweb="menu"] li:hover{background:#2a2d3a!important}
.stTextInput label,.stDateInput label,.stNumberInput label,.stSelectbox label,.stTextArea label{color:#7a7f96!important;font-size:12px!important}
[data-testid="stForm"]{background:#16181f!important;border:1px solid #2a2d3a!important;border-radius:16px!important;padding:24px!important}
div[data-testid="stSuccess"]{background:rgba(200,245,100,0.08)!important;border-left:4px solid #c8f564!important;border-radius:10px!important}
div[data-testid="stError"]{background:rgba(255,107,107,0.08)!important;border-left:4px solid #ff6b6b!important;border-radius:10px!important}
div[data-testid="stInfo"]{background:rgba(106,240,200,0.08)!important;border-left:4px solid #6af0c8!important;border-radius:10px!important}
[data-testid="stExpander"]{background:#16181f!important;border:1px solid #2a2d3a!important;border-radius:12px!important}
hr{border-color:#2a2d3a!important}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0e0f13}
::-webkit-scrollbar-thumb{background:#2a2d3a;border-radius:3px}
</style>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding-bottom:20px;border-bottom:1px solid #2a2d3a;margin-bottom:20px">
        <div style="font-family:'DM Serif Display',serif;font-size:26px;color:#c8f564">GymFlow</div>
        <div style="font-family:'DM Mono',monospace;font-size:10px;color:#7a7f96;letter-spacing:2px;text-transform:uppercase">Painel do Professor</div>
    </div>""", unsafe_allow_html=True)
    agora = datetime.now(TZ_BR)
    st.markdown(f"""
    <div style="padding:12px;background:#1e2029;border-radius:10px;border:1px solid #2a2d3a;text-align:center">
        <div style="font-family:'DM Mono',monospace;font-size:24px;color:#c8f564">{agora.strftime('%H:%M')}</div>
        <div style="font-size:11px;color:#7a7f96">{agora.strftime('%d/%m/%Y')}</div>
    </div>""", unsafe_allow_html=True)

# ── Dados globais ──────────────────────────────────────────────────────────
alunos_df = db.listar_alunos()
exercicios_df = db.listar_exercicios()

# ── Tabs ───────────────────────────────────────────────────────────────────
tab_alunos, tab_exercicios, tab_planos, tab_ficha = st.tabs([
    "👤 Alunos", "💪 Exercícios", "📅 Planos", "📋 Ficha de Treino"
])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — ALUNOS
# ══════════════════════════════════════════════════════════════════════════
with tab_alunos:
    st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#e8eaf0;margin-bottom:20px">👤 Alunos</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    c1.metric("Total de alunos", len(alunos_df))

    with st.form("form_aluno", clear_on_submit=True):
        st.markdown("**Novo aluno**")
        fa1, fa2, fa3 = st.columns(3)
        with fa1: a_nome = st.text_input("Nome *")
        with fa2: a_email = st.text_input("Email")
        with fa3: a_tel = st.text_input("Telefone")
        if st.form_submit_button("✓ Cadastrar aluno", type="primary", use_container_width=True):
            if not a_nome.strip():
                st.error("Informe o nome do aluno.")
            else:
                db.salvar_aluno(a_nome, a_email, a_tel)
                st.success(f"✓ Aluno '{a_nome}' cadastrado!")
                st.rerun()

    st.divider()
    if alunos_df.empty:
        st.info("Nenhum aluno cadastrado.")
    else:
        for _, row in alunos_df.iterrows():
            with st.expander(f"👤 {row['nome']}"):
                i1, i2, i3 = st.columns([2, 2, 1])
                i1.markdown(f"📧 {row['email'] or '—'}")
                i2.markdown(f"📱 {row['telefone'] or '—'}")
                if i3.button("Desativar", key=f"del_aluno_{row['id']}"):
                    db.desativar_aluno(int(row["id"]))
                    st.success("Aluno desativado.")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — EXERCÍCIOS
# ══════════════════════════════════════════════════════════════════════════
with tab_exercicios:
    st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#e8eaf0;margin-bottom:20px">💪 Exercícios</div>', unsafe_allow_html=True)

    GRUPOS = ["Peito","Costas","Pernas","Ombro","Bíceps","Tríceps","Abdômen","Cardio","Outro"]

    with st.form("form_exercicio", clear_on_submit=True):
        st.markdown("**Novo exercício**")
        fe1, fe2, fe3 = st.columns([2, 1, 2])
        with fe1: e_nome = st.text_input("Nome *")
        with fe2: e_grupo = st.selectbox("Grupo muscular", GRUPOS)
        with fe3: e_desc = st.text_input("Descrição (opcional)")
        if st.form_submit_button("✓ Cadastrar exercício", type="primary", use_container_width=True):
            if not e_nome.strip():
                st.error("Informe o nome do exercício.")
            else:
                db.salvar_exercicio(e_nome, e_grupo, e_desc)
                st.success(f"✓ Exercício '{e_nome}' cadastrado!")
                st.rerun()

    st.divider()
    if not exercicios_df.empty:
        for grupo in exercicios_df["grupo"].unique():
            st.markdown(f"**{grupo}**")
            df_g = exercicios_df[exercicios_df["grupo"] == grupo]
            cols = st.columns(4)
            for i, (_, row) in enumerate(df_g.iterrows()):
                with cols[i % 4]:
                    st.markdown(f"""
                    <div style="background:#16181f;border:1px solid #2a2d3a;border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:13px">
                        {row['nome']}
                    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — PLANOS
# ══════════════════════════════════════════════════════════════════════════
with tab_planos:
    st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#e8eaf0;margin-bottom:20px">📅 Planos de Treino</div>', unsafe_allow_html=True)

    if alunos_df.empty:
        st.warning("Cadastre um aluno primeiro.")
    else:
        aluno_map = {int(r["id"]): r["nome"] for _, r in alunos_df.iterrows()}

        with st.form("form_plano", clear_on_submit=True):
            st.markdown("**Novo plano**")
            fp1, fp2, fp3 = st.columns([2, 1, 1])
            with fp1:
                p_aluno = st.selectbox("Aluno", options=list(aluno_map.keys()),
                                       format_func=lambda x: aluno_map[x])
            with fp2:
                agora_br = datetime.now(TZ_BR)
                p_mes = st.text_input("Mês (YYYY-MM)", value=agora_br.strftime("%Y-%m"))
            with fp3:
                MESES_PT = ["","Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                            "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
                try:
                    y, m = p_mes.split("-")
                    p_nome = f"{MESES_PT[int(m)]}/{y}"
                except Exception:
                    p_nome = p_mes
                st.text_input("Nome do plano", value=p_nome, disabled=True)

            if st.form_submit_button("✓ Criar plano", type="primary", use_container_width=True):
                db.salvar_plano(p_aluno, p_nome, p_mes)
                st.success(f"✓ Plano '{p_nome}' criado para {aluno_map[p_aluno]}!")
                st.rerun()

        st.divider()
        planos_df = db.listar_planos()
        if not planos_df.empty:
            planos_df["aluno_nome"] = planos_df["aluno_id"].apply(
                lambda x: aluno_map.get(int(x), "—"))
            for aluno_nome in planos_df["aluno_nome"].unique():
                st.markdown(f"**👤 {aluno_nome}**")
                df_a = planos_df[planos_df["aluno_nome"] == aluno_nome]
                for _, row in df_a.iterrows():
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"📅 {row['nome']} — `{row['mes']}`")
                    if c2.button("🗑", key=f"del_plano_{row['id']}"):
                        db.excluir_plano(int(row["id"]))
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — FICHA DE TREINO
# ══════════════════════════════════════════════════════════════════════════
with tab_ficha:
    st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-size:24px;color:#e8eaf0;margin-bottom:20px">📋 Ficha de Treino</div>', unsafe_allow_html=True)

    planos_df = db.listar_planos()
    if planos_df.empty or alunos_df.empty:
        st.warning("Cadastre um aluno e crie um plano primeiro.")
    else:
        aluno_map = {int(r["id"]): r["nome"] for _, r in alunos_df.iterrows()}
        planos_df["aluno_nome"] = planos_df["aluno_id"].apply(lambda x: aluno_map.get(int(x), "—"))
        planos_df["label"] = planos_df["aluno_nome"] + " — " + planos_df["nome"]
        plano_map = {int(r["id"]): r["label"] for _, r in planos_df.iterrows()}

        sel_plano = st.selectbox("Selecione o plano", options=list(plano_map.keys()),
                                  format_func=lambda x: plano_map[x])

        treinos_df = db.listar_treinos(sel_plano)

        # Adicionar treino
        with st.form("form_treino", clear_on_submit=True):
            ft1, ft2 = st.columns([1, 3])
            with ft1:
                t_nome = st.text_input("Treino", placeholder="A, B, C...")
            with ft2:
                t_desc = st.text_input("Descrição", placeholder="Ex: Peito e Tríceps")
            if st.form_submit_button("+ Adicionar treino", use_container_width=True):
                if t_nome.strip():
                    ordem = len(treinos_df)
                    db.salvar_treino(sel_plano, t_nome.upper(), t_desc, ordem)
                    st.rerun()

        st.divider()

        if treinos_df.empty:
            st.info("Nenhum treino criado neste plano ainda.")
        else:
            ex_map = {int(r["id"]): r["nome"] for _, r in exercicios_df.iterrows()}

            for _, treino in treinos_df.iterrows():
                treino_id = int(treino["id"])
                with st.expander(f"🏋️ Treino {treino['nome']} — {treino['descricao'] or ''}", expanded=True):

                    itens_df = db.listar_itens(treino_id)

                    # Formulário para adicionar exercício
                    with st.form(f"form_item_{treino_id}", clear_on_submit=True):
                        st.markdown("**Adicionar exercício**")
                        fi1, fi2, fi3, fi4 = st.columns([3, 1, 1, 1])
                        with fi1:
                            ex_sel = st.selectbox("Exercício", options=list(ex_map.keys()),
                                                   format_func=lambda x: ex_map[x],
                                                   key=f"ex_{treino_id}")
                        with fi2:
                            tipo_s = st.selectbox("Tipo", options=["linear","piramide"],
                                                   format_func=lambda x: "Linear" if x == "linear" else "Pirâmide",
                                                   key=f"tipo_{treino_id}")
                        with fi3:
                            descanso = st.number_input("Descanso (s)", min_value=10, max_value=300,
                                                        value=60, step=5, key=f"desc_{treino_id}")
                        with fi4:
                            comb_opts = {"": "— Nenhum —"}
                            if not itens_df.empty:
                                comb_opts.update({str(int(r["id"])): f"{r['exercicio_nome']}" 
                                                   for _, r in itens_df.iterrows()})
                            comb_sel = st.selectbox("Combinado com", options=list(comb_opts.keys()),
                                                     format_func=lambda x: comb_opts[x],
                                                     key=f"comb_{treino_id}")

                        obs_item = st.text_input("Observação", key=f"obs_{treino_id}")

                        n_series = st.number_input("Nº de séries", min_value=1, max_value=10,
                                                    value=3, key=f"ns_{treino_id}")

                        series_cols = st.columns(int(n_series))
                        series_vals = []
                        for i in range(int(n_series)):
                            with series_cols[i]:
                                st.markdown(f"**Série {i+1}**")
                                reps = st.number_input("Reps", min_value=1, max_value=100,
                                                        value=12, key=f"reps_{treino_id}_{i}")
                                carga = st.number_input("Carga(kg)", min_value=0.0, step=0.5,
                                                         value=0.0, key=f"carga_{treino_id}_{i}")
                                series_vals.append((reps, carga))

                        if st.form_submit_button("✓ Adicionar exercício", type="primary", use_container_width=True):
                            comb_id = int(comb_sel) if comb_sel else None
                            item = db.salvar_item(
                                treino_id=treino_id, exercicio_id=ex_sel,
                                ordem=len(itens_df), tipo_serie=tipo_s,
                                descanso_seg=descanso, combinado_com=comb_id, observacao=obs_item
                            )
                            item_id = item["id"]
                            for i, (reps, carga) in enumerate(series_vals):
                                db.salvar_serie(item_id, i+1, reps, carga if carga > 0 else None)
                            st.success("✓ Exercício adicionado!")
                            st.rerun()

                    # Lista de exercícios do treino
                    if not itens_df.empty:
                        st.markdown("---")
                        for _, item in itens_df.iterrows():
                            item_id = int(item["id"])
                            series_df = db.listar_series(item_id)
                            tipo_badge = "🔺 Pirâmide" if item["tipo_serie"] == "piramide" else "➡️ Linear"
                            comb_txt = ""
                            if item.get("combinado_com"):
                                item_comb = itens_df[itens_df["id"] == item["combinado_com"]]
                                if not item_comb.empty:
                                    comb_txt = f" | 🔗 combinado com {item_comb.iloc[0]['exercicio_nome']}"

                            series_html = ""
                            for _, s in series_df.iterrows():
                                carga_txt = f" / {s['carga']}kg" if s['carga'] else ""
                                series_html += f'<span style="background:#1e2029;border:1px solid #2a2d3a;border-radius:6px;padding:4px 10px;margin-right:6px;font-family:DM Mono,monospace;font-size:12px;color:#c8f564">{int(s["numero"])}ª {int(s["repeticoes"])} reps{carga_txt}</span>'

                            col_ex, col_del = st.columns([9, 1])
                            with col_ex:
                                st.markdown(f"""
                                <div style="background:#16181f;border:1px solid #2a2d3a;border-radius:12px;padding:14px 18px;margin-bottom:8px">
                                    <div style="font-weight:600;color:#e8eaf0;margin-bottom:6px">
                                        {item['exercicio_nome']}
                                        <span style="font-size:11px;color:#7a7f96;margin-left:10px">{tipo_badge} | ⏱ {item['descanso_seg']}s{comb_txt}</span>
                                    </div>
                                    <div>{series_html}</div>
                                    {f'<div style="font-size:12px;color:#7a7f96;margin-top:8px">📝 {item["observacao"]}</div>' if item.get("observacao") else ''}
                                </div>""", unsafe_allow_html=True)
                            with col_del:
                                if st.button("🗑", key=f"del_item_{item_id}"):
                                    db.excluir_series_do_item(item_id)
                                    db.excluir_item(item_id)
                                    st.rerun()

                    # Excluir treino
                    if st.button(f"🗑 Excluir treino {treino['nome']}", key=f"del_treino_{treino_id}"):
                        db.excluir_treino(treino_id)
                        st.rerun()
