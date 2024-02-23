from math import exp
from altair import AggregateTransform
import streamlit as st
import pandas as pd
import numpy as np
import database as db
import datetime as dt

import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns

# Page navigation
st.sidebar.page_link('home.py', label='Home')
st.sidebar.page_link('pages/search.py', label='Search', icon='🔎')
st.sidebar.page_link('pages/upload.py', label='Upload', icon='🧾')
st.sidebar.page_link('pages/visualization.py', label='Visualize', icon='📊')
st.sidebar.divider()

#Get receipts data from database
df = db.data()
column_names = {
    'id_pk':'ID',
    'receipt_id':'Receipt',
    'receipt_date':'Date',
    'price':'Price',
    'product_abbr':'Name on receipt',
    'product_name':'Name',
    'category_main':'Category',
    'category_sub':'Kind',
    'embedding':'Semantic coordinates'
}

# For prototype: insert dates
receipt_ids =   ['Rewe_1.jpg', 'Rewe_2.jpg', 'Rewe_3.jpg', 'Rewe_4.jpg', 'Rewe_5.jpg', 'Rewe_6.jpg', 'Rewe_7.jpg', 'Rewe_8.jpg', 'Rewe_9.jpg', 'Rewe_10.jpg', 'Rewe_11.jpg', 'Rewe_12.jpg', 'Rewe_13.jpg', 'Rewe_14.jpg']
receipt_dates = ['20.01.2024', '12.12.2023', '30.12.2023', '13.12.2023', '08.11.2023', '11.11.2023', '18.11.2023', '11.11.2023', '07.11.2023', '22.01.2024',  '04.12.2023',  '09.02.2024',  '20.12.2023',  '03.01.2024']

df_dates = pd.DataFrame(zip(receipt_ids, receipt_dates), columns=['receipt_id', 'receipt_date'])
df_dates.receipt_date = pd.to_datetime(df_dates.receipt_date, dayfirst=True)
df = df.join(df_dates.set_index('receipt_id'), on='receipt_id')


# Options for dashboard

# Show subcategories
toggle_subcategories = st.sidebar.toggle('I want the details :tea: :teapot:')

# Select timeframe
df_timeframe = [df.receipt_date.min().date(), df.receipt_date.max().date()]
dates = st.sidebar.date_input('Select dates of expenses', value=(df_timeframe),
                              min_value=df_timeframe[0],
                              max_value=df_timeframe[1],
                              format='DD.MM.YYYY')
# TODO: set date_input state to reset
reset_dates = st.sidebar.button('Reset')

if reset_dates: # Reset button will display full df
    pass 
elif len(dates) == 2: # Dashboard already updates and throws error if only one date is chosen
    # Query df for timeframe for all visualizations on the dashboard
    df = df.query('@dates[0] < receipt_date < @dates[-1]') 

# Overview over spending at a glance

metric1, metric2, metric3 = st.columns(3, gap='small')

with metric1:
    total_spending = df.price.sum()

    st.metric(':money_with_wings: Total spending', 
              value=f'{round(total_spending, 2)} €')
with metric2:
    most_spending_category = df.groupby('category_main').price.sum().sort_values(ascending=False).reset_index().iloc[0].to_list()

    st.metric(':gem: Most expensive category', 
              value=f'{round(most_spending_category[1], 2)} €', 
              delta=most_spending_category[0], 
              delta_color='off')
with metric3:
    top_count_category = df.loc[df['price']>0].category_sub.value_counts().reset_index().iloc[0].to_list()

    st.metric(':shopping_bags: Most common kind of product',
              value=top_count_category[0],
              delta=f'Bought {top_count_category[1]} times',
              delta_color='off')





st.header('What makes up most of my expenses?')

# Choose with toggle if subcategories are colored in
if not toggle_subcategories:
    # Show h-bar of categories
    fig = px.bar(df.rename(columns=column_names),
                x='Price', y='Category', 
                hover_data=['Kind', 'Name', 'Name on receipt', 'Date'],
                orientation='h')
    fig.update_layout(
        yaxis = {"categoryorder":"total ascending"},
        xaxis_title="Sum of expenses in €")


    st.plotly_chart(fig, use_container_width=True)
else:
    # Show h-bar chart with subcategories
    fig = px.bar(df.rename(columns=column_names), 
                x='Price', y='Category', 
                color='Kind', 
                hover_data=['Name', 'Name on receipt', 'Date'],
                orientation='h')
    fig.update_layout(
        yaxis = {"categoryorder":"total ascending"},
        xaxis_title="Sum of expenses in €",
        showlegend=False)

    st.plotly_chart(fig, use_container_width=True)





st.header('Spending over time')
aggregate_state = st.radio('Select aggregation',
                           ['Days', 'Months'])
if aggregate_state == 'Days':
    if not toggle_subcategories:
        # Barplot over time one color
        fig = px.bar(df.rename(columns=column_names).sort_values(by='Date'), 
                        x='Date', y='Price',
                        hover_data=['Category', 'Kind', 'Name', 'Name on receipt'])
        fig.update_layout(
                yaxis_title="Sum of receipts in €",
                xaxis_title='',
                showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Barplot over time with colors by category
        fig = px.bar(df.rename(columns=column_names).sort_values(by='Date'), 
                        x='Date', y='Price',
                        color='Category',
                        hover_data=['Kind', 'Name', 'Name on receipt'])
        fig.update_layout(
                yaxis_title="Sum of receipts in €",
                xaxis_title='',
                showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
elif aggregate_state == 'Months':
    if not toggle_subcategories:
        # Histogram of expenses by month
        fig = px.histogram(
            df.rename(columns=column_names), 
            x="Date", 
            y="Price", 
            histfunc="sum")
        fig.update_traces(xbins_size="M1")
        fig.update_xaxes(ticklabelmode="period", dtick="M1", tickformat="%b\n%Y")
        fig.update_layout(bargap=0.1, yaxis_title='Sum of expenses in €')
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Histogram of expenses by month with categories
        fig = px.histogram(
            df.rename(columns=column_names), 
            x="Date", 
            y="Price", 
            histfunc="sum",
            color='Category',
            hover_data=['Kind', 'Name', 'Name on receipt'])
        fig.update_traces(xbins_size="M1")
        fig.update_xaxes(ticklabelmode="period", dtick="M1", tickformat="%b\n%Y")
        fig.update_layout(bargap=0.1, yaxis_title='Sum of expenses in €', showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Display data of monthly expenses by category
        # Group by Month, put categories as rows, months as col
        df_monthly = (df.set_index('receipt_date')
                      .groupby([pd.Grouper(freq='M'), 'category_main'])
                      .price.sum().unstack().fillna(0).T)
        # Prettify with formatting the months as Jan 24
        df_monthly.columns = [x.strftime('%b %Y') for x in df_monthly.columns.to_list()]
        # Delete index name
        df_monthly.index.rename(None, inplace=True)
        # Prettify with formatting all number cols as currency
        df_monthly = df_monthly.style.format(dict.fromkeys(df_monthly.select_dtypes(include='number').columns.tolist(), '{:.2f} €'))
        

        st.dataframe(df_monthly)


# Show all data and edit data in expander
with st.expander('Your groceries spendings, all in on place…'):
    full_data = st.toggle('Edit data')
    if full_data:
        # Show an editable df
        st.data_editor(df.rename(columns=column_names))
        # TODO: Embed edited entries and overwrite entry in db
        st.button('Submit Edits', type='primary')
    else:
        # Show prettified dataframe
        df['Date'] = df_dates.receipt_date.dt.strftime('%d.%m.%Y')
        st.dataframe(df[['Date', 'product_name', 'category_sub', 'price']]
                     .sort_values(by='Date')
                     .rename(columns=column_names)
                     .style.format({'Price':'{:.2f} €'}))