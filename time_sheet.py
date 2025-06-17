import streamlit as st
import pandas as pd
import tempfile
from datetime import datetime, date, time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import OAuth2Credentials
import httplib2
from openai import OpenAI
from io import BytesIO
from docx import Document
from docx.shared import Pt
import plotly.express as px
import re

st.set_page_config(page_title="Timesheet Fiscal", layout="wide")
st.sidebar.markdown(f"📅 Hoje é: **{date.today().strftime('%d/%m/%Y')}**")

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
    
admin_users = ["cvieira", "wreis", "waraujo", "iassis"]

# -----------------------------
# Funções Auxiliares
# -----------------------------

# 🚀 Conexão com Google Drive
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

    http = httplib2.Http()

    try:
        credentials.refresh(http)
    except Exception as e:
        st.error(f"Erro ao atualizar credenciais: {e}")
        st.stop()

    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    return drive

# 🚩 Obter pasta ts-fiscal
def obter_pasta_ts_fiscal(drive):
    lista = drive.ListFile({
        'q': "title='ts-fiscal' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if lista:
        return lista[0]['id']
    else:
        pasta = drive.CreateFile({
            'title': 'ts-fiscal',
            'mimeType': 'application/vnd.google-apps.folder'
        })
        pasta.Upload()
        return pasta['id']

# 📥 Carregar arquivo
def carregar_arquivo(nome_arquivo):
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    try:
        arquivos = drive.ListFile({
            'q': f"'{pasta_id}' in parents and title = '{nome_arquivo}' and trashed=false"
        }).GetList()
    except Exception as e:
        st.error(f"❌ Erro ao acessar o Drive: {e}")
        st.stop()

    if not arquivos:
        st.error(f"❌ Arquivo '{nome_arquivo}' não encontrado no Google Drive.")
        st.stop()

    caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
    arquivos[0].GetContentFile(caminho_temp)
    df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")

    if df.empty:
        st.warning("⚠️ A base foi carregada mas está vazia.")

    # Tratamento padrão de data e horas
    df = tratar_coluna_data(df)
    df = normalizar_coluna_horas(df)

    return df

# 💾 Salvar arquivo
def salvar_arquivo(df, nome_arquivo):
    # 🚩 Força para que a coluna Data esteja no formato datetime SEMPRE
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.strftime("%Y-%m-%d")

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

    salvar_backup_redundante(df, nome_base=nome_arquivo)

# 🏢 Carregar e salvar empresas
def carregar_empresas():
    df = carregar_arquivo("empresas.csv")
    return df

def salvar_empresas(df):
    salvar_arquivo(df, "empresas.csv")

# ⏰ Tratamento de horas
def formatar_horas(horas_input):
    if not horas_input:
        return None
    horas_input = str(horas_input).strip().replace(",", ".")
    pattern = re.fullmatch(r"(\d{1,2})[:;.,](\d{1,2})", horas_input)

    if pattern:
        h, m = map(int, pattern.groups())
        if 0 <= h < 24 and 0 <= m < 60:
            return f"{h:02d}:{m:02d}"

    try:
        decimal = float(horas_input)
        total_minutos = int(round(decimal * 60))
        h = total_minutos // 60
        m = total_minutos % 60
        return f"{h:02d}:{m:02d}"
    except:
        return None

def normalizar_coluna_horas(df, coluna="Horas Gastas"):
    if coluna in df.columns:
        df[coluna] = df[coluna].astype(str).apply(formatar_horas)
    return df

# 📅 Tratamento de data
def tratar_coluna_data(df, coluna="Data"):
    if coluna in df.columns:
        # Primeiro tenta ler padrão ISO (YYYY-MM-DD) sem ambiguidades
        df[coluna] = pd.to_datetime(df[coluna], errors="coerce", format="%Y-%m-%d")

        # Se ainda tiver datas NaT, tenta outros formatos comuns
        if df[coluna].isnull().sum() > 0:
            df.loc[df[coluna].isnull(), coluna] = pd.to_datetime(
                df.loc[df[coluna].isnull(), coluna], errors="coerce", dayfirst=True
            )

        df = df[df[coluna].notnull()]  # Remove linhas inválidas
    return df

# 🗂️ Backup redundante
def salvar_backup_redundante(df, nome_base="timesheet.csv"):
    drive = conectar_drive()
    pasta_principal_id = obter_pasta_ts_fiscal(drive)

    lista = drive.ListFile({
        'q': f"'{pasta_principal_id}' in parents and title='Backup' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if lista:
        pasta_backup_id = lista[0]['id']
    else:
        pasta = drive.CreateFile({
            'title': 'Backup',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': pasta_principal_id}]
        })
        pasta.Upload()
        pasta_backup_id = pasta['id']

    arquivos_backup = drive.ListFile({
        'q': f"'{pasta_backup_id}' in parents and title contains 'timesheet(' and trashed=false"
    }).GetList()

    padrao = re.compile(r"timesheet\((\d+)\)\.csv$")
    numeros_existentes = [
        int(match.group(1)) for arq in arquivos_backup
        if (match := padrao.search(arq['title']))
    ]
    proximo_numero = max(numeros_existentes, default=0) + 1

    nome_versao = f"timesheet({proximo_numero}).csv"

    caminho_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
    df.to_csv(caminho_temp, sep=";", index=False, encoding="utf-8-sig")

    arquivo_backup = drive.CreateFile({
        'title': nome_versao,
        'parents': [{'id': pasta_backup_id}]
    })
    arquivo_backup.SetContentFile(caminho_temp)
    arquivo_backup.Upload()

# -----------------------------
# Menu Latereal
# -----------------------------

st.sidebar.title("📋 Menu")

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

    # 🔗 Carregar Dados
    df_timesheet = carregar_arquivo(
        "timesheet.csv")
    df_timesheet = normalizar_coluna_horas(df_timesheet)
    df_timesheet = tratar_coluna_data(df_timesheet)

    if df_timesheet.empty:
        st.info("⚠️ Não há dados no timesheet para gerar dashboard.")
        st.stop()
      
    # 🔢 Conversão de Horas
    def converter_para_horas(horas_str):
        try:
            h, m = map(int, horas_str.strip().split(":"))
            return h + m / 60
        except:
            return 0
    
    df_timesheet["Horas"] = df_timesheet["Horas Gastas"].apply(converter_para_horas)
    
    # 🔍 Filtros
    st.sidebar.subheader("🔍 Filtros")
    df_timesheet["Data"] = pd.to_datetime(df_timesheet["Data"], dayfirst=True, errors="coerce")
    data_inicial, data_final = st.sidebar.date_input(
        "Período:",
        [df_timesheet["Data"].min().date(), df_timesheet["Data"].max().date()]
    )
    
    empresa = st.sidebar.selectbox(
        "Empresa:",
        ["Todas"] + sorted(df_timesheet["Empresa"].dropna().unique().tolist())
    )
    
    projeto = st.sidebar.selectbox(
        "Projeto:",
        ["Todos"] + sorted(df_timesheet["Projeto"].dropna().unique().tolist())
    )

    time = st.sidebar.selectbox(
        "Time:",
        ["Todos"] + sorted(df_timesheet["Time"].dropna().unique().tolist())
    )

    atividade = st.sidebar.selectbox(
        "Atividade:",
        ["Todas"] + sorted(df_timesheet["Atividade"].dropna().unique().tolist())
    )
    
    # Aplicar filtros
    df_filtrado = df_timesheet[
        (df_timesheet["Data"].dt.date >= data_inicial) &
        (df_timesheet["Data"].dt.date <= data_final)
    ].copy()
    
    if empresa != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]
    
    if projeto != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == projeto]

    if time != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Time"] == time]

    if atividade != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Atividade"] == atividade]
    
    # 🚀 KPIs
    total_horas = df_filtrado["Horas"].sum()
    total_registros = len(df_filtrado)
    total_colaboradores = df_filtrado["Nome"].nunique()
    total_projetos = df_filtrado["Projeto"].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏰ Total de Horas", f"{total_horas:.2f}")
    col2.metric("📄 Total Registros", total_registros)
    col3.metric("👤 Colaboradores", total_colaboradores)
    col4.metric("🏗️ Projetos", total_projetos)
    
    # 📊 Gráficos
    
    # 🔸 Horas por Projeto
    st.subheader("🏗️ Horas por Projeto")
    if not df_filtrado.empty:
        grafico_projeto = df_filtrado.groupby("Projeto")["Horas"].sum().reset_index().sort_values(by="Horas", ascending=False)
        fig = px.bar(
            grafico_projeto,
            x="Projeto",
            y="Horas",
            title=None,
            text_auto='.2s'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 🔸 Horas por Time
    st.subheader("🚀 Horas por Time")
    if not df_filtrado.empty:
        grafico_time = df_filtrado.groupby("Time")["Horas"].sum().reset_index().sort_values(by="Horas", ascending=False)
        fig = px.bar(
            grafico_time,
            x="Time",
            y="Horas",
            title=None,
            text_auto='.2s'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 🔸 Horas por Atividade
    st.subheader("🗒️ Horas por Atividade")
    grafico_atividade = df_filtrado.groupby("Atividade")["Horas"].sum().reset_index().sort_values(by="Horas", ascending=False)
    fig = px.bar(
        grafico_atividade,
        x="Atividade",
        y="Horas",
        title=None,
        text_auto='.2s'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 🔸 Horas por Empresa
    st.subheader("🏢 Horas por Empresa")
    grafico_empresa = df_filtrado.groupby("Empresa")["Horas"].sum().reset_index().sort_values(by="Horas", ascending=False)
    fig = px.pie(
        grafico_empresa,
        names="Empresa",
        values="Horas",
        title=None,
        hole=0.4
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 🔸 Horas por Colaborador
    st.subheader("👤 Horas por Colaborador")
    grafico_colab = df_filtrado.groupby("Nome")["Horas"].sum().reset_index().sort_values(by="Horas", ascending=False)
    fig = px.bar(
        grafico_colab,
        x="Nome",
        y="Horas",
        title=None,
        text_auto='.2s'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 🔸 Evolução Temporal (Somente por dia, sem horas)
    st.subheader("📅 Evolução de Horas no Tempo (Por Dia)")
    
    grafico_tempo = df_filtrado.groupby(df_filtrado["Data"].dt.date)["Horas"].sum().reset_index()
    grafico_tempo.rename(columns={"Data": "Dia"}, inplace=True)
    
    fig = px.line(
        grafico_tempo,
        x="Dia",
        y="Horas",
        title=None,
        markers=True
    )
    
    fig.update_xaxes(
        type='category',
        title="Data"
    )
    
    fig.update_yaxes(title="Horas")
    
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Menu Cadastro de Empresa
# -----------------------------

elif menu == "🏢 Cadastro de Empresas":
    st.title("🏢 Cadastro de Empresas (Códigos SAP)")
    st.subheader("📥 Inserir nova empresa")

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
    st.markdown("## 🏗️ Projetos")

    df_projetos = carregar_arquivo("projetos.csv")
    
    with st.form("form_projeto"):
        nome_projeto = st.text_input("Nome do Projeto")
        descricao_projeto = st.selectbox("Time", ["Ambos", "Diretos", "Indiretos"])
        status_projeto = st.selectbox("Status do Projeto", ["Não Iniciado", "Em Andamento", "Concluído"])
    
        submitted = st.form_submit_button("💾 Salvar Projeto")
        if submitted:
            if not nome_projeto:
                st.warning("⚠️ O nome do projeto é obrigatório.")
            else:
                if nome_projeto in df_projetos["Nome Projeto"].values:
                    st.warning("⚠️ Já existe um projeto com este nome.")
                else:
                    novo = pd.DataFrame({
                        "Nome Projeto": [nome_projeto.strip()],
                        "Time": [descricao_projeto.strip()],
                        "Status": [status_projeto]
                    })
                    df_projetos = pd.concat([df_projetos, novo], ignore_index=True)
                    salvar_arquivo(df_projetos, "projetos.csv")
                    st.success("✅ Projeto cadastrado com sucesso!")
    
    st.dataframe(df_projetos, use_container_width=True)
    
    # 🛠️ Edição e Exclusão de Projeto
    st.markdown("### 🔧 Editar ou Excluir Projeto")
    if not df_projetos.empty:
        projeto_selecionado = st.selectbox("Selecione o Projeto:", df_projetos["Nome Projeto"])
    
        # Garantir índice fixo
        idx = df_projetos[df_projetos["Nome Projeto"] == projeto_selecionado].index
        if idx.empty:
            st.warning("⚠️ Projeto não encontrado.")
            st.stop()
    
        projeto_info = df_projetos.loc[idx[0]]
    
        novo_nome = st.text_input("Novo Nome do Projeto", value=projeto_info["Nome Projeto"])
        nova_desc = st.selectbox("Alterar Time", ["Ambos", "Diretos", "Indiretos"], index=["Ambos", "Diretos", "Indiretos"].index(projeto_info["Time"]))
        novo_status = st.selectbox("Novo Status", ["Não Iniciado", "Em Andamento", "Concluído"], index=["Não Iniciado", "Em Andamento", "Concluído"].index(projeto_info["Status"]))
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Atualizar Projeto"):
                df_projetos.loc[idx, "Nome Projeto"] = novo_nome.strip()
                df_projetos.loc[idx, "Time"] = nova_desc.strip()
                df_projetos.loc[idx, "Status"] = novo_status
                salvar_arquivo(df_projetos, "projetos.csv")
                st.success("✅ Projeto atualizado com sucesso!")
                st.experimental_rerun()
    
        with col2:
            if st.button("🗑️ Excluir Projeto"):
                confirmar = st.radio("⚠️ Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
                if confirmar == "Sim":
                    df_projetos = df_projetos.drop(idx)
                    salvar_arquivo(df_projetos, "projetos.csv")
                    st.success("✅ Projeto excluído com sucesso!")
                    st.experimental_rerun()
    
    # 🔸 ATIVIDADES
    st.markdown("---")
    st.markdown("## 🗒️ Atividades")
    
    df_atividades = carregar_arquivo("atividades.csv")
    
    with st.form("form_atividade"):
        nome_atividade = st.text_input("Nome da Atividade")
        projeto_vinculado = st.selectbox("Projeto Vinculado", df_projetos["Nome Projeto"])
        descricao_atividade = st.text_area("Descrição da Atividade")
        status_atividade = st.selectbox("Status da Atividade", ["Não Iniciada", "Em Andamento", "Concluída"])
    
        submitted = st.form_submit_button("💾 Salvar Atividade")
        if submitted:
            if not nome_atividade:
                st.warning("⚠️ O nome da atividade é obrigatório.")
            else:
                if nome_atividade in df_atividades["Nome Atividade"].values:
                    st.warning("⚠️ Já existe uma atividade com este nome.")
                else:
                    nova = pd.DataFrame({
                        "Nome Atividade": [nome_atividade.strip()],
                        "Projeto Vinculado": [projeto_vinculado.strip()],
                        "Descrição": [descricao_atividade.strip()],
                        "Status": [status_atividade]
                    })
                    df_atividades = pd.concat([df_atividades, nova], ignore_index=True)
                    salvar_arquivo(df_atividades, "atividades.csv")
                    st.success("✅ Atividade cadastrada com sucesso!")
    
    st.dataframe(df_atividades, use_container_width=True)
    
    # 🛠️ Edição e Exclusão de Atividade
    st.markdown("### 🔧 Editar ou Excluir Atividade")
    if not df_atividades.empty:
        atividade_selecionada = st.selectbox("Selecione a Atividade:", df_atividades["Nome Atividade"])
    
        idx = df_atividades[df_atividades["Nome Atividade"] == atividade_selecionada].index
        if idx.empty:
            st.warning("⚠️ Atividade não encontrada.")
            st.stop()
    
        atividade_info = df_atividades.loc[idx[0]]
    
        novo_nome = st.text_input("Novo Nome da Atividade", value=atividade_info["Nome Atividade"])
        novo_projeto = st.selectbox("Novo Projeto Vinculado", df_projetos["Nome Projeto"], index=df_projetos["Nome Projeto"].tolist().index(atividade_info["Projeto Vinculado"]))
        nova_desc = st.text_area("Nova Descrição", value=atividade_info["Descrição"])
        novo_status = st.selectbox("Novo Status", ["Não Iniciada", "Em Andamento", "Concluída"], index=["Não Iniciada", "Em Andamento", "Concluída"].index(atividade_info["Status"]))
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Atualizar Atividade"):
                df_atividades.loc[idx, "Nome Atividade"] = novo_nome.strip()
                df_atividades.loc[idx, "Projeto Vinculado"] = novo_projeto.strip()
                df_atividades.loc[idx, "Descrição"] = nova_desc.strip()
                df_atividades.loc[idx, "Status"] = novo_status
                salvar_arquivo(df_atividades, "atividades.csv")
                st.success("✅ Atividade atualizada com sucesso!")
                st.experimental_rerun()
    
        with col2:
            if st.button("🗑️ Excluir Atividade"):
                confirmar = st.radio("⚠️ Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
                if confirmar == "Sim":
                    df_atividades = df_atividades.drop(idx)
                    salvar_arquivo(df_atividades, "atividades.csv")
                    st.success("✅ Atividade excluída com sucesso!")
                    st.experimental_rerun()

# -----------------------------
# Menu Lançamento TS
# -----------------------------

elif menu == "📝 Lançamento de Timesheet":
    st.title("📝 Lançamento de Timesheet")
    st.subheader("⏱️ Registro de Horas")

    usuario_logado = st.session_state.username
    nome_usuario = users[usuario_logado]["name"]

    # 🔸 Carregar Bases
    df_empresas = carregar_arquivo("empresas.csv")
    df_projetos = carregar_arquivo("projetos.csv")
    df_atividades = carregar_arquivo("atividades.csv")
    df_timesheet = carregar_arquivo(
        "timesheet.csv")
    df_timesheet = normalizar_coluna_horas(df_timesheet)
    df_timesheet = tratar_coluna_data(df_timesheet)

    # 🔸 Seleção de Projeto e Atividade
    projeto = st.selectbox(
        "Projeto",
        sorted(df_projetos["Nome Projeto"].unique()) if not df_projetos.empty else ["Sem projetos cadastrados"]
    )
    
    df_atividades_filtrado = df_atividades[df_atividades["Projeto Vinculado"] == projeto]
    atividade = st.selectbox(
        "Atividade",
        sorted(df_atividades_filtrado["Nome Atividade"].unique()) if not df_atividades_filtrado.empty else ["Sem atividades para este projeto"]
    )

    time_opcao = st.selectbox(
        "Time",
        sorted(df_projetos[df_projetos["Nome Projeto"] == projeto]["Time"].unique()) if not df_projetos.empty else ["Sem projetos cadastrados"]
    )

    # 🔸 Formulário de Lançamento
    with st.form("form_timesheet"):
        data = st.date_input("Data", value=date.today())

        empresa = st.selectbox(
            "Empresa (Código SAP)",
            sorted(df_empresas["Codigo SAP"].unique()) if not df_empresas.empty else ["Sem empresas cadastradas"]
        )

        quantidade = st.number_input("Quantidade Tarefas", min_value=0, step=1)

        tempo = st.time_input("Horas Gastas", value=time(0, 0)) 
        horas = f"{tempo.hour:02d}:{tempo.minute:02d}"

        observacoes = st.text_area(
            "Observações", 
            placeholder="Descreva detalhes relevantes sobre este lançamento...",
            height=120,
            max_chars=500
        ).replace('\n', ' ') \
         .replace(';', ',') \
         .strip()

        submitted = st.form_submit_button("💾 Registrar")

        if submitted:
            if horas == "00:00":
                st.warning("⚠️ O campo Horas Gastas não pode ser 00:00.")
            else:
                novo = pd.DataFrame({
                    "Usuário": [usuario_logado],
                    "Nome": [nome_usuario],
                    "Data": [data],
                    "Empresa": [empresa],
                    "Projeto": [projeto],
                    "Time": [time_opcao],
                    "Atividade": [atividade],
                    "Quantidade": [quantidade],
                    "Horas Gastas": [horas],
                    "Observações": [observacoes.strip()]
                })
                df_timesheet = pd.concat([df_timesheet, novo], ignore_index=True)
                salvar_arquivo(df_timesheet, "timesheet.csv")
                st.success("✅ Registro salvo no Timesheet com sucesso!")

# -----------------------------
# Menu Visualizar TS
# -----------------------------

elif menu == "📄 Visualizar / Editar Timesheet":
    st.title("📄 Visualizar, Editar ou Excluir Timesheet")

    usuario_logado = st.session_state.username
    nome_usuario = users[usuario_logado]["name"]

    # 🔸 Carregar Dados
    df_timesheet = carregar_arquivo("timesheet.csv")
    df_timesheet = normalizar_coluna_horas(df_timesheet)

    # 🔧 Garantir que a coluna Data está corretamente tratada
    if "Data" in df_timesheet.columns:
        df_timesheet["Data"] = pd.to_datetime(df_timesheet["Data"], errors="coerce", dayfirst=True)
        df_timesheet = df_timesheet[df_timesheet["Data"].notnull()]

    # 🔐 Filtrar por usuário logado (não admins só veem seus dados)
    if usuario_logado not in admin_users:
        df_timesheet = df_timesheet[df_timesheet["Usuário"] == usuario_logado]

    # 🔍 Filtros na sidebar
    st.sidebar.subheader("🔍 Filtros")

    data_inicial, data_final = st.sidebar.date_input(
        "Período:",
        [
            df_timesheet["Data"].min().date() if not df_timesheet.empty else date.today(),
            df_timesheet["Data"].max().date() if not df_timesheet.empty else date.today()
        ]
    )

    empresa = st.sidebar.selectbox(
        "Empresa:",
        ["Todas"] + sorted(df_timesheet["Empresa"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todas"]
    )

    projeto = st.sidebar.selectbox(
        "Projeto:",
        ["Todos"] + sorted(df_timesheet["Projeto"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todos"]
    )

    time = st.sidebar.selectbox(
        "Time:",
        ["Todos"] + sorted(df_timesheet["Time"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todos"]
    )

    atividade = st.sidebar.selectbox(
        "Atividade:",
        ["Todas"] + sorted(df_timesheet["Atividade"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todas"]
    )

    if usuario_logado in admin_users:
        usuario = st.sidebar.selectbox(
            "Nome:",
            ["Todos"] + sorted(df_timesheet["Nome"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todos"]
        )
    else:
        usuario = usuario_logado

    # 🔸 Aplicar filtros
    df_filtrado = df_timesheet.copy()

    if empresa != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]

    if projeto != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == projeto]

    if time != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Time"] == time]

    if atividade != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Atividade"] == atividade]

    if usuario != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Usuário"] == usuario]

    # 🔍 Filtro de período
    df_filtrado = df_filtrado[
        (df_filtrado["Data"].dt.date >= data_inicial) &
        (df_filtrado["Data"].dt.date <= data_final)
    ].sort_values(by="Data")

    # 🔸 Visualização
    df_visual = df_filtrado.copy()
    df_visual["Data"] = df_visual["Data"].dt.strftime("%d/%m/%Y")

    st.markdown(f"### 🔍 {len(df_visual)} registros encontrados")

    if df_visual.empty:
        st.info("🚩 Nenhum registro encontrado com os filtros aplicados.")
    else:
        st.dataframe(df_visual, use_container_width=True)

    # 🔸 Edição de Registro
    st.markdown("---")
    st.subheader("✏️ Editar um Registro")

    if not df_filtrado.empty:
        indice = st.selectbox("Selecione o índice para editar:", df_filtrado.index.tolist())

        linha = df_filtrado.loc[indice]

        col_editar = st.selectbox("Coluna:", [
            "Data", "Nome", "Empresa", "Projeto", "Atividade", "Quantidade", "Horas Gastas", "Observações"
        ])

        valor_atual = linha[col_editar]

        if col_editar == "Data":
            novo_valor = st.date_input(
                "Nova Data",
                value=valor_atual.date() if pd.notnull(valor_atual) else date.today()
            )
            st.markdown(f"📅 Data selecionada: **{novo_valor.strftime('%d/%m/%Y')}**")
            novo_valor = pd.to_datetime(novo_valor)

        elif col_editar == "Quantidade":
            novo_valor = st.number_input(
                "Nova Quantidade",
                value=int(valor_atual) if pd.notnull(valor_atual) else 0
            )

        else:
            novo_valor = st.text_input(
                "Novo Valor",
                value=str(valor_atual) if pd.notnull(valor_atual) else ""
            )

        if st.button("💾 Atualizar Registro"):
            df_timesheet.at[indice, col_editar] = novo_valor
            salvar_arquivo(df_timesheet, "timesheet.csv")
            st.success(f"✅ Registro atualizado com sucesso!")
            st.experimental_rerun()

    # 🔸 Exclusão de Registro
    st.markdown("---")
    st.subheader("🗑️ Excluir um Registro")

    if not df_filtrado.empty:
        indice_excluir = st.selectbox("Índice para excluir:", df_filtrado.index.tolist(), key="excluir")

        linha = df_filtrado.loc[indice_excluir]
        st.markdown("**Registro selecionado:**")
        st.json(linha.to_dict())

        confirmar = st.radio("⚠️ Confirmar Exclusão?", ["Não", "Sim"], horizontal=True, key="confirmar_excluir")

        if confirmar == "Sim":
            if st.button("🗑️ Confirmar Exclusão"):
                df_timesheet = df_timesheet.drop(index=indice_excluir)
                salvar_arquivo(df_timesheet, "timesheet.csv")
                st.success("✅ Registro excluído com sucesso!")
                st.experimental_rerun()

    # 🔸 Exportação dos Dados
    st.markdown("---")
    st.subheader("📥 Exportar Dados")

    df_export = df_filtrado.copy()
    df_export["Data"] = df_export["Data"].dt.strftime("%d/%m/%Y")

    buffer = df_export.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()

    st.download_button(
        label="📥 Baixar Tabela",
        data=buffer,
        file_name="timesheet_filtrado.csv",
        mime="text/csv"
    )

# -----------------------------
# Menu Performance
# -----------------------------

elif menu == "📊 Avaliação de Performance — IA":
    st.title("📊 Avaliação de Performance com IA")

    # 🔐 Definir admins
    usuario_logado = st.session_state.username
    
    # 🔗 Carregar Dados
    df_timesheet = carregar_arquivo(
        "timesheet.csv")
    df_timesheet = normalizar_coluna_horas(df_timesheet)
    
    if df_timesheet.empty:
        st.info("⚠️ Não há dados no timesheet para avaliar.")
        st.stop()
    
    # Tratamento de datas
    df_timesheet["Data"] = pd.to_datetime(df_timesheet["Data"], errors="coerce")
    
    # 🔐 Controle de Permissão
    if usuario_logado not in admin_users:
        st.error("🚫 Você não tem permissão para acessar a Avaliação de Performance.")
        st.stop()
    
    # 🔍 Filtro por Projeto
    st.markdown("### 🤖 Gerando relatório com IA")
    
    lista_projetos = sorted(df_timesheet["Projeto"].dropna().unique().tolist())
    projeto_escolhido = st.selectbox(
        "Selecione o Projeto para análise:",
        ["Todos os Projetos"] + lista_projetos
    )
    
    # Aplicar filtro
    if projeto_escolhido != "Todos os Projetos":
        df_filtrado = df_timesheet[df_timesheet["Projeto"] == projeto_escolhido]
    else:
        df_filtrado = df_timesheet.copy()
    
    if df_filtrado.empty:
        st.info("⚠️ Nenhum registro encontrado para o projeto selecionado.")
        st.stop()
    
    # 🤖 Cliente OpenAI
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    
    # 🔥 Geração do Relatório
    dados_markdown = df_filtrado.fillna("").astype(str).to_markdown(index=False)
    
    prompt = f"""
    Você é um consultor especialista em gestão de tempo, produtividade e análise de performance.
    
    Analise os dados do timesheet abaixo e gere um relatório completo e estruturado contendo:
    - ✅ Resumo executivo
    - ✅ Principais indicadores
    - ✅ Gargalos e desvios
    - ✅ Recomendações de melhorias operacionais
    - ✅ Conclusões finais
    
    Seja objetivo, técnico e claro. Utilize contagens, percentuais e análises de tendência.
    
    ### Dados do Timesheet:
    {dados_markdown}
    """
    
    if st.button("🚀 Gerar Relatório de Performance"):
        with st.spinner("A IA está gerando o relatório..."):
            resposta = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise de produtividade corporativa e performance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
    
            texto_relatorio = resposta.choices[0].message.content
    
            st.success("✅ Relatório gerado com sucesso!")
            st.markdown("### 📄 Relatório Gerado:")
            st.markdown(texto_relatorio)
    
            # =============================
            # 📄 Gerar Arquivo .docx
            # =============================
            doc = Document()
    
            # Estilo
            style = doc.styles["Normal"]
            font = style.font
            font.name = 'Arial'
            font.size = Pt(11)
    
            doc.add_heading("📊 Relatório de Avaliação de Performance", level=1)
    
            if projeto_escolhido == "Todos os Projetos":
                doc.add_paragraph("Projeto: Todos os Projetos")
            else:
                doc.add_paragraph(f"Projeto: {projeto_escolhido}")
    
            doc.add_paragraph(f"Data da geração: {datetime.today().strftime('%Y-%m-%d')}")
    
            doc.add_paragraph("\n")
    
            for linha in texto_relatorio.split("\n"):
                if linha.strip().startswith("#"):
                    nivel = linha.count("#")
                    texto = linha.replace("#", "").strip()
                    doc.add_heading(texto, level=min(nivel, 4))
                else:
                    doc.add_paragraph(linha.strip())
    
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
    
            st.download_button(
                label="📥 Baixar Relatório em Word",
                data=buffer,
                file_name="relatorio_performance.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
