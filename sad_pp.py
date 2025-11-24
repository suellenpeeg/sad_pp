import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fpdf import FPDF

# --- Configuração da Página ---
st.set_page_config(
    page_title="SAD Fábrica de Tecidos",
    layout="wide"
)

st.title("SAD Fábrica de Tecidos - Gestão de Pedidos e Produção")

# --------------------------
# Controle de acesso
# --------------------------
st.sidebar.header("Login")
usuario = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")

usuarios_validos = {
    "admin": {"senha": "1234", "acesso_ate": datetime(2025, 12, 31)},
    "usuario1": {"senha": "abcd", "acesso_ate": datetime(2025, 11, 30)}
}

acesso_autorizado = False
if usuario in usuarios_validos:
    if senha == usuarios_validos[usuario]["senha"]:
        if datetime.today() <= usuarios_validos[usuario]["acesso_ate"]:
            acesso_autorizado = True
        else:
            st.sidebar.error("⛔ Acesso expirado para este usuário.")
    else:
        st.sidebar.error("Senha incorreta.")

if not acesso_autorizado:
    st.stop()

# --------------------------
# Configuração da capacidade da fábrica
# --------------------------
NUM_MAQUINAS = 5
HORAS_POR_DIA = 8
DIAS_POR_SEMANA = 5
CAPACIDADE_SEMANAL = NUM_MAQUINAS * HORAS_POR_DIA * DIAS_POR_SEMANA

# --------------------------
# Session State para pedidos e produtos
# --------------------------
if "pedidos" not in st.session_state:
    st.session_state.pedidos = pd.DataFrame(columns=[
        "Pedido", "Produto", "Urgência", "Custo", "Tempo de Produção", "Pontuação", "Prazo", "Status"
    ])

if "produtos" not in st.session_state:
    st.session_state.produtos = pd.DataFrame([
        {"Produto": "Camiseta de Malha", "Tempo": 2},
        {"Produto": "Camiseta UV", "Tempo": 3},
        {"Produto": "Shorts de Malha", "Tempo": 2},
        {"Produto": "Calças de Malha", "Tempo": 4},
    ])

# --------------------------
# Abas principais
# --------------------------
abas = st.tabs(["Pedidos", "Produtos", "Relatórios"])

# --------------------------
# Aba 1: Pedidos
# --------------------------
with abas[0]:
    st.header("Pedidos")
    
    # Cards de resumo
    pedidos_abertos = st.session_state.pedidos[st.session_state.pedidos["Status"]=="Aberto"]
    pedidos_concluidos = st.session_state.pedidos[st.session_state.pedidos["Status"]=="Concluído"]
    pedidos_atrasados = pedidos_abertos[pedidos_abertos["Prazo"] < datetime.today().date()]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Pedidos Abertos", len(pedidos_abertos))
    col2.metric("Pedidos Concluídos", len(pedidos_concluidos))
    col3.metric("Pedidos Atrasados", len(pedidos_atrasados))
    
    # Formulário para adicionar pedidos
    st.subheader("Adicionar Novo Pedido")
    with st.form("form_novo_pedido", clear_on_submit=True):
        nome = st.text_input("Nome do Pedido")
        produto = st.selectbox("Tipo de Produto", st.session_state.produtos["Produto"].tolist())
        urgencia = st.slider("Urgência (1-10)", 1, 10, 5)
        custo = st.slider("Custo (1-10)", 1, 10, 5)
        prazo = st.date_input("Prazo de entrega", datetime.today() + timedelta(days=7))
        submit = st.form_submit_button("Adicionar Pedido")
        
        if submit and nome:
            tempo = st.session_state.produtos.loc[st.session_state.produtos["Produto"]==produto, "Tempo"].values[0]
            pontuacao = (urgencia*0.4 + (10 - tempo)*0.3 + (10 - custo)*0.3)
            novo_pedido = pd.DataFrame([{
                "Pedido": nome,
                "Produto": produto,
                "Urgência": urgencia,
                "Custo": custo,
                "Tempo de Produção": tempo,
                "Pontuação": pontuacao,
                "Prazo": prazo,
                "Status": "Aberto"
            }])
            st.session_state.pedidos = pd.concat([st.session_state.pedidos, novo_pedido], ignore_index=True)
            st.success(f"Pedido '{nome}' adicionado!")

    # Lista de pedidos abertos
    if not pedidos_abertos.empty:
        pedidos_abertos = pedidos_abertos.sort_values(by="Pontuação", ascending=False)
        st.dataframe(pedidos_abertos)
        
        st.subheader("Marcar Pedidos como Concluídos")
        for idx, row in pedidos_abertos.iterrows():
            if st.checkbox(f"Concluir Pedido: {row['Pedido']}", key=f"chk_{idx}"):
                st.session_state.pedidos.at[idx, "Status"] = "Concluído"
                st.experimental_rerun()
        
        # Gráfico de prioridade
        fig1 = px.bar(pedidos_abertos, x="Pedido", y="Pontuação", color="Urgência",
                      title="Prioridade dos Pedidos")
        st.plotly_chart(fig1)
        
        # Gráfico de capacidade
        st.subheader("Capacidade Semanal")
        horas_totais = pedidos_abertos["Tempo de Produção"].sum()
        df_capacidade = pd.DataFrame({
            "Tipo": ["Horas Planejadas", "Capacidade Total"],
            "Horas": [horas_totais, CAPACIDADE_SEMANAL]
        })
        fig2 = px.bar(df_capacidade, x="Tipo", y="Horas", color="Tipo", text="Horas")
        st.plotly_chart(fig2)
        
        # Alertas de prazo
        st.subheader("Alertas de Prazo")
        proximos_alerta = pedidos_abertos[(pedidos_abertos["Prazo"] - timedelta(days=3)) <= datetime.today().date()]
        if not proximos_alerta.empty:
            st.warning(f"⏰ Pedidos próximos do prazo: {', '.join(proximos_alerta['Pedido'].tolist())}")
        
        # Exportar PDF
        st.subheader("Exportar PDF da Ordem de Produção")
        if st.button("Gerar PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Ordem de Produção - Pedidos Abertos", ln=True, align="C")
            pdf.ln(10)
            for idx, row in pedidos_abertos.iterrows():
                pdf.cell(0, 10, txt=f"Pedido: {row['Pedido']}, Produto: {row['Produto']}, Urgência: {row['Urgência']}, Tempo: {row['Tempo de Produção']}h, Custo: {row['Custo']}, Prazo: {row['Prazo']}", ln=True)
            pdf_file = "ordem_producao.pdf"
            pdf.output(pdf_file)
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", f, file_name=pdf_file)
    else:
        st.info("Nenhum pedido aberto no momento.")

# --------------------------
# Aba 2: Produtos
# --------------------------
with abas[1]:
    st.header("Produtos")
    
    # Formulário para adicionar novo produto
    st.subheader("Adicionar/Editar Produto")
    with st.form("form_produto", clear_on_submit=True):
        produto_nome = st.text_input("Nome do Produto")
        tempo_prod = st.number_input("Tempo de Produção (horas)", min_value=0, value=1)
        submit_prod = st.form_submit_button("Salvar Produto")
        
        if submit_prod and produto_nome:
            if produto_nome in st.session_state.produtos["Produto"].tolist():
                st.session_state.produtos.loc[st.session_state.produtos["Produto"]==produto_nome, "Tempo"] = tempo_prod
                st.success(f"Produto '{produto_nome}' atualizado!")
            else:
                st.session_state.produtos = pd.concat([st.session_state.produtos, pd.DataFrame([{"Produto": produto_nome, "Tempo": tempo_prod}])], ignore_index=True)
                st.success(f"Produto '{produto_nome}' adicionado!")
    
    st.dataframe(st.session_state.produtos)

# --------------------------
# Aba 3: Relatórios
# --------------------------
with abas[2]:
    st.header("Relatórios por Período")
    
    st.subheader("Selecionar Período")
    data_inicio = st.date_input("Data Início", datetime.today() - timedelta(days=30))
    data_fim = st.date_input("Data Fim", datetime.today())
    
    df_periodo = st.session_state.pedidos[(st.session_state.pedidos["Prazo"] >= data_inicio) &
                                         (st.session_state.pedidos["Prazo"] <= data_fim)]
    
    concluidos = df_periodo[df_periodo["Status"]=="Concluído"].shape[0]
    atrasados = df_periodo[(df_periodo["Status"]=="Aberto") & (df_periodo["Prazo"] < datetime.today().date())].shape[0]
    abertos = df_periodo[df_periodo["Status"]=="Aberto"].shape[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Concluídos", concluidos)
    col2.metric("Atrasados", atrasados)
    col3.metric("Em Aberto", abertos)
    
    st.subheader("Pedidos no Período")
    st.dataframe(df_periodo)
    
    # Gráfico resumo
    df_grafico = pd.DataFrame({
        "Status": ["Concluídos", "Atrasados", "Em Aberto"],
        "Quantidade": [concluidos, atrasados, abertos]
    })
    fig3 = px.bar(df_grafico, x="Status", y="Quantidade", color="Status", text="Quantidade")
    st.plotly_chart(fig3)

st.caption("SAD Profissional com três abas: Pedidos, Produtos e Relatórios, controle de capacidade, alertas e PDF.")
