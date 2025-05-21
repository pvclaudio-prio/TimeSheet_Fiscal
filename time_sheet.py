import streamlit as st
import pandas as pd
import tempfile
from datetime import datetime, date
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import OAuth2Credentials
import httplib2
import openai
from io import BytesIO
from docx import Document
from docx.shared import Pt

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
    
admin_users = ["cvieira", "mathayde", "amendonca"]

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

    http = httplib2.Http()

    try:
        credentials.refresh(http)
    except Exception as e:
        st.error(f"Erro ao atualizar credenciais: {e}")

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

def carregar_arquivo(nome_arquivo, colunas):
    drive = conectar_drive()
    pasta_id = obter_pasta_ts_fiscal(drive)

    arquivos = drive.ListFile({
        'q': f"'{pasta_id}' in parents and title = '{nome_arquivo}' and trashed=false"
    }).GetList()

    if not arquivos:
        df = pd.DataFrame(columns=colunas)
        df.to_csv(nome_arquivo, sep=";", index=False, encoding="utf-8-sig")
        arquivo = drive.CreateFile({
            'title': nome_arquivo,
            'parents': [{'id': pasta_id}]
        })
        arquivo.SetContentFile(nome_arquivo)
        arquivo.Upload()
        return df

    caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
    arquivos[0].GetContentFile(caminho_temp)
    df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
    return df

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

    df_projetos = carregar_arquivo("projetos.csv", ["Nome Projeto", "Descrição", "Status"])
    
    with st.form("form_projeto"):
        nome_projeto = st.text_input("Nome do Projeto")
        descricao_projeto = st.text_area("Descrição do Projeto")
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
                        "Descrição": [descricao_projeto.strip()],
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
    
        projeto_info = df_projetos[df_projetos["Nome Projeto"] == projeto_selecionado].iloc[0]
    
        novo_nome = st.text_input("Novo Nome do Projeto", value=projeto_info["Nome Projeto"])
        nova_desc = st.text_area("Nova Descrição", value=projeto_info["Descrição"])
        novo_status = st.selectbox("Novo Status", ["Não Iniciado", "Em Andamento", "Concluído"], index=["Não Iniciado", "Em Andamento", "Concluído"].index(projeto_info["Status"]))
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Atualizar Projeto"):
                df_projetos.loc[df_projetos["Nome Projeto"] == projeto_selecionado, "Nome Projeto"] = novo_nome.strip()
                df_projetos.loc[df_projetos["Nome Projeto"] == projeto_selecionado, "Descrição"] = nova_desc.strip()
                df_projetos.loc[df_projetos["Nome Projeto"] == projeto_selecionado, "Status"] = novo_status
                salvar_arquivo(df_projetos, "projetos.csv")
                st.success("✅ Projeto atualizado com sucesso!")
                st.experimental_rerun()
    
        with col2:
            if st.button("🗑️ Excluir Projeto"):
                confirmar = st.radio("⚠️ Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
                if confirmar == "Sim":
                    df_projetos = df_projetos[df_projetos["Nome Projeto"] != projeto_selecionado]
                    salvar_arquivo(df_projetos, "projetos.csv")
                    st.success("✅ Projeto excluído com sucesso!")
                    st.experimental_rerun()
    
    # 🔸 ATIVIDADES
    st.markdown("---")
    st.markdown("## 🗒️ Atividades")
    
    df_atividades = carregar_arquivo("atividades.csv", ["Nome Atividade", "Projeto Vinculado", "Descrição", "Status"])
    
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
    
        atividade_info = df_atividades[df_atividades["Nome Atividade"] == atividade_selecionada].iloc[0]
    
        novo_nome = st.text_input("Novo Nome da Atividade", value=atividade_info["Nome Atividade"])
        novo_projeto = st.selectbox("Novo Projeto Vinculado", df_projetos["Nome Projeto"], index=df_projetos["Nome Projeto"].tolist().index(atividade_info["Projeto Vinculado"]))
        nova_desc = st.text_area("Nova Descrição", value=atividade_info["Descrição"])
        novo_status = st.selectbox("Novo Status", ["Não Iniciada", "Em Andamento", "Concluída"], index=["Não Iniciada", "Em Andamento", "Concluída"].index(atividade_info["Status"]))
    
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✏️ Atualizar Atividade"):
                df_atividades.loc[df_atividades["Nome Atividade"] == atividade_selecionada, "Nome Atividade"] = novo_nome.strip()
                df_atividades.loc[df_atividades["Nome Atividade"] == atividade_selecionada, "Projeto Vinculado"] = novo_projeto.strip()
                df_atividades.loc[df_atividades["Nome Atividade"] == atividade_selecionada, "Descrição"] = nova_desc.strip()
                df_atividades.loc[df_atividades["Nome Atividade"] == atividade_selecionada, "Status"] = novo_status
                salvar_arquivo(df_atividades, "atividades.csv")
                st.success("✅ Atividade atualizada com sucesso!")
                st.experimental_rerun()
    
        with col2:
            if st.button("🗑️ Excluir Atividade"):
                confirmar = st.radio("⚠️ Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
                if confirmar == "Sim":
                    df_atividades = df_atividades[df_atividades["Nome Atividade"] != atividade_selecionada]
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
    df_empresas = carregar_arquivo("empresas.csv", ["Codigo SAP", "Nome Empresa", "Descrição"])
    df_projetos = carregar_arquivo("projetos.csv", ["Nome Projeto", "Descrição", "Status"])
    df_atividades = carregar_arquivo("atividades.csv", ["Nome Atividade", "Projeto Vinculado", "Descrição", "Status"])
    df_timesheet = carregar_arquivo(
        "timesheet.csv",
        ["Usuário","Nome", "Data", "Empresa", "Projeto", "Atividade", "Quantidade", "Horas Gastas", "Observações"]
    )
    
    # 🔸 Formulário de Lançamento
    with st.form("form_timesheet"):
        data = st.date_input("Data", value=date.today())
    
        empresa = st.selectbox(
            "Empresa (Código SAP)",
            df_empresas["Codigo SAP"] if not df_empresas.empty else ["Sem empresas cadastradas"]
        )
    
        projeto = st.selectbox(
            "Projeto",
            df_projetos["Nome Projeto"] if not df_projetos.empty else ["Sem projetos cadastrados"]
        )
    
        atividades_filtradas = df_atividades[df_atividades["Projeto Vinculado"] == projeto]
    
        atividade = st.selectbox(
            "Atividade",
            atividades_filtradas["Nome Atividade"] if not atividades_filtradas.empty else ["Sem atividades para este projeto"]
        )
    
        quantidade = st.number_input("Quantidade Horas", min_value=0, step=1)
    
        horas = st.text_input("Horas Gastas (formato HH.MM)")
    
        observacoes = st.text_area("Observações", placeholder="Descreva detalhes relevantes sobre este lançamento...")
    
        submitted = st.form_submit_button("💾 Registrar")
    
        if submitted:
            if not horas.strip():
                st.warning("⚠️ O campo Horas Gastas é obrigatório no formato HH:MM.")
            else:
                novo = pd.DataFrame({
                    "Usuário": [usuario_logado],
                    "Nome":[nome_usuario],
                    "Data": [data.strftime("%Y-%m-%d")],
                    "Empresa": [empresa],
                    "Projeto": [projeto],
                    "Atividade": [atividade],
                    "Quantidade": [quantidade],
                    "Horas Gastas": [horas.strip()],
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
    df_timesheet = carregar_arquivo(
        "timesheet.csv",
        ["Usuário", "Data", "Empresa", "Projeto", "Atividade", "Quantidade", "Horas Gastas", "Observações"]
    )
    
    # 🔧 Tratamento de datas
    if not df_timesheet.empty:
        df_timesheet["Data"] = pd.to_datetime(df_timesheet["Data"], errors="coerce")
    
    # 🔐 Filtrar por usuário logado
    usuario_logado = st.session_state.username
    
    if usuario_logado not in admin_users:
        df_timesheet = df_timesheet[df_timesheet["Usuário"] == usuario_logado]
    
    # 🔍 Filtros
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
        ["Todas"] + sorted(df_timesheet["Projeto"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todas"]
    )
    
    atividade = st.sidebar.selectbox(
        "Atividade:",
        ["Todas"] + sorted(df_timesheet["Atividade"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todas"]
    )
    
    # Filtro de usuário (apenas admins veem)
    if usuario_logado in admin_users:
        usuario = st.sidebar.selectbox(
            "Nome:",
            ["Todos"] + sorted(df_timesheet["Nome"].dropna().unique().tolist()) if not df_timesheet.empty else ["Todos"]
        )
    else:
        usuario = usuario_logado
    
    # 🔸 Aplicando filtros
    df_filtrado = df_timesheet.copy()
    
    if empresa != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]
    
    if projeto != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Projeto"] == projeto]
    
    if atividade != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Atividade"] == atividade]
    
    if usuario != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Nome"] == usuario]
    
    df_filtrado = df_filtrado[
        (df_filtrado["Data"].dt.date >= data_inicial) &
        (df_filtrado["Data"].dt.date <= data_final)
    ].sort_values(by="Data")
    
    # 🔸 Visualização
    st.markdown(f"### 🔍 {len(df_filtrado)} registros encontrados")
    st.dataframe(df_filtrado, use_container_width=True)
    
    # 🔸 Edição
    st.markdown("---")
    st.subheader("✏️ Editar um Registro")
    
    if not df_filtrado.empty:
        indice = st.selectbox("Selecione o índice para editar:", df_filtrado.index.tolist())
    
        linha = df_filtrado.loc[indice]
    
        col_editar = st.selectbox("Coluna:", [
            "Data", "Empresa", "Projeto", "Atividade", "Quantidade", "Horas Gastas", "Observações"
        ])
    
        valor_atual = linha[col_editar]
        if col_editar == "Data":
            novo_valor = st.date_input("Nova Data", value=valor_atual.date() if pd.notnull(valor_atual) else date.today())
            novo_valor = pd.to_datetime(novo_valor)
        elif col_editar == "Quantidade":
            novo_valor = st.number_input("Nova Quantidade", value=int(valor_atual) if pd.notnull(valor_atual) else 0)
        else:
            novo_valor = st.text_input("Novo Valor", value=str(valor_atual) if pd.notnull(valor_atual) else "")
    
        if st.button("💾 Atualizar Registro"):
            df_timesheet.at[indice, col_editar] = novo_valor
            salvar_arquivo(df_timesheet, "timesheet.csv")
            st.success(f"✅ Registro atualizado com sucesso!")
            st.experimental_rerun()
    
    # 🔸 Exclusão
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
    
    # 🔸 Exportação
    st.markdown("---")
    st.subheader("📥 Exportar Dados")
    
    buffer = df_filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
    
    st.download_button(
        label="📥 Baixar CSV Filtrado",
        data=buffer,
        file_name="timesheet_filtrado.csv",
        mime="text/csv"
    )

# -----------------------------
# Menu Performance
# -----------------------------

elif menu == "📊 Avaliação de Performance — IA":
    st.title("📊 Avaliação de Performance com IA")
    # =============================
# 🔑 API OpenAI
# =============================
openai.api_key = st.secrets["openai"]["api_key"]


# =============================
# 🔗 Carregar Dados
# =============================
st.subheader("📊 Avaliação de Performance — IA")

df_timesheet = carregar_arquivo(
    "timesheet.csv",
    ["Usuário", "Nome", "Data", "Empresa", "Projeto", "Atividade", "Quantidade", "Horas Gastas", "Observações"]
)

if df_timesheet.empty:
    st.info("⚠️ Não há dados no timesheet para avaliar.")
    st.stop()

# Tratamento de datas
df_timesheet["Data"] = pd.to_datetime(df_timesheet["Data"], errors="coerce")

# =============================
# 🔍 Prompt para GPT
# =============================
st.markdown("### 🔧 Configuração da Avaliação")

periodo_inicio, periodo_fim = st.date_input(
    "Período da análise:",
    [df_timesheet["Data"].min().date(), df_timesheet["Data"].max().date()]
)

df_filtrado = df_timesheet[
    (df_timesheet["Data"].dt.date >= periodo_inicio) &
    (df_timesheet["Data"].dt.date <= periodo_fim)
]

if df_filtrado.empty:
    st.info("⚠️ Nenhum registro encontrado para o período selecionado.")
    st.stop()

    # 🔥 Geração do Relatório
    st.markdown("### 🤖 Gerando relatório com IA")
    
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
            resposta = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise de dados e produtividade corporativa."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
    
            texto_relatorio = resposta.choices[0].message["content"]
    
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
            doc.add_paragraph(f"Período: {periodo_inicio} a {periodo_fim}")
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



