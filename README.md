# Timesheet Fiscal — Documentação Técnica
## 🚀 Visão Geral
O **Timesheet Fiscal** é um aplicativo desenvolvido em **Python com Streamlit**, integrado à **OpenAI GPT-4o** e ao **Google Drive**, que permite controle, análise e gestão de horas por projetos, atividades e empresas.

Ele possui funcionalidades que vão além do simples controle de horas, oferecendo dashboards interativos, análises inteligentes com IA e geração de relatórios profissionais.

## 🏗️ Arquitetura do Projeto

```
timesheet_fiscal/
├── app.py
├── modules/
│   ├── drive_utils.py
│   ├── auth_utils.py
│   ├── timesheet_utils.py
├── pages/
│   ├── 1_Cadastro_de_Empresas.py
│   ├── 2_Cadastro_de_Projetos.py
│   ├── 3_Lancamento_Timesheet.py
│   ├── 4_Visualizacao_Timesheet.py
│   ├── 5_Dashboard.py
│   └── 6_Avaliacao_Performance_IA.py
├── README.md
├── requirements.txt
└── .streamlit/
```

## 🔗 Integrações

- ☁️ **Google Drive API:** Armazena as bases de dados na nuvem, em uma pasta chamada `ts-fiscal`.
- 🤖 **OpenAI GPT-4o:** Realiza análises inteligentes dos dados, gerando relatórios automáticos de performance.
- 🖥️ **Streamlit:** Interface web leve e interativa, sem necessidade de servidores complexos.

## 🗂️ Bases de Dados

| Arquivo          | Descrição                                           |
|------------------|-----------------------------------------------------|
| empresas.csv     | Cadastro de empresas e códigos SAP                 |
| projetos.csv     | Cadastro de projetos                               |
| atividades.csv   | Cadastro de atividades vinculadas aos projetos     |
| timesheet.csv    | Registros de horas lançadas pelos usuários         |
| usuarios (secrets.toml) | Usuários e senhas armazenados no secrets     |

## 🔐 Controle de Acesso

- ✅ **Login:** Usuário e senha validados via arquivo `secrets.toml`.
- 🔑 **Permissões:**
  - **Administradores:** Acesso completo a todos os dados e funcionalidades.
  - **Usuários comuns:** Podem visualizar, editar e excluir **apenas seus próprios lançamentos**.

## 🧠 Funcionalidades

### 1. 🏢 Cadastro de Empresas
- Cadastra empresas e códigos SAP.
- CRUD completo (Criar, Editar, Excluir).

### 2. 🏗️ Cadastro de Projetos e Atividades
- Permite criar projetos com status.
- Vincula atividades a projetos.

### 3. 📝 Lançamento de Timesheet
- Registro de:
  - Data
  - Empresa
  - Projeto
  - Atividade
  - Quantidade
  - Horas gastas (HH:MM)
  - Observações
- Dados são salvos automaticamente no Google Drive.

### 4. 📄 Visualizar, Editar e Excluir Timesheet
- Filtros por:
  - Data
  - Empresa
  - Projeto
  - Atividade
  - Colaborador (nome)
- Permite exportação para CSV.

### 5. 📊 Dashboard
- KPIs:
  - Total de horas
  - Total de registros
  - Total de projetos
  - Total de colaboradores
- Gráficos:
  - 📅 Evolução temporal
  - 🏗️ Horas por projeto
  - 🏢 Horas por empresa
  - 🗒️ Horas por atividade
  - 👤 Horas por colaborador
- Filtros por período, projeto e empresa.

### 6. 🤖 Avaliação de Performance com IA
- Disponível **somente para administradores**.
- Gera relatórios executivos com IA:
  - Resumo executivo
  - Principais indicadores
  - Gargalos operacionais
  - Recomendações de melhoria
- Exportação em **Word (.docx)**.

## 🏛️ Arquitetura Técnica

- **Frontend:**  
  - Streamlit  
  - Plotly (Dashboards)  
  - Docx (Relatórios)

- **Backend:**  
  - Google Drive API (Persistência)  
  - OpenAI GPT-4o (Inteligência Artificial)

- **Persistência:**  
  - Arquivos CSV no Google Drive (`ts-fiscal`)

- **Autenticação:**  
  - Usuários e senhas no arquivo `secrets.toml`

## 🔧 Requisitos

### 🐍 Python 3.9+

### 📦 requirements.txt

```
streamlit==1.35.0
pandas==2.2.2
pydrive2==1.19.0
oauth2client==4.1.3
plotly==5.21.0
yagmail==0.15.293
openai==1.30.1
python-docx==1.1.2
httpx==0.27.0
matplotlib==3.8.4
```

## 🚀 Deploy Local

```
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy na Nuvem (Streamlit Cloud)

1. Suba o projeto no GitHub.
2. Crie um arquivo `.streamlit/secrets.toml` com as credenciais:

```
[credentials]
access_token = "..."
client_id = "..."
client_secret = "..."
refresh_token = "..."
token_expiry = "..."
token_uri = "https://oauth2.googleapis.com/token"
revoke_uri = "https://oauth2.googleapis.com/revoke"

[openai]
api_key = "..."
```

## 🔐 Segurança

- As credenciais de acesso ao Google Drive e OpenAI são armazenadas de forma segura no arquivo `secrets.toml`.
- Controle robusto de acesso por usuário e perfil (admin ou comum).

## ✍️ Autores

- 👤 **Claudio Paiva** — Desenvolvimento, Arquitetura e Implementação.

## ✅ Licença

Este projeto é de uso interno e controlado pela organização **Prio**.
