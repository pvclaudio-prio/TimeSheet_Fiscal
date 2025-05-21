import streamlit as st
import pandas as pd
import tempfile
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.client import OAuth2Credentials
from datetime import datetime


st.set_page_config(page_title="Cadastro de Empresas", layout="wide")
st.write("Hoje:", pd.Timestamp.today())

# Funções auxiliares
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

# -----------------------------
# Layout da Página
# -----------------------------
st.sidebar.image("PRIO_SEM_POLVO_PRIO_PANTONE_LOGOTIPO_Azul.png")
st.title("🏢 Cadastro de Empresas (Códigos SAP)")

st.subheader("📥 Inserir nova empresa")
with st.form("form_empresa"):
    codigo = st.text_input("Código SAP")
    nome = st.text_input("Nome da Empresa")
    descricao = st.text_area("Descrição", placeholder="Informações adicionais (opcional)")

    submitted = st.form_submit_button("💾 Salvar Empresa")
    if submitted:
        if not codigo or not nome:
            st.warning("⚠️ Código SAP e Nome são obrigatórios!")
        else:
            df = carregar_empresas()
            if codigo in df["Codigo SAP"].values:
                st.warning("⚠️ Já existe uma empresa com esse Código SAP.")
            else:
                nova_empresa = pd.DataFrame({
                    "Codigo SAP": [codigo.strip()],
                    "Nome Empresa": [nome.strip()],
                    "Descrição": [descricao.strip()]
                })
                df = pd.concat([df, nova_empresa], ignore_index=True)
                salvar_empresas(df)
                st.success("✅ Empresa cadastrada com sucesso!")

st.subheader("🏢 Empresas Cadastradas")
df_empresas = carregar_empresas()

st.dataframe(df_empresas, use_container_width=True)

st.subheader("🛠️ Editar ou Excluir Empresa")
if not df_empresas.empty:
    empresa_selecionada = st.selectbox("Selecione a empresa pelo Código SAP:", df_empresas["Codigo SAP"])

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
            confirmar = st.radio("Tem certeza que deseja excluir?", ["Não", "Sim"], horizontal=True)
            if confirmar == "Sim":
                df_empresas = df_empresas[df_empresas["Codigo SAP"] != empresa_selecionada]
                salvar_empresas(df_empresas)
                st.success("✅ Empresa excluída com sucesso!")
                st.experimental_rerun()
else:
    st.info("Nenhuma empresa cadastrada até o momento.")

