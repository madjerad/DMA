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

def detect_inf_sup_sequences(df):
    """Détecte les séquences consécutives d'INF et SUP"""
    sequences_inf = []
    sequences_sup = []
    
    # INF
    in_inf = False
    start_idx = None
    for idx, row in df.iterrows():
        if pd.notna(row['INF']) and row['INF'] == 'INF':
            if not in_inf:
                start_idx = idx
                in_inf = True
        else:
            if in_inf:
                sequences_inf.append((start_idx, idx - 1))
                in_inf = False
    if in_inf:
        sequences_inf.append((start_idx, df.index[-1]))
    
    # SUP
    in_sup = False
    start_idx = None
    for idx, row in df.iterrows():
        if pd.notna(row['SUP']) and row['SUP'] == 'SUP':
            if not in_sup:
                start_idx = idx
                in_sup = True
        else:
            if in_sup:
                sequences_sup.append((start_idx, idx - 1))
                in_sup = False
    if in_sup:
        sequences_sup.append((start_idx, df.index[-1]))
    
    return sequences_inf, sequences_sup

def calculate_general_stats(df, matches):
    """Calcule les statistiques générales par mi-temps"""
    if df is None or len(matches) == 0:
        return None
    
    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None
    
    stats = {}
    
    # Séparer par mi-temps
    mt1 = filtered_df[filtered_df['Minute'] <= 30]
    mt2 = filtered_df[filtered_df['Minute'] > 30]
    
    for period, period_data, suffix in [(mt1, '1'), (mt2, '2'), (filtered_df, 'T')]:
        if len(period_data) == 0:
            continue
        
        bhb_data = period_data[period_data['Equipe'] == 'BHB']
        adv_data = period_data[period_data['Equipe'] == 'ADV']
        
        # Buts
        buts_bhb = bhb_data['Issue'].sum()
        buts_adv = adv_data['Issue'].sum()
        stats[f'Buts BHB {suffix}'] = int(buts_bhb)
        stats[f'Buts ADV {suffix}'] = int(buts_adv)
        
        # Possessions
        stats[f'Poss BHB {suffix}'] = len(bhb_data)
        stats[f'Poss ADV {suffix}'] = len(adv_data)
        stats[f'Poss Total {suffix}'] = len(period_data)
        
        # Rythme (poss/30min)
        duree = 30 if suffix != 'T' else 60
        stats[f'Rythme {suffix}'] = len(period_data) / duree if duree > 0 else 0
        
        # Ratio But/Poss BHB
        stats[f'Ratio But/Poss {suffix}'] = (buts_bhb / len(bhb_data)) if len(bhb_data) > 0 else 0
        
        # Efficacité Défensive = (PossADV - ButsADV) / PossADV
        stats[f'Eff Def {suffix}'] = ((len(adv_data) - buts_adv) / len(adv_data)) if len(adv_data) > 0 else 0
        
        # Déchet technique (Tireur vide ou 0)
        dechet = bhb_data[(bhb_data['Tireur'].isna()) | (bhb_data['Tireur'] == 0)]
        stats[f'Déchet {suffix}'] = len(dechet)
        
        # Efficacité Tir = Buts / (PossBHB - Déchet)
        tirs_effectifs = len(bhb_data) - len(dechet)
        stats[f'Eff Tir {suffix}'] = (buts_bhb / tirs_effectifs) if tirs_effectifs > 0 else 0
        
        # Ratio Perte/Poss
        stats[f'Ratio Perte {suffix}'] = (len(dechet) / len(bhb_data)) if len(bhb_data) > 0 else 0
        
        # DMA
        dma_bhb = bhb_data['DMA BHB'].dropna()
        dma_adv = adv_data['DMA ADV'].dropna()
        
        stats[f'Moy DMA BHB {suffix}'] = dma_bhb.mean() if len(dma_bhb) > 0 else 0
        stats[f'ET DMA BHB {suffix}'] = dma_bhb.std() if len(dma_bhb) > 0 else 0
        stats[f'Moy DMA ADV {suffix}'] = dma_adv.mean() if len(dma_adv) > 0 else 0
        stats[f'ET DMA ADV {suffix}'] = dma_adv.std() if len(dma_adv) > 0 else 0
        
        # Rapport de Force
        stats[f'RdF {suffix}'] = stats[f'Moy DMA BHB {suffix}'] - stats[f'Moy DMA ADV {suffix}']
        
        # INF/SUP - Détecter séquences
        seq_inf, seq_sup = detect_inf_sup_sequences(period_data)
        
        stats[f'Nb INF {suffix}'] = len(seq_inf)
        stats[f'Nb SUP {suffix}'] = len(seq_sup)
        
        # Calculer écart sur INF/SUP
        ecart_inf = 0
        for start, end in seq_inf:
            seq_data = period_data.loc[start:end]
            bhb_buts = seq_data[(seq_data['Equipe'] == 'BHB') & (seq_data['Issue'] == 1)]['Issue'].sum()
            adv_buts = seq_data[(seq_data['Equipe'] == 'ADV') & (seq_data['Issue'] == 1)]['Issue'].sum()
            ecart_inf += (bhb_buts - adv_buts)
        
        ecart_sup = 0
        for start, end in seq_sup:
            seq_data = period_data.loc[start:end]
            bhb_buts = seq_data[(seq_data['Equipe'] == 'BHB') & (seq_data['Issue'] == 1)]['Issue'].sum()
            adv_buts = seq_data[(seq_data['Equipe'] == 'ADV') & (seq_data['Issue'] == 1)]['Issue'].sum()
            ecart_sup += (bhb_buts - adv_buts)
        
        stats[f'Ecart INF {suffix}'] = ecart_inf
        stats[f'Ecart SUP {suffix}'] = ecart_sup
        stats[f'Moy Ecart INF {suffix}'] = (ecart_inf / len(seq_inf)) if len(seq_inf) > 0 else 0
        stats[f'Moy Ecart SUP {suffix}'] = (ecart_sup / len(seq_sup)) if len(seq_sup) > 0 else 0
    
    return stats

def calculate_shooter_stats(df, matches):
    """Calcule les statistiques des buteurs par mi-temps"""
    if df is None or len(matches) == 0:
        return None
    
    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None
    
    # Filtrer uniquement BHB
    bhb_data = filtered_df[filtered_df['Equipe'] == 'BHB'].copy()
    
    if len(bhb_data) == 0:
        return None
    
    # Dictionnaire pour stocker les stats par tireur
    shooters = {}
    
    for _, row in bhb_data.iterrows():
        tireur = str(row['Tireur']) if pd.notna(row['Tireur']) else '(Inconnu)'
        minute = row['Minute']
        issue = row['Issue']
        
        if tireur not in shooters:
            shooters[tireur] = {
                'Tirs 1': 0, 'Buts 1': 0,
                'Tirs 2': 0, 'Buts 2': 0
            }
        
        # Déterminer mi-temps
        if minute <= 30:
            shooters[tireur]['Tirs 1'] += 1
            if issue == 1:
                shooters[tireur]['Buts 1'] += 1
        else:
            shooters[tireur]['Tirs 2'] += 1
            if issue == 1:
                shooters[tireur]['Buts 2'] += 1
    
    # Convertir en DataFrame et calculer totaux et efficacités
    data = []
    for tireur, stats in shooters.items():
        tirs_total = stats['Tirs 1'] + stats['Tirs 2']
        buts_total = stats['Buts 1'] + stats['Buts 2']
        
        eff1 = (stats['Buts 1'] / stats['Tirs 1']) if stats['Tirs 1'] > 0 else 0
        eff2 = (stats['Buts 2'] / stats['Tirs 2']) if stats['Tirs 2'] > 0 else 0
        eff_total = (buts_total / tirs_total) if tirs_total > 0 else 0
        
        data.append({
            'Joueur': tireur,
            'Tirs 1': stats['Tirs 1'],
            'Buts 1': stats['Buts 1'],
            'Eff 1': eff1,
            'Tirs 2': stats['Tirs 2'],
            'Buts 2': stats['Buts 2'],
            'Eff 2': eff2,
            'Tirs Total': tirs_total,
            'Buts Total': buts_total,
            'Eff Total': eff_total
        })
    
    shooter_df = pd.DataFrame(data)
    # Trier par buts totaux décroissants
    shooter_df = shooter_df.sort_values('Buts Total', ascending=False)
    
    return shooter_df

def chart(d1, d2, l1, l2, metric, title, show_trend=False):
    fig = go.Figure()
    
    if d1 is not None:
        fig.add_trace(go.Scatter(
            x=d1['Minute'], 
            y=d1[metric], 
            name=l1, 
            line=dict(color='#667eea', width=4),
            hovertemplate='<b>' + l1 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        
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
    
    if d2 is not None:
        fig.add_trace(go.Scatter(
            x=d2['Minute'], 
            y=d2[metric], 
            name=l2, 
            line=dict(color='#f5576c', width=4, dash='dash'),
            hovertemplate='<b>' + l2 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        
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

st.title("🤾 BHB Analytics")

# Chargement
df = None
if os.path.exists('Base_Donnees_Handball.xlsx'):
    df = load_data('Base_Donnees_Handball.xlsx')
    st.sidebar.success("✅ Données chargées")
else:
    st.sidebar.error("❌ Fichier Base_Donnees_Handball.xlsx non trouvé")
    st.error("❌ Impossible de charger les données")
    st.stop()

if df is None:
    st.error("❌ Erreur lors du chargement")
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔵 GROUPE 1")
    
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
    else:
        matches1 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[0]] if len(df['Match'].unique()) > 0 else [],
            key="m1"
        )
    
    label1 = st.text_input("Nom du groupe", "Groupe 1", key="label1")
    
    st.markdown("---")
    st.markdown("### 🔴 GROUPE 2")
    
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
    else:
        matches2 = st.multiselect(
            "Sélectionner les matchs",
            sorted(df['Match'].unique()),
            default=[sorted(df['Match'].unique())[1]] if len(df['Match'].unique()) > 1 else [],
            key="m2"
        )
    
    label2 = st.text_input("Nom du groupe", "Groupe 2", key="label2")

# Résumé
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**🔵 {label1}** : {len(matches1)} matchs")
with col2:
    st.markdown(f"**🔴 {label2}** : {len(matches2)} matchs")

# Tabs - AJOUT DES 2 NOUVEAUX ONGLETS
t1, t2, t3, t4, t5 = st.tabs([
    "📈 DMA BHB", 
    "📊 DMA ADV", 
    "⚖️ Rapport de Force",
    "📋 Stats Générales",
    "🎯 Stats Buteurs"
])

# Agrégation
d1 = aggregate(df, matches1)
d2 = aggregate(df, matches2)

if d1 is None and d2 is None:
    st.warning("⚠️ Aucune donnée à afficher. Veuillez sélectionner des matchs.")
    st.stop()

# Graphiques DMA
with t1:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA BHB', 'Évolution DMA BHB', show_trend=False), use_container_width=True)

with t2:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA ADV', 'Évolution DMA Adversaire', show_trend=False), use_container_width=True)

with t3:
    show_trend = st.checkbox("Afficher les courbes de tendance", value=True)
    st.plotly_chart(chart(d1, d2, label1, label2, 'Rapport de force', 'Évolution du Rapport de Force', show_trend=show_trend), use_container_width=True)

# NOUVEAU: Stats Générales
with t4:
    st.markdown("### 📋 Statistiques Générales")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown(f"#### {label1}")
        stats1 = calculate_general_stats(df, matches1)
        if stats1:
            data1 = []
            indicators = [
                ('Score', f"{stats1['Buts BHB 1']}-{stats1['Buts ADV 1']}", f"{stats1['Buts BHB 2']}-{stats1['Buts ADV 2']}", f"{stats1['Buts BHB T']}-{stats1['Buts ADV T']}"),
                ('Buts Pour', stats1['Buts BHB 1'], stats1['Buts BHB 2'], stats1['Buts BHB T']),
                ('Buts Contre', stats1['Buts ADV 1'], stats1['Buts ADV 2'], stats1['Buts ADV T']),
                ('Nb Possessions', stats1['Poss Total 1'], stats1['Poss Total 2'], stats1['Poss Total T']),
                ('Rythme (Poss/30min)', f"{stats1['Rythme 1']:.2f}", f"{stats1['Rythme 2']:.2f}", f"{stats1['Rythme T']:.2f}"),
                ('Ratio But/Poss BHB', f"{stats1['Ratio But/Poss 1']:.1%}", f"{stats1['Ratio But/Poss 2']:.1%}", f"{stats1['Ratio But/Poss T']:.1%}"),
                ('Efficacité Défensive', f"{stats1['Eff Def 1']:.1%}", f"{stats1['Eff Def 2']:.1%}", f"{stats1['Eff Def T']:.1%}"),
                ('Efficacité Tir', f"{stats1['Eff Tir 1']:.1%}", f"{stats1['Eff Tir 2']:.1%}", f"{stats1['Eff Tir T']:.1%}"),
                ('Déchet Technique', stats1['Déchet 1'], stats1['Déchet 2'], stats1['Déchet T']),
                ('Ratio Perte/Poss', f"{stats1['Ratio Perte 1']:.1%}", f"{stats1['Ratio Perte 2']:.1%}", f"{stats1['Ratio Perte T']:.1%}"),
                ('Nb INF', stats1['Nb INF 1'], stats1['Nb INF 2'], stats1['Nb INF T']),
                ('Écart sur INF', stats1['Ecart INF 1'], stats1['Ecart INF 2'], stats1['Ecart INF T']),
                ('Moy Écart INF', f"{stats1['Moy Ecart INF 1']:.2f}", f"{stats1['Moy Ecart INF 2']:.2f}", f"{stats1['Moy Ecart INF T']:.2f}"),
                ('Nb SUP', stats1['Nb SUP 1'], stats1['Nb SUP 2'], stats1['Nb SUP T']),
                ('Écart sur SUP', stats1['Ecart SUP 1'], stats1['Ecart SUP 2'], stats1['Ecart SUP T']),
                ('Moy Écart SUP', f"{stats1['Moy Ecart SUP 1']:.2f}", f"{stats1['Moy Ecart SUP 2']:.2f}", f"{stats1['Moy Ecart SUP T']:.2f}"),
                ('Moyenne DMA BHB', f"{stats1['Moy DMA BHB 1']:.4f}", f"{stats1['Moy DMA BHB 2']:.4f}", f"{stats1['Moy DMA BHB T']:.4f}"),
                ('Écart Type DMA BHB', f"{stats1['ET DMA BHB 1']:.4f}", f"{stats1['ET DMA BHB 2']:.4f}", f"{stats1['ET DMA BHB T']:.4f}"),
                ('Moyenne DMA ADV', f"{stats1['Moy DMA ADV 1']:.4f}", f"{stats1['Moy DMA ADV 2']:.4f}", f"{stats1['Moy DMA ADV T']:.4f}"),
                ('Écart Type DMA ADV', f"{stats1['ET DMA ADV 1']:.4f}", f"{stats1['ET DMA ADV 2']:.4f}", f"{stats1['ET DMA ADV T']:.4f}"),
                ('Rapport de Force', f"{stats1['RdF 1']:.4f}", f"{stats1['RdF 2']:.4f}", f"{stats1['RdF T']:.4f}"),
            ]
            for ind, mt1, mt2, total in indicators:
                data1.append({'Indicateur': ind, '1ère MT': mt1, '2ème MT': mt2, 'Total': total})
            
            st.dataframe(pd.DataFrame(data1), use_container_width=True, hide_index=True, height=700)
        else:
            st.info("Aucune donnée")
    
    with col_g2:
        st.markdown(f"#### {label2}")
        stats2 = calculate_general_stats(df, matches2)
        if stats2:
            data2 = []
            indicators = [
                ('Score', f"{stats2['Buts BHB 1']}-{stats2['Buts ADV 1']}", f"{stats2['Buts BHB 2']}-{stats2['Buts ADV 2']}", f"{stats2['Buts BHB T']}-{stats2['Buts ADV T']}"),
                ('Buts Pour', stats2['Buts BHB 1'], stats2['Buts BHB 2'], stats2['Buts BHB T']),
                ('Buts Contre', stats2['Buts ADV 1'], stats2['Buts ADV 2'], stats2['Buts ADV T']),
                ('Nb Possessions', stats2['Poss Total 1'], stats2['Poss Total 2'], stats2['Poss Total T']),
                ('Rythme (Poss/30min)', f"{stats2['Rythme 1']:.2f}", f"{stats2['Rythme 2']:.2f}", f"{stats2['Rythme T']:.2f}"),
                ('Ratio But/Poss BHB', f"{stats2['Ratio But/Poss 1']:.1%}", f"{stats2['Ratio But/Poss 2']:.1%}", f"{stats2['Ratio But/Poss T']:.1%}"),
                ('Efficacité Défensive', f"{stats2['Eff Def 1']:.1%}", f"{stats2['Eff Def 2']:.1%}", f"{stats2['Eff Def T']:.1%}"),
                ('Efficacité Tir', f"{stats2['Eff Tir 1']:.1%}", f"{stats2['Eff Tir 2']:.1%}", f"{stats2['Eff Tir T']:.1%}"),
                ('Déchet Technique', stats2['Déchet 1'], stats2['Déchet 2'], stats2['Déchet T']),
                ('Ratio Perte/Poss', f"{stats2['Ratio Perte 1']:.1%}", f"{stats2['Ratio Perte 2']:.1%}", f"{stats2['Ratio Perte T']:.1%}"),
                ('Nb INF', stats2['Nb INF 1'], stats2['Nb INF 2'], stats2['Nb INF T']),
                ('Écart sur INF', stats2['Ecart INF 1'], stats2['Ecart INF 2'], stats2['Ecart INF T']),
                ('Moy Écart INF', f"{stats2['Moy Ecart INF 1']:.2f}", f"{stats2['Moy Ecart INF 2']:.2f}", f"{stats2['Moy Ecart INF T']:.2f}"),
                ('Nb SUP', stats2['Nb SUP 1'], stats2['Nb SUP 2'], stats2['Nb SUP T']),
                ('Écart sur SUP', stats2['Ecart SUP 1'], stats2['Ecart SUP 2'], stats2['Ecart SUP T']),
                ('Moy Écart SUP', f"{stats2['Moy Ecart SUP 1']:.2f}", f"{stats2['Moy Ecart SUP 2']:.2f}", f"{stats2['Moy Ecart SUP T']:.2f}"),
                ('Moyenne DMA BHB', f"{stats2['Moy DMA BHB 1']:.4f}", f"{stats2['Moy DMA BHB 2']:.4f}", f"{stats2['Moy DMA BHB T']:.4f}"),
                ('Écart Type DMA BHB', f"{stats2['ET DMA BHB 1']:.4f}", f"{stats2['ET DMA BHB 2']:.4f}", f"{stats2['ET DMA BHB T']:.4f}"),
                ('Moyenne DMA ADV', f"{stats2['Moy DMA ADV 1']:.4f}", f"{stats2['Moy DMA ADV 2']:.4f}", f"{stats2['Moy DMA ADV T']:.4f}"),
                ('Écart Type DMA ADV', f"{stats2['ET DMA ADV 1']:.4f}", f"{stats2['ET DMA ADV 2']:.4f}", f"{stats2['ET DMA ADV T']:.4f}"),
                ('Rapport de Force', f"{stats2['RdF 1']:.4f}", f"{stats2['RdF 2']:.4f}", f"{stats2['RdF T']:.4f}"),
            ]
            for ind, mt1, mt2, total in indicators:
                data2.append({'Indicateur': ind, '1ère MT': mt1, '2ème MT': mt2, 'Total': total})
            
            st.dataframe(pd.DataFrame(data2), use_container_width=True, hide_index=True, height=700)
        else:
            st.info("Aucune donnée")

# NOUVEAU: Stats Buteurs
with t5:
    st.markdown("### 🎯 Statistiques des Buteurs")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown(f"#### {label1}")
        shooters1 = calculate_shooter_stats(df, matches1)
        if shooters1 is not None and len(shooters1) > 0:
            st.dataframe(shooters1.style.format({
                'Eff 1': '{:.1%}',
                'Eff 2': '{:.1%}',
                'Eff Total': '{:.1%}'
            }), use_container_width=True, hide_index=True, height=600)
        else:
            st.info("Aucun buteur")
    
    with col_s2:
        st.markdown(f"#### {label2}")
        shooters2 = calculate_shooter_stats(df, matches2)
        if shooters2 is not None and len(shooters2) > 0:
            st.dataframe(shooters2.style.format({
                'Eff 1': '{:.1%}',
                'Eff 2': '{:.1%}',
                'Eff Total': '{:.1%}'
            }), use_container_width=True, hide_index=True, height=600)
        else:
            st.info("Aucun buteur")

st.markdown("---")
st.markdown("*BHB Analytics v4.0 | Dashboard Handball Complet*")
