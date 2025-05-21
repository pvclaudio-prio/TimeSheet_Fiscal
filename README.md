# Timesheet Fiscal — Documentação Técnica
🚀 Visão Geral
O Timesheet Fiscal é um aplicativo desenvolvido em Python com Streamlit, integrado à OpenAI GPT-4o e ao Google Drive, que permite controle, análise e gestão de horas por projetos, atividades e empresas.
🏗️ Arquitetura do Projeto
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
🔗 Integrações
- Google Drive API
- OpenAI GPT-4o
- Streamlit
🗂️ Bases de Dados
- empresas.csv
- projetos.csv
- atividades.csv
- timesheet.csv
- usuarios (secrets.toml)
🔐 Controle de Acesso
- Login por usuário e senha
- Permissão diferenciada para admins e usuários comuns
🧠 Funcionalidades
1. Cadastro de Empresas
2. Cadastro de Projetos e Atividades
3. Lançamento de Timesheet
4. Visualização, Edição e Exclusão
5. Dashboard Interativo
6. Avaliação de Performance com IA
🏛️ Arquitetura Técnica
- Frontend: Streamlit + Plotly + Docx
- Backend: Google Drive API + OpenAI GPT-4o
- Persistência: Arquivos CSV
- Autenticação: secrets.toml
🔧 Requisitos
Python 3.9+
requirements.txt
🚀 Deploy Local
pip install -r requirements.txt
streamlit run app.py
☁️ Deploy na Nuvem (Streamlit Cloud)
- GitHub + secrets.toml
🔐 Segurança
- Credenciais protegidas no secrets.toml
✍️ Autores
- Claudio Paiva
✅ Licença
- Uso interno da Prio

