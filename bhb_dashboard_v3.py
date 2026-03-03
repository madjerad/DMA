#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="BHB Analytics", layout="wide")

@st.cache_data
def load_data(f):
    df = pd.read_excel(f)
    return df

def aggregate(df, matches):
    filtered = df[df['Match'].isin(matches)]
    if len(filtered) == 0:
        return None
    return filtered.groupby('Minute').agg({'DMA BHB': 'mean', 'DMA ADV': 'mean', 'Rapport de force': 'mean'}).reset_index()

def chart(d1, d2, l1, l2, metric, title):
    fig = go.Figure()
    if d1 is not None:
        fig.add_trace(go.Scatter(x=d1['Minute'], y=d1[metric], name=l1, line=dict(color='blue', width=3)))
    if d2 is not None:
        fig.add_trace(go.Scatter(x=d2['Minute'], y=d2[metric], name=l2, line=dict(color='red', width=3, dash='dash')))
    fig.update_layout(title=title, height=600)
    return fig

st.title("🤾 BHB Analytics")

f = st.sidebar.file_uploader("Fichier Excel", type=['xlsx'])
if not f:
    st.stop()

df = load_data(f)

st.sidebar.markdown("### Groupe 1")
m1 = st.sidebar.multiselect("Matchs 1", df['Match'].unique(), default=[df['Match'].unique()[0]])
l1 = st.sidebar.text_input("Nom 1", "Groupe 1")

st.sidebar.markdown("### Groupe 2")
m2 = st.sidebar.multiselect("Matchs 2", df['Match'].unique(), default=[df['Match'].unique()[1]] if len(df['Match'].unique()) > 1 else [])
l2 = st.sidebar.text_input("Nom 2", "Groupe 2")

t1, t2, t3 = st.tabs(["DMA BHB", "DMA ADV", "Rapport de Force"])
d1, d2 = aggregate(df, m1), aggregate(df, m2)

with t1:
    st.plotly_chart(chart(d1, d2, l1, l2, 'DMA BHB', 'DMA BHB'), use_container_width=True)
with t2:
    st.plotly_chart(chart(d1, d2, l1, l2, 'DMA ADV', 'DMA ADV'), use_container_width=True)
with t3:
    st.plotly_chart(chart(d1, d2, l1, l2, 'Rapport de force', 'Rapport de Force'), use_container_width=True)
