#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="BHB Analytics", layout="wide")

@st.cache_data
def load_data(filepath):
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
        return None

def aggregate(df, matches):
    if df is None or len(matches) == 0:
        return None
    filtered = df[df['Match'].isin(matches)]
    if len(filtered) == 0:
        return None
    return filtered.groupby('Minute').agg({
        'DMA BHB': 'mean', 
        'DMA ADV': 'mean', 
        'Rapport de force': 'mean'
    }).reset_index()

def chart(d1, d2, l1, l2, metric, title):
    fig = go.Figure()
    if d1 is not None:
        fig.add_trace(go.Scatter(
            x=d1['Minute'], 
            y=d1[metric], 
            name=l1, 
            line=dict(color='#667eea', width=4),
            hovertemplate='<b>' + l1 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
    if d2 is not None:
        fig.add_trace(go.Scatter(
            x=d2['Minute'], 
            y=d2[metric], 
            name=l2, 
            line=dict(color='#f5576c', width=4, dash='dash'),
            hovertemplate='<b>' + l2 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
    if 'Rapport' in metric:
        fig.add_hline(y=0, line_dash="dot", line_color="gray", 
                     annotation_text="Équilibre", annotation_position="right")
    fig.update_layout(
        title=title, 
        height=600,
        hovermode='x unified',
        plot_bgcolor='white',
        font=dict(family='Inter, sans-serif')
    )
    return fig

st.title("BHB Analytics")

# Chargement automatique du fichier
df = None

# Essayer de charger le fichier par défaut du repository
if os.path.exists('Base_Donnees_Handball.xlsx'):
    df = load_data('Base_Donnees_Handball.xlsx')
    st.sidebar.success("✅ Données chargées du repository")
else:
    st.sidebar.warning("⚠️ Fichier Base_Donnees_Handball.xlsx non trouvé")

# Option d'upload si besoin
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📁 Charger un autre fichier (optionnel)")
    uploaded = st.file_uploader("", type=['xlsx'], label_visibility="collapsed")
    if uploaded:
        df = load_data(uploaded)
        st.success("✅ Fichier uploadé chargé")

if df is None:
    st.error("❌ Impossible de charger les données")
    st.stop()

# Sidebar - Sélection des groupes
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔵 GROUPE 1")
    
    # Mode de sélection Groupe 1
    mode1 = st.radio(
        "Mode de sélection",
        ["📋 Matchs spécifiques", "🏠 Par Lieu", "⚡ Par Phase"],
        key="mode1"
    )
    
    if mode1 == "📋 Matchs spécifiques":
        matches1 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[0]] if len(df['Match'].unique()) > 0 else [],
            key="m1"
        )
    elif mode1 == "🏠 Par Lieu":
        lieu1 = st.selectbox("Sélectionner le lieu", ['Domicile', 'Extérieur'], key="lieu1")
        matches1 = df[df['Lieu'] == lieu1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs sélectionnés")
    else:  # Par Phase
        phase1 = st.selectbox("Sélectionner la phase", ['ALLER', 'RETOUR'], key="phase1")
        matches1 = df[df['Phase'] == phase1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs sélectionnés")
    
    label1 = st.text_input("Nom du groupe", "Groupe 1", key="label1")
    
    st.markdown("---")
    st.markdown("### 🔴 GROUPE 2")
    
    # Mode de sélection Groupe 2
    mode2 = st.radio(
        "Mode de sélection",
        ["📋 Matchs spécifiques", "🏠 Par Lieu", "⚡ Par Phase"],
        key="mode2"
    )
    
    if mode2 == "📋 Matchs spécifiques":
        matches2 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[1]] if len(df['Match'].unique()) > 1 else [],
            key="m2"
        )
    elif mode2 == "🏠 Par Lieu":
        lieu2 = st.selectbox("Sélectionner le lieu", ['Domicile', 'Extérieur'], index=1, key="lieu2")
        matches2 = df[df['Lieu'] == lieu2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs sélectionnés")
    else:  # Par Phase
        phase2 = st.selectbox("Sélectionner la phase", ['ALLER', 'RETOUR'], index=1, key="phase2")
        matches2 = df[df['Phase'] == phase2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs sélectionnés")
    
    label2 = st.text_input("Nom du groupe", "Groupe 2", key="label2")

# Affichage du résumé des sélections
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**🔵 {label1}** : {len(matches1)} matchs")
with col2:
    st.markdown(f"**🔴 {label2}** : {len(matches2)} matchs")

# Tabs
t1, t2, t3 = st.tabs(["📈 DMA BHB", "📊 DMA ADV", "⚖️ Rapport de Force"])

# Agrégation
d1 = aggregate(df, matches1)
d2 = aggregate(df, matches2)

# Vérification
if d1 is None and d2 is None:
    st.warning("⚠️ Aucune donnée à afficher. Veuillez sélectionner des matchs dans la sidebar.")
    st.stop()

# Graphiques
with t1:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA BHB', 'Évolution DMA BHB'), use_container_width=True)
    with st.expander("ℹ️ À propos de la DMA BHB"):
        st.markdown("""
        **DMA BHB** (Différence de Moyenne Mobile BHB) :
        - Mesure la dynamique offensive de BHB
        - Valeurs hautes = Bonne efficacité récente
        - Valeurs basses = Baisse de performance
        """)

with t2:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA ADV', 'Évolution DMA Adversaire'), use_container_width=True)
    with st.expander("ℹ️ À propos de la DMA ADV"):
        st.markdown("""
        **DMA ADV** (Différence de Moyenne Mobile Adversaire) :
        - Mesure la dynamique offensive des adversaires
        - Valeurs hautes = Adversaire performant
        - Valeurs basses = Adversaire en difficulté
        """)

with t3:
    st.plotly_chart(chart(d1, d2, label1, label2, 'Rapport de force', 'Évolution du Rapport de Force'), use_container_width=True)
    with st.expander("ℹ️ À propos du Rapport de Force"):
        st.markdown("""
        **Rapport de Force** = DMA BHB - DMA ADV :
        - > 0 🟢 : BHB domine
        - < 0 🔴 : Adversaire domine
        - ≈ 0 ⚪ : Équilibre
        """)

st.markdown("---")
st.markdown("*BHB Analytics v3.1 | Dashboard Handball*")
