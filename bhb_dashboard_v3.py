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
    z = np.polyfit(x, y, 3)
    p = np.poly1d(z)
    return p(x)

def calculate_general_stats(df, matches):
    """Calcule les statistiques générales en MOYENNE PAR MATCH (DMA déjà en moyenne).
    Note: les ratios/efficacités sont moyennés par match (non pondérés).
    """
    if df is None or len(matches) == 0:
        return None

    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None

    def _period_stats(period_data):
        """Stats d'une période pour UN match (mt1 / mt2 / total)."""
        if period_data is None or len(period_data) == 0:
            return None

        bhb_data = period_data[period_data['Equipe'] == 'BHB']
        adv_data = period_data[period_data['Equipe'] == 'ADV']

        buts_bhb = float(bhb_data['Issue'].sum())
        buts_adv = float(adv_data['Issue'].sum())

        poss_bhb = float(len(bhb_data))
        poss_adv = float(len(adv_data))
        poss_total = float(len(period_data))

        stats = {}
        stats['Buts BHB'] = buts_bhb
        stats['Buts ADV'] = buts_adv
        stats['Poss BHB'] = poss_bhb
        stats['Poss ADV'] = poss_adv
        stats['Poss Total'] = poss_total

        # Ratios / Eff (calculés sur le match, puis moyennés entre matchs)
        stats['Ratio But/Poss'] = (buts_bhb / poss_bhb) if poss_bhb > 0 else 0.0
        stats['Eff Def'] = ((poss_adv - buts_adv) / poss_adv) if poss_adv > 0 else 0.0

        # Déchet
        dechet = float(len(bhb_data[(bhb_data['Tireur'].isna()) | (bhb_data['Tireur'] == 0)]))
        stats['Déchet'] = dechet

        tirs_effectifs = poss_bhb - dechet
        stats['Eff Tir'] = (buts_bhb / tirs_effectifs) if tirs_effectifs > 0 else 0.0
        stats['Ratio Perte'] = (dechet / poss_bhb) if poss_bhb > 0 else 0.0

        # DMA (déjà des moyennes)
        dma_bhb_vals = bhb_data['DMA BHB'].dropna()
        dma_adv_vals = adv_data['DMA ADV'].dropna()

        stats['Moy DMA BHB'] = float(dma_bhb_vals.mean()) if len(dma_bhb_vals) > 0 else 0.0
        stats['ET DMA BHB'] = float(dma_bhb_vals.std()) if len(dma_bhb_vals) > 0 else 0.0
        stats['Moy DMA ADV'] = float(dma_adv_vals.mean()) if len(dma_adv_vals) > 0 else 0.0
        stats['ET DMA ADV'] = float(dma_adv_vals.std()) if len(dma_adv_vals) > 0 else 0.0
        stats['RdF'] = stats['Moy DMA BHB'] - stats['Moy DMA ADV']

        # INF / SUP : comptage par match (important)
        period_sorted = period_data.sort_index()

        inf_mask = (period_sorted['INF'] == 'INF')
        inf_changes = inf_mask.astype(int).diff().fillna(0)
        nb_inf = float((inf_changes == 1).sum())

        inf_possessions = period_sorted[inf_mask]
        if len(inf_possessions) > 0:
            bhb_inf = inf_possessions[(inf_possessions['Equipe'] == 'BHB') & (inf_possessions['Issue'] == 1)]
            adv_inf = inf_possessions[(inf_possessions['Equipe'] == 'ADV') & (inf_possessions['Issue'] == 1)]
            ecart_inf = float(len(bhb_inf) - len(adv_inf))
        else:
            ecart_inf = 0.0

        sup_mask = (period_sorted['SUP'] == 'SUP')
        sup_changes = sup_mask.astype(int).diff().fillna(0)
        nb_sup = float((sup_changes == 1).sum())

        sup_possessions = period_sorted[sup_mask]
        if len(sup_possessions) > 0:
            bhb_sup = sup_possessions[(sup_possessions['Equipe'] == 'BHB') & (sup_possessions['Issue'] == 1)]
            adv_sup = sup_possessions[(sup_possessions['Equipe'] == 'ADV') & (sup_possessions['Issue'] == 1)]
            ecart_sup = float(len(bhb_sup) - len(adv_sup))
        else:
            ecart_sup = 0.0

        stats['Nb INF'] = nb_inf
        stats['Nb SUP'] = nb_sup
        stats['Ecart INF'] = ecart_inf
        stats['Ecart SUP'] = ecart_sup
        stats['Moy Ecart INF'] = (ecart_inf / nb_inf) if nb_inf > 0 else 0.0
        stats['Moy Ecart SUP'] = (ecart_sup / nb_sup) if nb_sup > 0 else 0.0

        return stats

    # Collecte match par match
    per_match = {'1': [], '2': [], 'T': []}

    for m in matches:
        mdf = filtered_df[filtered_df['Match'] == m]
        if len(mdf) == 0:
            continue

        mt1 = mdf[mdf['Minute'] <= 30]
        mt2 = mdf[mdf['Minute'] > 30]

        s1 = _period_stats(mt1)
        s2 = _period_stats(mt2)
        sT = _period_stats(mdf)

        if s1 is not None:
            # Rythme: possessions / durée (par match)
            s1['Rythme'] = float(len(mt1)) / 30.0
            per_match['1'].append(s1)
        if s2 is not None:
            s2['Rythme'] = float(len(mt2)) / 30.0
            per_match['2'].append(s2)
        if sT is not None:
            sT['Rythme'] = float(len(mdf)) / 60.0
            per_match['T'].append(sT)

    # Agrégation: moyenne simple entre matchs
    out = {}
    for suffix, rows in per_match.items():
        if len(rows) == 0:
            continue

        keys = rows[0].keys()
        for k in keys:
            vals = [r.get(k, 0.0) for r in rows]
            out[f'{k} {suffix}'] = float(np.mean(vals)) if len(vals) > 0 else 0.0

    return out

def calculate_shooter_stats(df, matches):
    """Calcule stats buteurs - VERSION OPTIMISÉE"""
    if df is None or len(matches) == 0:
        return None
    
    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None
    
    bhb_data = filtered_df[filtered_df['Equipe'] == 'BHB'].copy()
    if len(bhb_data) == 0:
        return None
    
    # Ajouter colonne mi-temps
    bhb_data['MT'] = (bhb_data['Minute'] > 30).astype(int) + 1
    
    # Remplacer Tireur vide
    bhb_data['Tireur'] = bhb_data['Tireur'].fillna('(Inconnu)')
    bhb_data['Tireur'] = bhb_data['Tireur'].replace(0, '(Inconnu)')
    
    # Grouper par tireur et mi-temps
    grouped = bhb_data.groupby(['Tireur', 'MT']).agg({
        'Issue': ['count', 'sum']
    }).reset_index()
    
    grouped.columns = ['Joueur', 'MT', 'Tirs', 'Buts']
    
    # Pivot pour avoir MT1 et MT2
    pivot = grouped.pivot(index='Joueur', columns='MT', values=['Tirs', 'Buts']).fillna(0)
    
    # Calculer totaux et efficacités
    result = pd.DataFrame()
    result['Joueur'] = pivot.index
    result['Tirs 1'] = pivot[('Tirs', 1)].values.astype(int)
    result['Buts 1'] = pivot[('Buts', 1)].values.astype(int)
    result['Eff 1'] = (result['Buts 1'] / result['Tirs 1']).where(result['Tirs 1'] > 0, 0)
    result['Tirs 2'] = pivot[('Tirs', 2)].values.astype(int)
    result['Buts 2'] = pivot[('Buts', 2)].values.astype(int)
    result['Eff 2'] = (result['Buts 2'] / result['Tirs 2']).where(result['Tirs 2'] > 0, 0)
    result['Tirs Total'] = result['Tirs 1'] + result['Tirs 2']
    result['Buts Total'] = result['Buts 1'] + result['Buts 2']
    result['Eff Total'] = (result['Buts Total'] / result['Tirs Total']).where(result['Tirs Total'] > 0, 0)
    
    # Trier par buts totaux
    result = result.sort_values('Buts Total', ascending=False).reset_index(drop=True)
    
    return result

def chart(d1, d2, l1, l2, metric, title, show_trend=False):
    fig = go.Figure()
    
    if d1 is not None:
        fig.add_trace(go.Scatter(
            x=d1['Minute'], y=d1[metric], name=l1, 
            line=dict(color='#667eea', width=4),
            hovertemplate='<b>' + l1 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        if show_trend and len(d1) > 3:
            trend1 = calculate_trend(d1['Minute'].values, d1[metric].values)
            fig.add_trace(go.Scatter(
                x=d1['Minute'], y=trend1, name=f'{l1} - Tendance',
                line=dict(color='#667eea', width=2, dash='dot'), opacity=0.6
            ))
    
    if d2 is not None:
        fig.add_trace(go.Scatter(
            x=d2['Minute'], y=d2[metric], name=l2,
            line=dict(color='#f5576c', width=4, dash='dash'),
            hovertemplate='<b>' + l2 + '</b><br>Minute: %{x}<br>' + metric + ': %{y:.3f}<extra></extra>'
        ))
        if show_trend and len(d2) > 3:
            trend2 = calculate_trend(d2['Minute'].values, d2[metric].values)
            fig.add_trace(go.Scatter(
                x=d2['Minute'], y=trend2, name=f'{l2} - Tendance',
                line=dict(color='#f5576c', width=2, dash='dot'), opacity=0.6
            ))
    
    if 'Rapport' in metric:
        fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, opacity=0.5)
    
    fig.update_layout(
        title=title, height=600, hovermode='x unified',
        plot_bgcolor='white', font=dict(family='Inter, sans-serif'),
        xaxis=dict(title="Minute", gridcolor='rgba(0,0,0,0.1)'),
        yaxis=dict(title=metric, gridcolor='rgba(0,0,0,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

st.title("BHB Analytics")

# Chargement
df = None
if os.path.exists('Base_Donnees_Handball.xlsx'):
    df = load_data('Base_Donnees_Handball.xlsx')
    st.sidebar.success("✅ Données chargées")
else:
    st.sidebar.error("❌ Fichier non trouvé")
    st.stop()

if df is None:
    st.stop()

# Sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔵 GROUPE 1")
    
    mode1 = st.radio("Mode", ["⚡ Phase", "🏠 Lieu", "📋 Matchs"], key="mode1")
    
    if mode1 == "⚡ Phase":
        phase1 = st.selectbox("Phase", ['ALLER', 'RETOUR'], key="p1")
        matches1 = df[df['Phase'] == phase1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs")
    elif mode1 == "🏠 Lieu":
        lieu1 = st.selectbox("Lieu", ['Domicile', 'Extérieur'], key="l1")
        matches1 = df[df['Lieu'] == lieu1]['Match'].unique().tolist()
        st.info(f"📊 {len(matches1)} matchs")
    else:
        matches1 = st.multiselect("Matchs", sorted(df['Match'].unique()), 
                                  default=[sorted(df['Match'].unique())[0]], key="m1")
    
    label1 = st.text_input("Nom", "Groupe 1", key="la1")
    
    st.markdown("---")
    st.markdown("### 🔴 GROUPE 2")
    
    mode2 = st.radio("Mode", ["⚡ Phase", "🏠 Lieu", "📋 Matchs"], key="mode2")
    
    if mode2 == "⚡ Phase":
        phase2 = st.selectbox("Phase", ['ALLER', 'RETOUR'], index=1, key="p2")
        matches2 = df[df['Phase'] == phase2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs")
    elif mode2 == "🏠 Lieu":
        lieu2 = st.selectbox("Lieu", ['Domicile', 'Extérieur'], index=1, key="l2")
        matches2 = df[df['Lieu'] == lieu2]['Match'].unique().tolist()
        st.info(f"📊 {len(matches2)} matchs")
    else:
        matches2 = st.multiselect("Matchs", sorted(df['Match'].unique()),
                                  default=[sorted(df['Match'].unique())[1]] if len(df['Match'].unique()) > 1 else [],
                                  key="m2")
    
    label2 = st.text_input("Nom", "Groupe 2", key="la2")

st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**🔵 {label1}** : {len(matches1)} matchs")
with col2:
    st.markdown(f"**🔴 {label2}** : {len(matches2)} matchs")

# Tabs
t1, t2, t3, t4, t5 = st.tabs(["📈 DMA BHB", "📊 DMA ADV", "⚖️ Rapport de Force", "📋 Stats Générales", "🎯 Buteurs"])

d1 = aggregate(df, matches1)
d2 = aggregate(df, matches2)

if d1 is None and d2 is None:
    st.warning("⚠️ Sélectionnez des matchs")
    st.stop()

with t1:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA BHB', 'DMA BHB'), use_container_width=True)

with t2:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA ADV', 'DMA ADV'), use_container_width=True)

with t3:
    show_trend = st.checkbox("Afficher tendances", value=True)
    st.plotly_chart(chart(d1, d2, label1, label2, 'Rapport de force', 'Rapport de Force', show_trend), use_container_width=True)

with t4:
    st.markdown("### 📋 Statistiques Générales")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown(f"#### {label1}")
        stats1 = calculate_general_stats(df, matches1)
        if stats1:
            data1 = [
              
                {'Indicateur': 'Score', '1ère MT': f"{stats1['Buts BHB 1']}-{stats1['Buts ADV 1']}", 
                 '2ème MT': f"{stats1['Buts BHB 2']}-{stats1['Buts ADV 2']}", 'Total': f"{stats1['Buts BHB T']}-{stats1['Buts ADV T']}"},
                {'Indicateur': 'Buts Pour', '1ère MT': stats1['Buts BHB 1'], '2ème MT': stats1['Buts BHB 2'], 'Total': stats1['Buts BHB T']},
                {'Indicateur': 'Buts Contre', '1ère MT': stats1['Buts ADV 1'], '2ème MT': stats1['Buts ADV 2'], 'Total': stats1['Buts ADV T']},
                {'Indicateur': 'Nb Possessions', '1ère MT': stats1['Poss Total 1'], '2ème MT': stats1['Poss Total 2'], 'Total': stats1['Poss Total T']},
                {'Indicateur': 'Rythme', '1ère MT': f"{stats1['Rythme 1']:.2f}", '2ème MT': f"{stats1['Rythme 2']:.2f}", 'Total': f"{stats1['Rythme T']:.2f}"},
                {'Indicateur': 'Ratio But/Poss', '1ère MT': f"{stats1['Ratio But/Poss 1']:.1%}", '2ème MT': f"{stats1['Ratio But/Poss 2']:.1%}", 'Total': f"{stats1['Ratio But/Poss T']:.1%}"},
                {'Indicateur': 'Eff Défensive', '1ère MT': f"{stats1['Eff Def 1']:.1%}", '2ème MT': f"{stats1['Eff Def 2']:.1%}", 'Total': f"{stats1['Eff Def T']:.1%}"},
                {'Indicateur': 'Eff Tir', '1ère MT': f"{stats1['Eff Tir 1']:.1%}", '2ème MT': f"{stats1['Eff Tir 2']:.1%}", 'Total': f"{stats1['Eff Tir T']:.1%}"},
                {'Indicateur': 'Déchet Tech', '1ère MT': stats1['Déchet 1'], '2ème MT': stats1['Déchet 2'], 'Total': stats1['Déchet T']},
                {'Indicateur': 'Nb INF', '1ère MT': stats1['Nb INF 1'], '2ème MT': stats1['Nb INF 2'], 'Total': stats1['Nb INF T']},
                {'Indicateur': 'Écart INF', '1ère MT': stats1['Ecart INF 1'], '2ème MT': stats1['Ecart INF 2'], 'Total': stats1['Ecart INF T']},
                {'Indicateur': 'Nb SUP', '1ère MT': stats1['Nb SUP 1'], '2ème MT': stats1['Nb SUP 2'], 'Total': stats1['Nb SUP T']},
                {'Indicateur': 'Écart SUP', '1ère MT': stats1['Ecart SUP 1'], '2ème MT': stats1['Ecart SUP 2'], 'Total': stats1['Ecart SUP T']},
                {'Indicateur': 'Moy DMA BHB', '1ère MT': f"{stats1['Moy DMA BHB 1']:.3f}", '2ème MT': f"{stats1['Moy DMA BHB 2']:.3f}", 'Total': f"{stats1['Moy DMA BHB T']:.3f}"},
                {'Indicateur': 'Moy DMA ADV', '1ère MT': f"{stats1['Moy DMA ADV 1']:.3f}", '2ème MT': f"{stats1['Moy DMA ADV 2']:.3f}", 'Total': f"{stats1['Moy DMA ADV T']:.3f}"},
                {'Indicateur': 'Rapport de Force', '1ère MT': f"{stats1['RdF 1']:.3f}", '2ème MT': f"{stats1['RdF 2']:.3f}", 'Total': f"{stats1['RdF T']:.3f}"},
            ]
            st.dataframe(pd.DataFrame(data1), use_container_width=True, hide_index=True, height=600)
    
    with col_g2:
        st.markdown(f"#### {label2}")
        stats2 = calculate_general_stats(df, matches2)
        if stats2:
            data2 = [
                {'Indicateur': 'Score', '1ère MT': f"{stats2['Buts BHB 1']}-{stats2['Buts ADV 1']}", 
                 '2ème MT': f"{stats2['Buts BHB 2']}-{stats2['Buts ADV 2']}", 'Total': f"{stats2['Buts BHB T']}-{stats2['Buts ADV T']}"},
                {'Indicateur': 'Buts Pour', '1ère MT': stats2['Buts BHB 1'], '2ème MT': stats2['Buts BHB 2'], 'Total': stats2['Buts BHB T']},
                {'Indicateur': 'Buts Contre', '1ère MT': stats2['Buts ADV 1'], '2ème MT': stats2['Buts ADV 2'], 'Total': stats2['Buts ADV T']},
                {'Indicateur': 'Nb Possessions', '1ère MT': stats2['Poss Total 1'], '2ème MT': stats2['Poss Total 2'], 'Total': stats2['Poss Total T']},
                {'Indicateur': 'Rythme', '1ère MT': f"{stats2['Rythme 1']:.2f}", '2ème MT': f"{stats2['Rythme 2']:.2f}", 'Total': f"{stats2['Rythme T']:.2f}"},
                {'Indicateur': 'Ratio But/Poss', '1ère MT': f"{stats2['Ratio But/Poss 1']:.1%}", '2ème MT': f"{stats2['Ratio But/Poss 2']:.1%}", 'Total': f"{stats2['Ratio But/Poss T']:.1%}"},
                {'Indicateur': 'Eff Défensive', '1ère MT': f"{stats2['Eff Def 1']:.1%}", '2ème MT': f"{stats2['Eff Def 2']:.1%}", 'Total': f"{stats2['Eff Def T']:.1%}"},
                {'Indicateur': 'Eff Tir', '1ère MT': f"{stats2['Eff Tir 1']:.1%}", '2ème MT': f"{stats2['Eff Tir 2']:.1%}", 'Total': f"{stats2['Eff Tir T']:.1%}"},
                {'Indicateur': 'Déchet Tech', '1ère MT': stats2['Déchet 1'], '2ème MT': stats2['Déchet 2'], 'Total': stats2['Déchet T']},
                {'Indicateur': 'Nb INF', '1ère MT': stats2['Nb INF 1'], '2ème MT': stats2['Nb INF 2'], 'Total': stats2['Nb INF T']},
                {'Indicateur': 'Écart INF', '1ère MT': stats2['Ecart INF 1'], '2ème MT': stats2['Ecart INF 2'], 'Total': stats2['Ecart INF T']},
                {'Indicateur': 'Nb SUP', '1ère MT': stats2['Nb SUP 1'], '2ème MT': stats2['Nb SUP 2'], 'Total': stats2['Nb SUP T']},
                {'Indicateur': 'Écart SUP', '1ère MT': stats2['Ecart SUP 1'], '2ème MT': stats2['Ecart SUP 2'], 'Total': stats2['Ecart SUP T']},
                {'Indicateur': 'Moy DMA BHB', '1ère MT': f"{stats2['Moy DMA BHB 1']:.3f}", '2ème MT': f"{stats2['Moy DMA BHB 2']:.3f}", 'Total': f"{stats2['Moy DMA BHB T']:.3f}"},
                {'Indicateur': 'Moy DMA ADV', '1ère MT': f"{stats2['Moy DMA ADV 1']:.3f}", '2ème MT': f"{stats2['Moy DMA ADV 2']:.3f}", 'Total': f"{stats2['Moy DMA ADV T']:.3f}"},
                {'Indicateur': 'Rapport de Force', '1ère MT': f"{stats2['RdF 1']:.3f}", '2ème MT': f"{stats2['RdF 2']:.3f}", 'Total': f"{stats2['RdF T']:.3f}"},
            ]
            st.dataframe(pd.DataFrame(data2), use_container_width=True, hide_index=True, height=600)

with t5:
    st.markdown("### 🎯 Buteurs")
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown(f"#### {label1}")
        shooters1 = calculate_shooter_stats(df, matches1)
        if shooters1 is not None and len(shooters1) > 0:
            st.dataframe(shooters1.style.format({
                'Eff 1': '{:.1%}', 'Eff 2': '{:.1%}', 'Eff Total': '{:.1%}'
            }), use_container_width=True, hide_index=True, height=600)
    
    with col_s2:
        st.markdown(f"#### {label2}")
        shooters2 = calculate_shooter_stats(df, matches2)
        if shooters2 is not None and len(shooters2) > 0:
            st.dataframe(shooters2.style.format({
                'Eff 1': '{:.1%}', 'Eff 2': '{:.1%}', 'Eff Total': '{:.1%}'
            }), use_container_width=True, hide_index=True, height=600)

st.markdown("---")
st.markdown("*BHB Analytics v4.1*")
