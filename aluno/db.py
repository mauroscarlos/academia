"""
gymflow/db.py — Acesso ao Supabase (compartilhado entre professor e aluno)
"""
from __future__ import annotations
import time as time_module
import streamlit as st
from supabase import create_client, Client
from datetime import date
from typing import Optional
import pandas as pd


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _retry(fn, retries=3, delay=1.5):
    last_err = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time_module.sleep(delay)
    raise last_err


def _df(resp, cols):
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame(columns=cols)


# ── Alunos ─────────────────────────────────────────────────────────────────

def listar_alunos(apenas_ativos=True) -> pd.DataFrame:
    client = get_client()
    def _q():
        q = client.table("alunos").select("*").order("nome")
        if apenas_ativos:
            q = q.eq("ativo", True)
        return q.execute()
    return _df(_retry(_q), ["id","nome","email","telefone","ativo","created_at"])

def salvar_aluno(nome, email="", telefone="", aluno_id=None) -> dict:
    client = get_client()
    payload = {"nome": nome.strip(), "email": email or None, "telefone": telefone or None, "ativo": True}
    if aluno_id:
        payload["id"] = aluno_id
        resp = _retry(lambda: client.table("alunos").upsert(payload).execute())
    else:
        resp = _retry(lambda: client.table("alunos").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def desativar_aluno(aluno_id: int):
    client = get_client()
    _retry(lambda: client.table("alunos").update({"ativo": False}).eq("id", aluno_id).execute())


# ── Exercícios ─────────────────────────────────────────────────────────────

def listar_exercicios() -> pd.DataFrame:
    client = get_client()
    resp = _retry(lambda: client.table("exercicios").select("*").order("grupo").order("nome").execute())
    return _df(resp, ["id","nome","grupo","descricao","created_at"])

def salvar_exercicio(nome, grupo, descricao="") -> dict:
    client = get_client()
    payload = {"nome": nome.strip(), "grupo": grupo, "descricao": descricao or None}
    resp = _retry(lambda: client.table("exercicios").upsert(payload, on_conflict="nome").execute())
    return resp.data[0] if resp.data else payload

def excluir_exercicio(ex_id: int):
    client = get_client()
    _retry(lambda: client.table("exercicios").delete().eq("id", ex_id).execute())


# ── Planos ─────────────────────────────────────────────────────────────────

def listar_planos(aluno_id=None) -> pd.DataFrame:
    client = get_client()
    def _q():
        q = client.table("planos").select("*").order("mes", desc=True)
        if aluno_id:
            q = q.eq("aluno_id", aluno_id)
        return q.execute()
    return _df(_retry(_q), ["id","aluno_id","nome","mes","ativo","created_at"])

def salvar_plano(aluno_id, nome, mes) -> dict:
    client = get_client()
    payload = {"aluno_id": aluno_id, "nome": nome.strip(), "mes": mes, "ativo": True}
    resp = _retry(lambda: client.table("planos").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def excluir_plano(plano_id: int):
    client = get_client()
    _retry(lambda: client.table("planos").delete().eq("id", plano_id).execute())


# ── Treinos ────────────────────────────────────────────────────────────────

def listar_treinos(plano_id) -> pd.DataFrame:
    client = get_client()
    resp = _retry(lambda: client.table("treinos").select("*").eq("plano_id", plano_id).order("ordem").execute())
    return _df(resp, ["id","plano_id","nome","descricao","ordem","created_at"])

def salvar_treino(plano_id, nome, descricao="", ordem=0) -> dict:
    client = get_client()
    payload = {"plano_id": plano_id, "nome": nome.strip(), "descricao": descricao or None, "ordem": ordem}
    resp = _retry(lambda: client.table("treinos").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def excluir_treino(treino_id: int):
    client = get_client()
    _retry(lambda: client.table("treinos").delete().eq("id", treino_id).execute())


# ── Itens do treino ────────────────────────────────────────────────────────

def listar_itens(treino_id) -> pd.DataFrame:
    client = get_client()
    resp = _retry(lambda: client.table("treino_itens").select("*, exercicios(nome, grupo)")
                  .eq("treino_id", treino_id).order("ordem").execute())
    if not resp.data:
        return pd.DataFrame(columns=["id","treino_id","exercicio_id","ordem",
                                      "tipo_serie","descanso_seg","combinado_com","observacao"])
    df = pd.DataFrame(resp.data)
    df["exercicio_nome"] = df["exercicios"].apply(lambda x: x["nome"] if isinstance(x, dict) else "—")
    df["exercicio_grupo"] = df["exercicios"].apply(lambda x: x["grupo"] if isinstance(x, dict) else "—")
    return df

def salvar_item(treino_id, exercicio_id, ordem, tipo_serie, descanso_seg,
                combinado_com=None, observacao="") -> dict:
    client = get_client()
    payload = {
        "treino_id": treino_id, "exercicio_id": exercicio_id, "ordem": ordem,
        "tipo_serie": tipo_serie, "descanso_seg": descanso_seg,
        "combinado_com": combinado_com or None, "observacao": observacao or None,
    }
    resp = _retry(lambda: client.table("treino_itens").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def excluir_item(item_id: int):
    client = get_client()
    _retry(lambda: client.table("treino_itens").delete().eq("id", item_id).execute())


# ── Séries ─────────────────────────────────────────────────────────────────

def listar_series(treino_item_id) -> pd.DataFrame:
    client = get_client()
    resp = _retry(lambda: client.table("series").select("*")
                  .eq("treino_item_id", treino_item_id).order("numero").execute())
    return _df(resp, ["id","treino_item_id","numero","repeticoes","carga","created_at"])

def salvar_serie(treino_item_id, numero, repeticoes, carga=None) -> dict:
    client = get_client()
    payload = {"treino_item_id": treino_item_id, "numero": numero,
               "repeticoes": repeticoes, "carga": float(carga) if carga else None}
    resp = _retry(lambda: client.table("series").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def excluir_series_do_item(treino_item_id: int):
    client = get_client()
    _retry(lambda: client.table("series").delete().eq("treino_item_id", treino_item_id).execute())


# ── Histórico ──────────────────────────────────────────────────────────────

def iniciar_treino(aluno_id, treino_id) -> dict:
    from datetime import datetime, timezone
    client = get_client()
    payload = {"aluno_id": aluno_id, "treino_id": treino_id,
               "data": str(date.today()), "iniciado_em": datetime.now(timezone.utc).isoformat()}
    resp = _retry(lambda: client.table("historico_treinos").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def finalizar_treino(historico_id: int):
    from datetime import datetime, timezone
    client = get_client()
    _retry(lambda: client.table("historico_treinos")
           .update({"finalizado_em": datetime.now(timezone.utc).isoformat()})
           .eq("id", historico_id).execute())

def registrar_serie_executada(historico_treino_id, treino_item_id, serie_numero,
                               repeticoes_feitas=None, carga_usada=None) -> dict:
    from datetime import datetime, timezone
    client = get_client()
    payload = {
        "historico_treino_id": historico_treino_id,
        "treino_item_id": treino_item_id,
        "serie_numero": serie_numero,
        "repeticoes_feitas": repeticoes_feitas,
        "carga_usada": float(carga_usada) if carga_usada else None,
        "executado_em": datetime.now(timezone.utc).isoformat(),
    }
    resp = _retry(lambda: client.table("historico_series").insert(payload).execute())
    return resp.data[0] if resp.data else payload

def listar_historico(aluno_id, limit=30) -> pd.DataFrame:
    client = get_client()
    resp = _retry(lambda: client.table("historico_treinos")
                  .select("*, treinos(nome, descricao)")
                  .eq("aluno_id", aluno_id).order("data", desc=True).limit(limit).execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["treino_nome"] = df["treinos"].apply(lambda x: x["nome"] if isinstance(x, dict) else "—")
    df["treino_desc"] = df["treinos"].apply(lambda x: x.get("descricao","") if isinstance(x, dict) else "")
    return df
