"""
GymFlow — App do Aluno
Execução do treino com timer de descanso
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo
import time
import db

TZ_BR = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title="GymFlow — Treino", page_icon="🏋️",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@400;500&family=Figtree:wght@300;400;500;600&display=swap');
html,body,[class*="css"],.stApp{font-family:'Figtree',sans-serif!important;background:#0e0f13!important;color:#e8eaf0!important}
.stApp,.main .block-container{background:#0e0f13!important;padding:1rem}
.stButton>button{background:#1e2029!important;color:#e8eaf0!important;border:1px solid #2a2d3a!important;border-radius:12px!important;font-family:'Figtree',sans-serif!important;font-weight:600!important;font-size:16px!important;padding:12px!important;width:100%}
.stButton>button:hover{background:#2a2d3a!important;border-color:#c8f564!important;color:#c8f564!important}
button[kind="primary"]{background:#c8f564!important;color:#0e0f13!important;border:none!important;font-size:18px!important;padding:16px!important;border-radius:14px!important}
[data-baseweb="select"]>div:first-child{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:9px!important;color:#e8eaf0!important}
[data-baseweb="popover"] ul,[data-baseweb="menu"]{background:#1e2029!important;border:1px solid #2a2d3a!important;border-radius:10px!important}
[data-baseweb="menu"] li:hover{background:#2a2d3a!important}
div[data-testid="stSuccess"]{background:rgba(200,245,100,0.08)!important;border-left:4px solid #c8f564!important;border-radius:10px!important}
div[data-testid="stInfo"]{background:rgba(106,240,200,0.08)!important;border-left:4px solid #6af0c8!important;border-radius:10px!important}
hr{border-color:#2a2d3a!important}
</style>""", unsafe_allow_html=True)

# ── Estado da sessão ───────────────────────────────────────────────────────
def init_state():
    defaults = {
        "tela": "selecao",          # selecao | executando | descanso | concluido
        "aluno_id": None,
        "treino_id": None,
        "historico_id": None,
        "itens": [],                 # lista de itens do treino
        "item_idx": 0,              # índice do exercício atual
        "serie_idx": 0,             # índice da série atual
        "series_por_item": {},       # {item_id: [series]}
        "timer_fim": None,
        "timer_seg": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ══════════════════════════════════════════════════════════════════════════
# TELA 1 — SELEÇÃO DE ALUNO E TREINO
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.tela == "selecao":
    st.markdown("""
    <div style="text-align:center;padding:20px 0 30px">
        <div style="font-family:'DM Serif Display',serif;font-size:36px;color:#c8f564">GymFlow</div>
        <div style="color:#7a7f96;font-size:13px;letter-spacing:2px;text-transform:uppercase;margin-top:4px">Seu treino de hoje</div>
    </div>""", unsafe_allow_html=True)

    alunos_df = db.listar_alunos()
    if alunos_df.empty:
        st.warning("Nenhum aluno cadastrado. Fale com seu professor.")
        st.stop()

    aluno_map = {int(r["id"]): r["nome"] for _, r in alunos_df.iterrows()}
    sel_aluno = st.selectbox("Quem é você?", options=list(aluno_map.keys()),
                              format_func=lambda x: aluno_map[x])

    planos_df = db.listar_planos(sel_aluno)
    if planos_df.empty:
        st.info("Nenhum plano de treino encontrado. Fale com seu professor.")
        st.stop()

    # Plano mais recente ativo
    plano_atual = planos_df.iloc[0]
    treinos_df = db.listar_treinos(int(plano_atual["id"]))

    if treinos_df.empty:
        st.info(f"O plano '{plano_atual['nome']}' ainda não tem treinos. Fale com seu professor.")
        st.stop()

    st.markdown(f"""
    <div style="background:#16181f;border:1px solid #2a2d3a;border-radius:12px;padding:14px 18px;margin:16px 0;text-align:center">
        <div style="font-size:11px;color:#7a7f96;text-transform:uppercase;letter-spacing:1.5px">Plano atual</div>
        <div style="font-size:20px;font-weight:600;color:#e8eaf0;margin-top:4px">{plano_atual['nome']}</div>
    </div>""", unsafe_allow_html=True)

    treino_map = {int(r["id"]): f"Treino {r['nome']} — {r['descricao'] or ''}" 
                  for _, r in treinos_df.iterrows()}
    sel_treino = st.selectbox("Qual treino de hoje?", options=list(treino_map.keys()),
                               format_func=lambda x: treino_map[x])

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏋️ Iniciar Treino", type="primary", use_container_width=True):
        # Carrega itens e séries
        itens_df = db.listar_itens(sel_treino)
        if itens_df.empty:
            st.error("Este treino não tem exercícios. Fale com seu professor.")
            st.stop()

        itens = itens_df.to_dict("records")
        series_por_item = {}
        for item in itens:
            s_df = db.listar_series(int(item["id"]))
            series_por_item[int(item["id"])] = s_df.to_dict("records")

        hist = db.iniciar_treino(sel_aluno, sel_treino)

        st.session_state.aluno_id = sel_aluno
        st.session_state.treino_id = sel_treino
        st.session_state.historico_id = hist["id"]
        st.session_state.itens = itens
        st.session_state.series_por_item = series_por_item
        st.session_state.item_idx = 0
        st.session_state.serie_idx = 0
        st.session_state.tela = "executando"
        st.rerun()

    st.divider()
    # Histórico rápido
    hist_df = db.listar_historico(sel_aluno, limit=5)
    if not hist_df.empty:
        st.markdown("**Últimos treinos**")
        for _, h in hist_df.iterrows():
            data_fmt = pd.to_datetime(str(h["data"])).strftime("%d/%m/%Y")
            duracao = ""
            if h.get("finalizado_em") and h.get("iniciado_em"):
                try:
                    ini = pd.to_datetime(h["iniciado_em"])
                    fim = pd.to_datetime(h["finalizado_em"])
                    mins = int((fim - ini).total_seconds() / 60)
                    duracao = f" — {mins} min"
                except Exception:
                    pass
            st.markdown(f"""
            <div style="background:#16181f;border:1px solid #2a2d3a;border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between">
                <span>Treino {h['treino_nome']}</span>
                <span style="color:#7a7f96;font-size:13px">{data_fmt}{duracao}</span>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TELA 2 — EXECUTANDO TREINO
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.tela == "executando":
    itens = st.session_state.itens
    item_idx = st.session_state.item_idx
    serie_idx = st.session_state.serie_idx
    item = itens[item_idx]
    item_id = int(item["id"])
    series = st.session_state.series_por_item.get(item_id, [])
    total_itens = len(itens)
    total_series = len(series)

    # Verifica se é combinado
    eh_combinado = bool(item.get("combinado_com"))

    # Progresso geral
    progresso = (item_idx) / total_itens
    st.markdown(f"""
    <div style="background:#16181f;border-radius:20px;height:6px;margin-bottom:20px;overflow:hidden">
        <div style="background:#c8f564;height:100%;width:{progresso*100:.0f}%;border-radius:20px;transition:width 0.3s"></div>
    </div>
    <div style="text-align:right;font-size:11px;color:#7a7f96;margin-top:-14px;margin-bottom:20px">
        Exercício {item_idx+1} de {total_itens}
    </div>""", unsafe_allow_html=True)

    # Card do exercício atual
    tipo_badge = "🔺 Pirâmide" if item.get("tipo_serie") == "piramide" else "➡️ Linear"
    comb_badge = "🔗 Combinado" if eh_combinado else ""

    st.markdown(f"""
    <div style="background:#16181f;border:1px solid #2a2d3a;border-radius:16px;padding:20px;margin-bottom:16px">
        <div style="font-size:11px;color:#7a7f96;text-transform:uppercase;letter-spacing:1.5px">{item.get('exercicio_grupo','')}</div>
        <div style="font-family:'DM Serif Display',serif;font-size:28px;color:#e8eaf0;margin:6px 0">{item.get('exercicio_nome','')}</div>
        <div style="font-size:12px;color:#7a7f96">{tipo_badge} {'· ' + comb_badge if comb_badge else ''} · ⏱ {item.get('descanso_seg',60)}s descanso</div>
        {f'<div style="font-size:13px;color:#6af0c8;margin-top:8px">📝 {item["observacao"]}</div>' if item.get("observacao") else ''}
    </div>""", unsafe_allow_html=True)

    # Série atual
    if serie_idx < total_series:
        serie = series[serie_idx]
        carga_txt = f" · {serie['carga']}kg" if serie.get('carga') else ""

        st.markdown(f"""
        <div style="background:#1e2029;border:2px solid #c8f564;border-radius:16px;padding:24px;text-align:center;margin-bottom:20px">
            <div style="font-size:11px;color:#7a7f96;text-transform:uppercase;letter-spacing:2px">Série atual</div>
            <div style="font-family:'DM Mono',monospace;font-size:56px;font-weight:700;color:#c8f564;line-height:1.1">{serie_idx+1}</div>
            <div style="font-size:13px;color:#7a7f96">de {total_series} séries</div>
            <div style="font-size:22px;color:#e8eaf0;margin-top:12px;font-weight:600">{serie['repeticoes']} repetições{carga_txt}</div>
        </div>""", unsafe_allow_html=True)

        # Todas as séries em miniatura
        series_html = ""
        for i, s in enumerate(series):
            if i < serie_idx:
                bg, cor = "#c8f564", "#0e0f13"
                txt = "✓"
            elif i == serie_idx:
                bg, cor = "#2a2d3a", "#c8f564"
                txt = str(i+1)
            else:
                bg, cor = "#1e2029", "#7a7f96"
                txt = str(i+1)
            series_html += f'<div style="width:36px;height:36px;border-radius:50%;background:{bg};color:{cor};display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;margin:0 4px">{txt}</div>'
        st.markdown(f'<div style="text-align:center;margin-bottom:20px">{series_html}</div>', unsafe_allow_html=True)

        if st.button("✅ Série concluída!", type="primary", use_container_width=True):
            # Registra série no histórico
            db.registrar_serie_executada(
                historico_treino_id=st.session_state.historico_id,
                treino_item_id=item_id,
                serie_numero=serie_idx + 1,
                repeticoes_feitas=serie.get("repeticoes"),
                carga_usada=serie.get("carga"),
            )

            prox_serie = serie_idx + 1
            if prox_serie >= total_series:
                # Acabaram as séries — avança exercício
                prox_item = item_idx + 1
                if prox_item >= total_itens:
                    # Último exercício concluído!
                    st.session_state.tela = "concluido"
                else:
                    # Vai para o descanso antes do próximo exercício
                    # Se for combinado, descanso é do último exercício do bloco
                    st.session_state.item_idx = prox_item
                    st.session_state.serie_idx = 0
                    st.session_state.timer_seg = int(item.get("descanso_seg", 60))
                    st.session_state.tela = "descanso"
            else:
                # Próxima série — vai para o descanso
                st.session_state.serie_idx = prox_serie
                st.session_state.timer_seg = int(item.get("descanso_seg", 60))
                st.session_state.tela = "descanso"
            st.rerun()

        col_pular, col_sair = st.columns(2)
        with col_pular:
            if st.button("⏭ Pular série", use_container_width=True):
                prox_serie = serie_idx + 1
                if prox_serie >= total_series:
                    prox_item = item_idx + 1
                    if prox_item >= total_itens:
                        st.session_state.tela = "concluido"
                    else:
                        st.session_state.item_idx = prox_item
                        st.session_state.serie_idx = 0
                        st.session_state.timer_seg = int(item.get("descanso_seg", 60))
                        st.session_state.tela = "descanso"
                else:
                    st.session_state.serie_idx = prox_serie
                    st.session_state.timer_seg = int(item.get("descanso_seg", 60))
                    st.session_state.tela = "descanso"
                st.rerun()
        with col_sair:
            if st.button("🚪 Encerrar treino", use_container_width=True):
                db.finalizar_treino(st.session_state.historico_id)
                st.session_state.tela = "selecao"
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TELA 3 — DESCANSO (TIMER)
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.tela == "descanso":
    total_seg = st.session_state.timer_seg
    item_idx = st.session_state.item_idx
    serie_idx = st.session_state.serie_idx
    itens = st.session_state.itens
    item_atual = itens[item_idx]
    total_series = len(st.session_state.series_por_item.get(int(item_atual["id"]), []))

    # Inicializa o fim do timer
    if st.session_state.timer_fim is None:
        st.session_state.timer_fim = time.time() + total_seg

    restante = max(0, int(st.session_state.timer_fim - time.time()))
    pct = restante / total_seg if total_seg > 0 else 0
    mins = restante // 60
    segs = restante % 60

    # Cor muda conforme urgência
    if restante > total_seg * 0.5:
        cor_timer = "#6af0c8"
    elif restante > total_seg * 0.2:
        cor_timer = "#f5a623"
    else:
        cor_timer = "#ff6b6b"

    st.markdown(f"""
    <div style="text-align:center;padding:30px 0">
        <div style="font-size:13px;color:#7a7f96;text-transform:uppercase;letter-spacing:2px;margin-bottom:16px">⏱ Descansando</div>
        <div style="font-family:'DM Mono',monospace;font-size:72px;font-weight:700;color:{cor_timer};line-height:1">{mins:02d}:{segs:02d}</div>
        <div style="margin:20px auto;max-width:280px;background:#1e2029;border-radius:20px;height:8px;overflow:hidden">
            <div style="background:{cor_timer};height:100%;width:{pct*100:.1f}%;border-radius:20px;transition:width 0.5s"></div>
        </div>
        <div style="color:#7a7f96;font-size:13px">Próximo: <b style="color:#e8eaf0">{item_atual.get('exercicio_nome','')} — Série {serie_idx+1}/{total_series}</b></div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚡ Pular descanso", use_container_width=True):
            st.session_state.timer_fim = None
            st.session_state.tela = "executando"
            st.rerun()
    with col2:
        if st.button("➕ +30s", use_container_width=True):
            st.session_state.timer_fim += 30
            st.rerun()

    if restante <= 0:
        st.session_state.timer_fim = None
        st.session_state.tela = "executando"
        st.rerun()
    else:
        time.sleep(1)
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TELA 4 — TREINO CONCLUÍDO
# ══════════════════════════════════════════════════════════════════════════
elif st.session_state.tela == "concluido":
    db.finalizar_treino(st.session_state.historico_id)

    st.markdown("""
    <div style="text-align:center;padding:40px 0">
        <div style="font-size:64px;margin-bottom:16px">🏆</div>
        <div style="font-family:'DM Serif Display',serif;font-size:36px;color:#c8f564;margin-bottom:8px">Treino Concluído!</div>
        <div style="color:#7a7f96;font-size:15px">Excelente trabalho! Continue assim.</div>
    </div>""", unsafe_allow_html=True)

    total_series = sum(len(v) for v in st.session_state.series_por_item.values())
    total_exercicios = len(st.session_state.itens)

    st.markdown(f"""
    <div style="display:flex;gap:12px;margin:20px 0">
        <div style="flex:1;background:#16181f;border:1px solid #2a2d3a;border-radius:14px;padding:20px;text-align:center;border-top:3px solid #c8f564">
            <div style="font-family:'DM Mono',monospace;font-size:32px;color:#c8f564">{total_exercicios}</div>
            <div style="font-size:11px;color:#7a7f96;text-transform:uppercase;letter-spacing:1px;margin-top:4px">Exercícios</div>
        </div>
        <div style="flex:1;background:#16181f;border:1px solid #2a2d3a;border-radius:14px;padding:20px;text-align:center;border-top:3px solid #6af0c8">
            <div style="font-family:'DM Mono',monospace;font-size:32px;color:#6af0c8">{total_series}</div>
            <div style="font-size:11px;color:#7a7f96;text-transform:uppercase;letter-spacing:1px;margin-top:4px">Séries</div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 Voltar ao início", type="primary", use_container_width=True):
        for key in ["tela","aluno_id","treino_id","historico_id","itens",
                    "item_idx","serie_idx","series_por_item","timer_fim","timer_seg"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
