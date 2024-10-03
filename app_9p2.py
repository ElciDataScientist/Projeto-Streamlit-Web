import pandas            as pd
import streamlit         as st
import seaborn           as sns
import matplotlib.pyplot as plt
import os
from PIL                 import Image
from io                  import BytesIO
from flask import Flask, render_template

# Set no tema do seaborn para melhorar o visual dos plots
custom_params = {"axes.spines.right": False, "axes.spines.top": False}
sns.set_theme(style="ticks", rc=custom_params)


# Função para ler os dados
@st.cache_data(show_spinner= True)
def load_data(file_data):
    try:
        return pd.read_csv(file_data, sep=';')
    except:
        return pd.read_excel(file_data)

# Função para filtrar baseado na multiseleção de categorias
@st.cache_data()
def multiselect_filter(relatorio, col, selecionados):
    if 'all' in selecionados:
        return relatorio
    else:
        return relatorio[relatorio[col].isin(selecionados)].reset_index(drop=True)

# Função para converter o df para csv
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')


# Função para converter o df para excel
@st.cache_data
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data


# Função principal da aplicação
def main():
    # Configuração inicial da página da aplicação
    st.set_page_config(page_title = 'RFV', \
        layout="wide",
        initial_sidebar_state='expanded'
    )

    # Título principal da aplicação
    st.write("""# RFV

    RFV significa recência, frequência, valor e é utilizado para segmentação de clientes baseado no comportamento 
    de compras dos clientes e agrupa eles em clusters parecidos. Utilizando esse tipo de agrupamento podemos realizar 
    ações de marketing e CRM melhores direcionadas, ajudando assim na personalização do conteúdo e até a retenção de clientes.

    Para cada cliente é preciso calcular cada uma das componentes abaixo:

    - Recência (R): Quantidade de dias desde a última compra.
    - Frequência (F): Quantidade total de compras no período.
    - Valor (V): Total de dinheiro gasto nas compras do período.

    E é isso que iremos fazer abaixo.
    """)
    st.markdown("---")
    
    # Apresenta a imagem na barra lateral da aplicação
    # image = Image.open("Bank-Branding.jpg")
    # st.sidebar.image(image)

    # Botão para carregar arquivo na aplicação
    st.sidebar.write("## Suba o arquivo")
    data_file_1 = st.sidebar.file_uploader("Recência Frequência de Valor", type = ['csv','xlsx'])

    # Verifica se há conteúdo carregado na aplicação
    if (data_file_1 is not None):
        def recencia_class(value, column_name, quartis):
            if value <= quartis[column_name][0.25]:
                return 'D'
            elif value <= quartis[column_name][0.50]:
                return 'C'
            elif value <= quartis[column_name][0.75]:
                return 'B'
            else:
                return 'A'
        def freq_val_class(value, column_name, quartis):
            if value >= quartis.loc[0.75, column_name]:
                return 'A'
            elif value >= quartis.loc[0.50, column_name]:
                return 'B'
            elif value >= quartis.loc[0.25, column_name]:
                return 'C'
            else:
                return 'D'
    
        df_compras = pd.read_csv(data_file_1, infer_datetime_format=True, parse_dates=['DiaCompra'])

        st.write('## Recência (R)')

        
        dia_atual = df_compras['DiaCompra'].max()
        st.write('Dia máximo na base de dados: ', dia_atual)

        st.write('Quantos dias faz que o cliente fez a sua última compra?')

        df_recencia = df_compras.groupby(by='ID_cliente', as_index=False)['DiaCompra'].max()
        df_recencia.columns = ['ID_cliente','DiaUltimaCompra']
        df_recencia['Recencia'] = df_recencia['DiaUltimaCompra'].apply(lambda x: (dia_atual - x).days)
        st.write(df_recencia.head())

        df_recencia.drop('DiaUltimaCompra', axis=1, inplace=True)

        st.write('## Frequência (F)')
        st.write('Quantas vezes cada cliente comprou com a gente?')
        df_frequencia = df_compras[['ID_cliente','CodigoCompra']].groupby('ID_cliente').count().reset_index()
        df_frequencia.columns = ['ID_cliente','Frequencia']
        st.write(df_frequencia.head())

        st.write('## Valor (V)')
        st.write('Quanto que cada cliente gastou no periodo?')
        df_valor = df_compras[['ID_cliente','ValorTotal']].groupby('ID_cliente').sum().reset_index()
        df_valor.columns = ['ID_cliente','Valor']
        st.write(df_valor.head())
        

        st.write('## Tabela RFV final')
        df_RF = df_recencia.merge(df_frequencia, on='ID_cliente')
        df_RFV = df_RF.merge(df_valor, on='ID_cliente')
        df_RFV.set_index('ID_cliente', inplace=True)
        st.write(df_RFV.head())

        st.write('## Segmentação utilizando o RFV')
        st.write("Um jeito de segmentar os clientes é criando quartis para cada componente do RFV, sendo que o melhor quartil é chamado de 'A', o segundo melhor quartil de 'B', o terceiro melhor de 'C' e o pior de 'D'. O melhor e o pior depende da componente. Po exemplo, quanto menor a recência melhor é o cliente (pois ele comprou com a gente tem pouco tempo) logo o menor quartil seria classificado como 'A', já pra componente frêquencia a lógica se inverte, ou seja, quanto maior a frêquencia do cliente comprar com a gente, melhor ele/a é, logo, o maior quartil recebe a letra 'A'.")
        st.write('Se a gente tiver interessado em mais ou menos classes, basta a gente aumentar ou diminuir o número de quantils pra cada componente.')

        st.write('Quartis para o RFV')
        quartis = df_RFV.quantile(q=[0.25,0.5,0.75])
        st.write(quartis)

        st.write('Tabela após a criação dos grupos')
        
        # Aplicar a classificação de recência
        df_RFV['R_quartil'] = df_RFV['Recencia'].apply(recencia_class, args=('Recencia', quartis))
        
        # Aplicar a classificação de frequência
        df_RFV['F_quartil'] = df_RFV['Frequencia'].apply(freq_val_class, args=('Frequencia', quartis))
        
        # Aplicar a classificação de valor
        df_RFV['V_quartil'] = df_RFV['Valor'].apply(freq_val_class, args=('Valor', quartis))
        
        # Calcular o score RFV
        df_RFV['RFV_Score'] = (df_RFV.R_quartil + df_RFV.F_quartil + df_RFV.V_quartil)
        
        # Exibir as primeiras linhas do DataFrame resultante
        st.write(df_RFV.head())

        st.write('Quantidade de clientes por grupos')
        st.write(df_RFV['RFV_Score'].value_counts())

        st.write('#### Clientes com menor recência, maior frequência e maior valor gasto')
        st.write(df_RFV[df_RFV['RFV_Score']=='AAA'].sort_values('Valor', ascending=False).head(10))

        st.write('### Ações de marketing/CRM')

        dict_acoes = {'AAA': 'Enviar cupons de desconto, Pedir para indicar nosso produto pra algum amigo, Ao lançar um novo produto enviar amostras grátis pra esses.',
        'DDD': 'Churn! clientes que gastaram bem pouco e fizeram poucas compras, fazer nada',
        'DAA': 'Churn! clientes que gastaram bastante e fizeram muitas compras, enviar cupons de desconto para tentar recuperar',
        'CAA': 'Churn! clientes que gastaram bastante e fizeram muitas compras, enviar cupons de desconto para tentar recuperar'
        }

        df_RFV['acoes de marketing/crm'] = df_RFV['RFV_Score'].map(dict_acoes)
        st.write(df_RFV.head())


        # df_RFV.to_excel('./auxiliar/output/RFV_.xlsx')
        df_xlsx = to_excel(df_RFV)
        st.download_button(label='📥 Download',
                            data=df_xlsx ,
                            file_name= 'RFV_.xlsx')

        st.write('Quantidade de clientes por tipo de ação')
        st.write(df_RFV['acoes de marketing/crm'].value_counts(dropna=False))
        
        
        # Exemplo de DataFrame filtrado
        data_file_1_filtrado = df_RFV  # Substitua por seu DataFrame filtrado
        

        # Download para Excel
        df_xlsx = to_excel(data_file_1_filtrado)  # Certifique-se de que a função to_excel está definida
        st.download_button(
        label='📥 Download como Excel',
        data=df_xlsx,
        file_name='dados_filtrados.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key='download_excel_button'  # Key exclusivo para o botão Excel
)       
if __name__ == '__main__':
	main()
    









