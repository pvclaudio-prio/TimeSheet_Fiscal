import streamlit as st
import pandas as pd
from datetime import datetime, date
from io import BytesIO
from pathlib import Path
import plotly.express as px
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import zipfile
import tempfile
import json
from oauth2client.client import OAuth2Credentials
import httplib2
import traceback
import openai
import json
import httpx
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
import json
import requests
import tempfile
from difflib import get_close_matches
import re
from datetime import timedelta
import matplotlib.pyplot as plt


st.set_page_config(page_title="Timesheet Fiscal", layout="wide")
st.write("Hoje:", pd.Timestamp.today())

# -----------------------------
# Validação Usuários
# -----------------------------

@st.cache_data
def carregar_usuarios():
    usuarios_config = st.secrets.get("users", {})
    usuarios = {}
    for user, dados in usuarios_config.items():
        try:
            nome, senha = dados.split("|", 1)
            usuarios[user] = {"name": nome, "password": senha}
        except:
            st.warning(f"Erro ao carregar usuário '{user}' nos secrets.")
    return usuarios

users = carregar_usuarios()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = users.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bem-vindo, {user['name']}!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

st.sidebar.image("PRIO_SEM_POLVO_PRIO_PANTONE_LOGOTIPO_Azul.png")
nome_usuario = users[st.session_state.username]["name"]
st.sidebar.success(f"Logado como: {nome_usuario}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()


# -----------------------------
# Funções Auxiliares
# -----------------------------

def conectar_drive():
    cred_dict = st.secrets["credentials"]
    credentials = OAuth2Credentials(
        access_token=cred_dict["access_token"],
        client_id=cred_dict["client_id"],
        client_secret=cred_dict["client_secret"],
        refresh_token=cred_dict["refresh_token"],
        token_expiry=datetime.strptime(cred_dict["token_expiry"], "%Y-%m-%dT%H:%M:%SZ"),
        token_uri=cred_dict["token_uri"],
        user_agent="streamlit-app/1.0",
        revoke_uri=cred_dict["revoke_uri"]
    )
    if credentials.access_token_expired:
        credentials.refresh()
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    return drive

def obter_pasta_ts_fiscal(drive):
    # Verifica se a pasta 'ts-fiscal' existe
    lista = drive.ListFile({
        'q': "title='ts-fiscal' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if lista:
        return lista[0]['id']
    else:
        # Cria a pasta caso não exista
        pasta = drive.CreateFile({
            'title': 'ts-fiscal',
            'mimeType': 'application/vnd.google-apps.folder'
        })
        pasta.Upload()
        return pasta['id']

def carregar_arquivo(nome_arquivo):
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    arquivos = drive.ListFile({
        'q': f"'{pasta_id}' in parents and title = '{nome_arquivo}' and trashed=false"
    }).GetList()

    if not arquivos:
        return None, None

    caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
    arquivos[0].GetContentFile(caminho_temp)
    return pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig"), arquivos[0]

def salvar_arquivo(df, nome_arquivo):
    df.to_csv(nome_arquivo, sep=";", index=False, encoding="utf-8-sig")
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    arquivos = drive.ListFile({
        'q': f"'{pasta_id}' in parents and title = '{nome_arquivo}' and trashed=false"
    }).GetList()

    if arquivos:
        arquivo = arquivos[0]
    else:
        arquivo = drive.CreateFile({
            'title': nome_arquivo,
            'parents': [{'id': pasta_id}]
        })

    arquivo.SetContentFile(nome_arquivo)
    arquivo.Upload()

def carregar_empresas():
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    arquivos = drive.ListFile({
        'q': f"'{pasta_id}' in parents and title = 'empresas.csv' and trashed=false"
    }).GetList()

    if not arquivos:
        df = pd.DataFrame(columns=["Codigo SAP", "Nome Empresa", "Descrição"])
        df.to_csv("empresas.csv", sep=";", index=False, encoding="utf-8-sig")
        arquivo = drive.CreateFile({
            'title': 'empresas.csv',
            'parents': [{'id': pasta_id}]
        })
        arquivo.SetContentFile("empresas.csv")
        arquivo.Upload()
        return df

    caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
    arquivos[0].GetContentFile(caminho_temp)
    df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
    return df


def salvar_empresas(df):
    df.to_csv("empresas.csv", sep=";", index=False, encoding="utf-8-sig")
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    arquivos = drive.ListFile({
        'q': f"'{pasta_id}' in parents and title = 'empresas.csv' and trashed=false"
    }).GetList()

    if arquivos:
        arquivo = arquivos[0]
    else:
        arquivo = drive.CreateFile({
            'title': 'empresas.csv',
            'parents': [{'id': pasta_id}]
        })

    arquivo.SetContentFile("empresas.csv")
    arquivo.Upload()
    
# -----------------------------
# Menu Latereal
# -----------------------------

st.sidebar.title("📋 Menu Timesheet Fiscal")

menu = st.sidebar.radio("Navegar para:", [
    "🏠 Dashboard",
    "🏢 Cadastro de Empresas",
    "🗂️ Cadastro de Projetos e Atividades",
    "📝 Lançamento de Timesheet",
    "📄 Visualizar / Editar Timesheet",
    "📊 Avaliação de Performance — IA"
])

# -----------------------------
# Conteúdo das Páginas
# -----------------------------

if menu == "🏠 Dashboard":
    st.title("📊 Painel de KPIs do Timesheet")
    st.info("Em construção...")

# -----------------------------
# Menu Cadastro de Empresa
# -----------------------------

elif menu == "🏢 Cadastro de Empresas":
    st.title("🏢 Cadastro de Empresas (Códigos SAP)")
    st.subheader("📥 Inserir nova empresa")
    st.markdown("### ➕ Adicionar Nova Empresa")

    with st.form("form_empresa"):
        col1, col2 = st.columns([2, 4])
        with col1:
            codigo = st.text_input("Código SAP")
        with col2:
            nome = st.text_input("Nome da Empresa")
    
        descricao = st.text_area("Descrição (opcional)", height=100)
    
        submitted = st.form_submit_button("💾 Salvar Empresa")
        if submitted:
            if not codigo or not nome:
                st.warning("⚠️ Código SAP e Nome são obrigatórios.")
            else:
                df = carregar_empresas()
                if codigo in df["Codigo SAP"].values:
                    st.warning("⚠️ Já existe uma empresa cadastrada com este Código SAP.")
                else:
                    nova = pd.DataFrame({
                        "Codigo SAP": [codigo.strip()],
                        "Nome Empresa": [nome.strip()],
                        "Descrição": [descricao.strip()]
                    })
                    df = pd.concat([df, nova], ignore_index=True)
                    salvar_empresas(df)
                    st.success("✅ Empresa cadastrada com sucesso!")
    
    # 📄 Empresas Cadastradas
    st.markdown("---")
    st.markdown("### 🏢 Empresas Cadastradas")
    
    df_empresas = carregar_empresas()
    
    st.dataframe(df_empresas, use_container_width=True)
    
    # 🛠️ Edição e Exclusão
    st.markdown("---")
    st.markdown("### 🛠️ Editar ou Excluir Empresa")
    
    if not df_empresas.empty:
        empresa_selecionada = st.selectbox(
            "Selecione a empresa pelo Código SAP:",
            df_empresas["Codigo SAP"]
        )
    
        empresa_info = df_empresas[df_empresas["Codigo SAP"] == empresa_selecionada].iloc[0]
    
        novo_nome = st.text_input("Novo Nome da Empresa", value=empresa_info["Nome Empresa"])
        nova_descricao = st.text_area("Nova Descrição", value=empresa_info["Descrição"])
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Atualizar Empresa"):
                df_empresas.loc[df_empresas["Codigo SAP"] == empresa_selecionada, "Nome Empresa"] = novo_nome.strip()
                df_empresas.loc[df_empresas["Codigo SAP"] == empresa_selecionada, "Descrição"] = nova_descricao.strip()
                salvar_empresas(df_empresas)
                st.success("✅ Empresa atualizada com sucesso!")
                st.experimental_rerun()
    
        with col2:
            if st.button("🗑️ Excluir Empresa"):
                confirmar = st.radio("⚠️ Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
                if confirmar == "Sim":
                    df_empresas = df_empresas[df_empresas["Codigo SAP"] != empresa_selecionada]
                    salvar_empresas(df_empresas)
                    st.success("✅ Empresa excluída com sucesso!")
                    st.experimental_rerun()
    else:
        st.info("🚩 Nenhuma empresa cadastrada até o momento.")
            
# -----------------------------
# Menu Cadastro de Projeto
# -----------------------------

elif menu == "🗂️ Cadastro de Projetos e Atividades":
    st.title("🗂️ Cadastro de Projetos e Atividades")
    st.info("Em construção...")

# -----------------------------
# Menu Lançamento TS
# -----------------------------

elif menu == "📝 Lançamento de Timesheet":
    st.title("📝 Lançamento de Timesheet")
    st.info("Em construção...")

# -----------------------------
# Menu Visualizar TS
# -----------------------------

elif menu == "📄 Visualizar / Editar Timesheet":
    st.title("📄 Visualizar, Editar ou Excluir Timesheet")
    st.info("Em construção...")

# -----------------------------
# Menu Performance
# -----------------------------

elif menu == "📊 Avaliação de Performance — IA":
    st.title("📊 Avaliação de Performance com IA")
    st.info("Em construção...")



