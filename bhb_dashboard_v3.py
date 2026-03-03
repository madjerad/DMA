#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
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

def calculate_trend(x, y):
    """Calcule la courbe de tendance polynomiale"""
    z = np.polyfit(x, y, 3)
    p = np.poly1d(z)
    return p(x)

def chart(d1, d2, l1, l2, metric, title, show_trend=False):
    fig = go.Figure()
    
    # Courbe Groupe 1
    if d1 is not None:
        fig.add_trace(go.Scatter(
            x=d1['Minute'], 
            y=d1[metric], 
            name=l1, 
            line=dict(color='#667eea', width=4),
            hovertemplate='<b>' + l1 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        
        # Courbe de tendance pour Groupe 1 (si activée)
        if show_trend and len(d1) > 3:
            trend1 = calculate_trend(d1['Minute'].values, d1[metric].values)
            fig.add_trace(go.Scatter(
                x=d1['Minute'],
                y=trend1,
                name=f'{l1} - Tendance',
                line=dict(color='#667eea', width=2, dash='dot'),
                opacity=0.6,
                hovertemplate='<b>' + l1 + ' Tendance</b><br>Minute: %{x}<br>Tendance: %{y:.3f}<extra></extra>'
            ))
    
    # Courbe Groupe 2
    if d2 is not None:
        fig.add_trace(go.Scatter(
            x=d2['Minute'], 
            y=d2[metric], 
            name=l2, 
            line=dict(color='#f5576c', width=4, dash='dash'),
            hovertemplate='<b>' + l2 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        
        # Courbe de tendance pour Groupe 2 (si activée)
        if show_trend and len(d2) > 3:
            trend2 = calculate_trend(d2['Minute'].values, d2[metric].values)
            fig.add_trace(go.Scatter(
                x=d2['Minute'],
                y=trend2,
                name=f'{l2} - Tendance',
                line=dict(color='#f5576c', width=2, dash='dot'),
                opacity=0.6,
                hovertemplate='<b>' + l2 + ' Tendance</b><br>Minute: %{x}<br>Tendance: %{y:.3f}<extra></extra>'
            ))
    
    # Ligne de référence pour Rapport de Force
    if 'Rapport' in metric:
        fig.add_hline(y=0, line_dash="dot", line_color="gray", 
                     annotation_text="Équilibre", annotation_position="right",
                     line_width=1, opacity=0.5)
    
    fig.update_layout(
        title=title, 
        height=600,
        hovermode='x unified',
        plot_bgcolor='white',
        font=dict(family='Inter, sans-serif'),
        xaxis=dict(title="Minute de jeu", gridcolor='rgba(0,0,0,0.1)'),
        yaxis=dict(title=metric, gridcolor='rgba(0,0,0,0.1)'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    return fig

st.title("BHB Analytics")

# Chargement automatique du fichier
df = None

# Charger uniquement le fichier du repository
if os.path.exists('Base_Donnees_Handball.xlsx'):
    df = load_data('Base_Donnees_Handball.xlsx')
    st.sidebar.success("✅ Données chargées")
else:
    st.sidebar.error("❌ Fichier Base_Donnees_Handball.xlsx non trouvé")
    st.error("❌ Impossible de charger les données. Vérifiez que le fichier Base_Donnees_Handball.xlsx est dans le repository.")
    st.stop()

if df is None:
    st.error("❌ Erreur lors du chargement des données")
    st.stop()

# Sidebar - Sélection des groupes
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔵 GROUPE 1")
    
    # Mode de sélection Groupe 1 - ORDRE INVERSÉ
    mode1 = st.radio(
        "Mode de sélection",
        ["⚡ Par Phase", "🏠 Par Lieu", "📋 Matchs spécifiques"],
        key="mode1"
    )
    
    if mode1 == "⚡ Par Phase":
        phase1 = st.selectbox("Sélectionner la phase", ['ALLER', 'RETOUR'], key="phase1")
        matches1 = df[df['Phase'] == phase1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs sélectionnés")
    elif mode1 == "🏠 Par Lieu":
        lieu1 = st.selectbox("Sélectionner le lieu", ['Domicile', 'Extérieur'], key="lieu1")
        matches1 = df[df['Lieu'] == lieu1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs sélectionnés")
    else:  # Matchs spécifiques
        matches1 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[0]] if len(df['Match'].unique()) > 0 else [],
            key="m1"
        )
    
    label1 = st.text_input("Nom du groupe", "Groupe 1", key="label1")
    
    st.markdown("---")
    st.markdown("### 🔴 GROUPE 2")
    
    # Mode de sélection Groupe 2 - ORDRE INVERSÉ
    mode2 = st.radio(
        "Mode de sélection",
        ["⚡ Par Phase", "🏠 Par Lieu", "📋 Matchs spécifiques"],
        key="mode2"
    )
    
    if mode2 == "⚡ Par Phase":
        phase2 = st.selectbox("Sélectionner la phase", ['ALLER', 'RETOUR'], index=1, key="phase2")
        matches2 = df[df['Phase'] == phase2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs sélectionnés")
    elif mode2 == "🏠 Par Lieu":
        lieu2 = st.selectbox("Sélectionner le lieu", ['Domicile', 'Extérieur'], index=1, key="lieu2")
        matches2 = df[df['Lieu'] == lieu2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs sélectionnés")
    else:  # Matchs spécifiques
        matches2 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[1]] if len(df['Match'].unique()) > 1 else [],
            key="m2"
        )
    
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
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA BHB', 'Évolution DMA BHB', show_trend=False), use_container_width=True)

with t2:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA ADV', 'Évolution DMA Adversaire', show_trend=False), use_container_width=True)

with t3:
    # Option pour afficher/masquer la courbe de tendance
    show_trend = st.checkbox("Afficher les courbes de tendance", value=True)
    st.plotly_chart(chart(d1, d2, label1, label2, 'Rapport de force', 'Évolution du Rapport de Force', show_trend=show_trend), use_container_width=True)

st.markdown("---")
st.markdown("*BHB Analytics v3.3 | Dashboard Handball*")
