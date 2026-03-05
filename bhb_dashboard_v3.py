#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="BHB Analytics", layout="wide")

# CSS pour fixer la colonne Joueur
st.markdown("""
<style>
/* Fixer la première colonne du tableau buteurs */
.stDataFrame table {
    position: relative;
}
.stDataFrame thead th:first-child,
.stDataFrame tbody td:first-child {
    position: sticky;
    left: 0;
    background: white;
    z-index: 2;
    border-right: 2px solid #ddd;
}
.stDataFrame thead th:first-child {
    z-index: 3;
}
</style>
""", unsafe_allow_html=True)

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
    """Calcule les statistiques générales - VERSION MODIFIÉE"""
    if df is None or len(matches) == 0:
        return None

    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None

    def _period_stats(period_data):
        if period_data is None or len(period_data) == 0:
            return None

        bhb_data = period_data[period_data['Equipe'] == 'BHB']
        adv_data = period_data[period_data['Equipe'] == 'ADV']

        buts_bhb = float(bhb_data['Issue'].sum())
        buts_adv = float(adv_data['Issue'].sum())

        poss_bhb = float(len(bhb_data))
        poss_adv = float(len(adv_data))
        poss_total = float(len(period_data))

        dechet = float(len(bhb_data[(bhb_data['Tireur'].isna()) | (bhb_data['Tireur'] == 0)]))
        tirs_effectifs = poss_bhb - dechet

        dma_bhb_vals = bhb_data['DMA BHB'].dropna()
        dma_adv_vals = adv_data['DMA ADV'].dropna()

        moy_dma_bhb = float(dma_bhb_vals.mean()) if len(dma_bhb_vals) > 0 else 0.0
        et_dma_bhb = float(dma_bhb_vals.std()) if len(dma_bhb_vals) > 0 else 0.0
        moy_dma_adv = float(dma_adv_vals.mean()) if len(dma_adv_vals) > 0 else 0.0
        et_dma_adv = float(dma_adv_vals.std()) if len(dma_adv_vals) > 0 else 0.0
        rdf = moy_dma_bhb - moy_dma_adv

        period_sorted = period_data.sort_index()

        # INF
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

        # SUP
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

        return {
            'Buts BHB': buts_bhb,
            'Buts ADV': buts_adv,
            'Poss BHB': poss_bhb,
            'Poss ADV': poss_adv,
            'Poss Total': poss_total,
            'Déchet': dechet,
            'Tirs Effectifs': tirs_effectifs,
            'Moy DMA BHB': moy_dma_bhb,
            'ET DMA BHB': et_dma_bhb,
            'Moy DMA ADV': moy_dma_adv,
            'ET DMA ADV': et_dma_adv,
            'RdF': rdf,
            'Nb INF': nb_inf,
            'Ecart INF': ecart_inf,
            'Nb SUP': nb_sup,
            'Ecart SUP': ecart_sup
        }

    # Par match
    all_matches = filtered_df['Match'].unique()
    rows_1 = []
    rows_2 = []
    rows_T = []

    for match in all_matches:
        match_data = filtered_df[filtered_df['Match'] == match]
        mt1 = match_data[match_data['Minute'] <= 30]
        mt2 = match_data[match_data['Minute'] > 30]

        s1 = _period_stats(mt1)
        s2 = _period_stats(mt2)
        sT = _period_stats(match_data)

        if s1: rows_1.append(s1)
        if s2: rows_2.append(s2)
        if sT: rows_T.append(sT)

    out = {}

    ratio_out_keys = [
        'Ratio But/Poss', 'Taux Déchet', 'Eff Def', 'Eff Tir', 'Ratio Perte',
        'Moy Ecart INF', 'Moy Ecart SUP'
    ]

    for suffix, rows in [('1', rows_1), ('2', rows_2), ('T', rows_T)]:
        if len(rows) == 0:
            continue

        all_keys = set(rows[0].keys())
        internal_exclude = {'Tirs Effectifs'}
        volume_keys = [k for k in all_keys if k not in set(ratio_out_keys) and k not in internal_exclude]

        for k in volume_keys:
            vals = [r.get(k, 0.0) for r in rows]
            out[f'{k} {suffix}'] = float(np.mean(vals))

        # Ratios pondérés
        sum_buts_bhb = sum(r.get('Buts BHB', 0.0) for r in rows)
        sum_poss_bhb = sum(r.get('Poss BHB', 0.0) for r in rows)
        sum_poss_adv = sum(r.get('Poss ADV', 0.0) for r in rows)
        sum_buts_adv = sum(r.get('Buts ADV', 0.0) for r in rows)
        sum_dechet = sum(r.get('Déchet', 0.0) for r in rows)
        sum_tirs_effectifs = sum(r.get('Tirs Effectifs', 0.0) for r in rows)
        sum_ecart_inf = sum(r.get('Ecart INF', 0.0) for r in rows)
        sum_nb_inf = sum(r.get('Nb INF', 0.0) for r in rows)
        sum_ecart_sup = sum(r.get('Ecart SUP', 0.0) for r in rows)
        sum_nb_sup = sum(r.get('Nb SUP', 0.0) for r in rows)

        out[f'Ratio But/Poss {suffix}'] = (sum_buts_bhb / sum_poss_bhb) if sum_poss_bhb > 0 else 0.0
        out[f'Taux Déchet {suffix}'] = (sum_dechet / sum_poss_bhb) if sum_poss_bhb > 0 else 0.0
        out[f'Eff Def {suffix}'] = ((sum_poss_adv - sum_buts_adv) / sum_poss_adv) if sum_poss_adv > 0 else 0.0
        out[f'Eff Tir {suffix}'] = (sum_buts_bhb / sum_tirs_effectifs) if sum_tirs_effectifs > 0 else 0.0
        out[f'Moy Ecart INF {suffix}'] = (sum_ecart_inf / sum_nb_inf) if sum_nb_inf > 0 else 0.0
        out[f'Moy Ecart SUP {suffix}'] = (sum_ecart_sup / sum_nb_sup) if sum_nb_sup > 0 else 0.0

        # Rythme
        duree = 30 if suffix != 'T' else 60
        poss_total_sum = sum(r.get('Poss Total', 0.0) for r in rows)
        out[f'Rythme {suffix}'] = poss_total_sum / (len(rows) * duree) if len(rows) > 0 else 0.0

    return out


def calculate_shooter_stats(df, matches):
    """Calcule stats buteurs - VERSION OPTIMISÉE avec mapping joueurs"""
    if df is None or len(matches) == 0:
        return None
    
    player_mapping = {
        2: "NAUDIN Paul", 3: "NAUDIN Théo", 25: "FAVERIN Léan",
        7: "PLISSONNIER Jean", 8: "PANIC Milan", 9: "MINANA Lilian",
        10: "GREGULSKI Vincent", 12: "STEPHAN Corentin", 13: "THELCIDE Axel",
        15: "COSNIER Lubin", 16: "MAI François", 19: "GOSTOMSKI Sasha",
        21: "CHAZALON Marius", 24: "MINY Gabin", 4: "HERMAND Mathieu",
        33: "NAUDIN Hugo", 78: "LAURENCE Samuel", 92: "PHAROSE Kylian"
    }
    
    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None
    
    bhb_data = filtered_df[filtered_df['Equipe'] == 'BHB'].copy()
    if len(bhb_data) == 0:
        return None
    
    bhb_data = bhb_data[
        (bhb_data['Tireur'].notna()) & 
        (bhb_data['Tireur'] != 0) & 
        (bhb_data['Tireur'] != '')
    ].copy()
    
    if len(bhb_data) == 0:
        return None
    
    bhb_data['MT'] = (bhb_data['Minute'] > 30).astype(int) + 1
    bhb_data['Tireur'] = bhb_data['Tireur'].astype(int)
    
    grouped = bhb_data.groupby(['Tireur', 'MT']).agg({
        'Issue': ['count', 'sum']
    }).reset_index()
    
    grouped.columns = ['Numero', 'MT', 'Tirs', 'Buts']
    pivot = grouped.pivot(index='Numero', columns='MT', values=['Tirs', 'Buts']).fillna(0)
    
    result = pd.DataFrame()
    result['Numero'] = pivot.index
    result['Joueur'] = result['Numero'].map(player_mapping).fillna('Inconnu')
    
    result['Tirs 1'] = pivot[('Tirs', 1)].values.astype(int)
    result['Buts 1'] = pivot[('Buts', 1)].values.astype(int)
    result['Eff 1'] = (result['Buts 1'] / result['Tirs 1']).where(result['Tirs 1'] > 0, 0)
    result['Tirs 2'] = pivot[('Tirs', 2)].values.astype(int)
    result['Buts 2'] = pivot[('Buts', 2)].values.astype(int)
    result['Eff 2'] = (result['Buts 2'] / result['Tirs 2']).where(result['Tirs 2'] > 0, 0)
    result['Tirs Total'] = result['Tirs 1'] + result['Tirs 2']
    result['Buts Total'] = result['Buts 1'] + result['Buts 2']
    result['Eff Total'] = (result['Buts Total'] / result['Tirs Total']).where(result['Tirs Total'] > 0, 0)
    
    result = result[['Joueur', 'Tirs 1', 'Buts 1', 'Eff 1', 'Tirs 2', 'Buts 2', 'Eff 2', 'Tirs Total', 'Buts Total', 'Eff Total']]
    result = result.sort_values('Buts Total', ascending=False).reset_index(drop=True)
    
    return result

def apply_colors(df_stats):
    """Applique les couleurs de manière optimisée"""
    def style_cell(val, indicator):
        if indicator == 'Taux Déchet':
            return color_dechet(val)
        else:
            return color_ratio(val)
    
    # Créer un styler
    styler = df_stats.style
    
    # Appliquer les couleurs ligne par ligne
    for idx in df_stats.index:
        indicator = df_stats.loc[idx, 'Indicateur']
        for col in ['1ère MT', '2ème MT', 'Total']:
            val = df_stats.loc[idx, col]
            style = style_cell(val, indicator)
            if style:
                styler = styler.applymap(lambda x: style, subset=pd.IndexSlice[idx, col])
    
    return styler

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

st.title("🤾 BHB Analytics")

df = None
if os.path.exists('Base_Donnees_Handball.xlsx'):
    df = load_data('Base_Donnees_Handball.xlsx')
    st.sidebar.success("✅ Données chargées")
else:
    st.sidebar.error("❌ Fichier non trouvé")
    st.stop()

if df is None:
    st.stop()

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
                {'Indicateur': 'Score', '1ère MT': f"{stats1['Buts BHB 1']:.1f}-{stats1['Buts ADV 1']:.1f}", 
                 '2ème MT': f"{stats1['Buts BHB 2']:.1f}-{stats1['Buts ADV 2']:.1f}", 'Total': f"{stats1['Buts BHB T']:.1f}-{stats1['Buts ADV T']:.1f}"},
                {'Indicateur': 'Buts Pour', '1ère MT': f"{stats1['Buts BHB 1']:.1f}", '2ème MT': f"{stats1['Buts BHB 2']:.1f}", 'Total': f"{stats1['Buts BHB T']:.1f}"},
                {'Indicateur': 'Buts Contre', '1ère MT': f"{stats1['Buts ADV 1']:.1f}", '2ème MT': f"{stats1['Buts ADV 2']:.1f}", 'Total': f"{stats1['Buts ADV T']:.1f}"},
                {'Indicateur': 'Nb Possessions', '1ère MT': f"{stats1['Poss Total 1']:.1f}", '2ème MT': f"{stats1['Poss Total 2']:.1f}", 'Total': f"{stats1['Poss Total T']:.1f}"},
                {'Indicateur': 'Rythme', '1ère MT': f"{stats1.get('Rythme 1', 0):.2f}", '2ème MT': f"{stats1.get('Rythme 2', 0):.2f}", 'Total': f"{stats1.get('Rythme T', 0):.2f}"},
                {'Indicateur': 'Ratio But/Poss', '1ère MT': f"{stats1['Ratio But/Poss 1']*100:.1f}%", '2ème MT': f"{stats1['Ratio But/Poss 2']*100:.1f}%", 'Total': f"{stats1['Ratio But/Poss T']*100:.1f}%"},
                {'Indicateur': 'Taux Déchet', '1ère MT': f"{stats1['Taux Déchet 1']*100:.1f}%", '2ème MT': f"{stats1['Taux Déchet 2']*100:.1f}%", 'Total': f"{stats1['Taux Déchet T']*100:.1f}%"},
                {'Indicateur': 'Eff Défensive', '1ère MT': f"{stats1['Eff Def 1']*100:.1f}%", '2ème MT': f"{stats1['Eff Def 2']*100:.1f}%", 'Total': f"{stats1['Eff Def T']*100:.1f}%"},
                {'Indicateur': 'Eff Tir', '1ère MT': f"{stats1['Eff Tir 1']*100:.1f}%", '2ème MT': f"{stats1['Eff Tir 2']*100:.1f}%", 'Total': f"{stats1['Eff Tir T']*100:.1f}%"},
                {'Indicateur': 'Déchet Tech', '1ère MT': f"{stats1['Déchet 1']:.1f}", '2ème MT': f"{stats1['Déchet 2']:.1f}", 'Total': f"{stats1['Déchet T']:.1f}"},
                {'Indicateur': 'Nb INF', '1ère MT': f"{stats1['Nb INF 1']:.0f}", '2ème MT': f"{stats1['Nb INF 2']:.0f}", 'Total': f"{stats1['Nb INF T']:.0f}"},
                {'Indicateur': 'Écart INF', '1ère MT': f"{stats1['Ecart INF 1']:.0f}", '2ème MT': f"{stats1['Ecart INF 2']:.0f}", 'Total': f"{stats1['Ecart INF T']:.0f}"},
                {'Indicateur': 'Moy Écart INF', '1ère MT': f"{stats1['Moy Ecart INF 1']:.1f}", '2ème MT': f"{stats1['Moy Ecart INF 2']:.1f}", 'Total': f"{stats1['Moy Ecart INF T']:.1f}"},
                {'Indicateur': 'Nb SUP', '1ère MT': f"{stats1['Nb SUP 1']:.0f}", '2ème MT': f"{stats1['Nb SUP 2']:.0f}", 'Total': f"{stats1['Nb SUP T']:.0f}"},
                {'Indicateur': 'Écart SUP', '1ère MT': f"{stats1['Ecart SUP 1']:.0f}", '2ème MT': f"{stats1['Ecart SUP 2']:.0f}", 'Total': f"{stats1['Ecart SUP T']:.0f}"},
                {'Indicateur': 'Moy Écart SUP', '1ère MT': f"{stats1['Moy Ecart SUP 1']:.1f}", '2ème MT': f"{stats1['Moy Ecart SUP 2']:.1f}", 'Total': f"{stats1['Moy Ecart SUP T']:.1f}"},
                {'Indicateur': 'Moy DMA BHB', '1ère MT': f"{stats1['Moy DMA BHB 1']:.3f}", '2ème MT': f"{stats1['Moy DMA BHB 2']:.3f}", 'Total': f"{stats1['Moy DMA BHB T']:.3f}"},
                {'Indicateur': 'ET DMA BHB', '1ère MT': f"{stats1['ET DMA BHB 1']:.3f}", '2ème MT': f"{stats1['ET DMA BHB 2']:.3f}", 'Total': f"{stats1['ET DMA BHB T']:.3f}"},
                {'Indicateur': 'Moy DMA ADV', '1ère MT': f"{stats1['Moy DMA ADV 1']:.3f}", '2ème MT': f"{stats1['Moy DMA ADV 2']:.3f}", 'Total': f"{stats1['Moy DMA ADV T']:.3f}"},
                {'Indicateur': 'ET DMA ADV', '1ère MT': f"{stats1['ET DMA ADV 1']:.3f}", '2ème MT': f"{stats1['ET DMA ADV 2']:.3f}", 'Total': f"{stats1['ET DMA ADV T']:.3f}"},
                {'Indicateur': 'Rapport de Force', '1ère MT': f"{stats1['RdF 1']:.3f}", '2ème MT': f"{stats1['RdF 2']:.3f}", 'Total': f"{stats1['RdF T']:.3f}"},
            ]
            df_stats1 = pd.DataFrame(data1)
            # Appliquer la colorisation
            styled_df1 = df_stats1.style.apply(lambda x: [
                color_dechet(v) if x['Indicateur'] == 'Taux Déchet' else color_ratio(v) 
                for v in x
            ], subset=['1ère MT', '2ème MT', 'Total'], axis=1)
            st.dataframe(styled_df1, use_container_width=True, hide_index=True, height=700)
    
    with col_g2:
        st.markdown(f"#### {label2}")
        stats2 = calculate_general_stats(df, matches2)
        if stats2:
            data2 = [
                {'Indicateur': 'Score', '1ère MT': f"{stats2['Buts BHB 1']:.1f}-{stats2['Buts ADV 1']:.1f}", 
                 '2ème MT': f"{stats2['Buts BHB 2']:.1f}-{stats2['Buts ADV 2']:.1f}", 'Total': f"{stats2['Buts BHB T']:.1f}-{stats2['Buts ADV T']:.1f}"},
                {'Indicateur': 'Buts Pour', '1ère MT': f"{stats2['Buts BHB 1']:.1f}", '2ème MT': f"{stats2['Buts BHB 2']:.1f}", 'Total': f"{stats2['Buts BHB T']:.1f}"},
                {'Indicateur': 'Buts Contre', '1ère MT': f"{stats2['Buts ADV 1']:.1f}", '2ème MT': f"{stats2['Buts ADV 2']:.1f}", 'Total': f"{stats2['Buts ADV T']:.1f}"},
                {'Indicateur': 'Nb Possessions', '1ère MT': f"{stats2['Poss Total 1']:.1f}", '2ème MT': f"{stats2['Poss Total 2']:.1f}", 'Total': f"{stats2['Poss Total T']:.1f}"},
                {'Indicateur': 'Rythme', '1ère MT': f"{stats2.get('Rythme 1', 0):.2f}", '2ème MT': f"{stats2.get('Rythme 2', 0):.2f}", 'Total': f"{stats2.get('Rythme T', 0):.2f}"},
                {'Indicateur': 'Ratio But/Poss', '1ère MT': f"{stats2['Ratio But/Poss 1']*100:.1f}%", '2ème MT': f"{stats2['Ratio But/Poss 2']*100:.1f}%", 'Total': f"{stats2['Ratio But/Poss T']*100:.1f}%"},
                {'Indicateur': 'Taux Déchet', '1ère MT': f"{stats2['Taux Déchet 1']*100:.1f}%", '2ème MT': f"{stats2['Taux Déchet 2']*100:.1f}%", 'Total': f"{stats2['Taux Déchet T']*100:.1f}%"},
                {'Indicateur': 'Eff Défensive', '1ère MT': f"{stats2['Eff Def 1']*100:.1f}%", '2ème MT': f"{stats2['Eff Def 2']*100:.1f}%", 'Total': f"{stats2['Eff Def T']*100:.1f}%"},
                {'Indicateur': 'Eff Tir', '1ère MT': f"{stats2['Eff Tir 1']*100:.1f}%", '2ème MT': f"{stats2['Eff Tir 2']*100:.1f}%", 'Total': f"{stats2['Eff Tir T']*100:.1f}%"},
                {'Indicateur': 'Déchet Tech', '1ère MT': f"{stats2['Déchet 1']:.1f}", '2ème MT': f"{stats2['Déchet 2']:.1f}", 'Total': f"{stats2['Déchet T']:.1f}"},
                {'Indicateur': 'Nb INF', '1ère MT': f"{stats2['Nb INF 1']:.0f}", '2ème MT': f"{stats2['Nb INF 2']:.0f}", 'Total': f"{stats2['Nb INF T']:.0f}"},
                {'Indicateur': 'Écart INF', '1ère MT': f"{stats2['Ecart INF 1']:.0f}", '2ème MT': f"{stats2['Ecart INF 2']:.0f}", 'Total': f"{stats2['Ecart INF T']:.0f}"},
                {'Indicateur': 'Moy Écart INF', '1ère MT': f"{stats2['Moy Ecart INF 1']:.1f}", '2ème MT': f"{stats2['Moy Ecart INF 2']:.1f}", 'Total': f"{stats2['Moy Ecart INF T']:.1f}"},
                {'Indicateur': 'Nb SUP', '1ère MT': f"{stats2['Nb SUP 1']:.0f}", '2ème MT': f"{stats2['Nb SUP 2']:.0f}", 'Total': f"{stats2['Nb SUP T']:.0f}"},
                {'Indicateur': 'Écart SUP', '1ère MT': f"{stats2['Ecart SUP 1']:.0f}", '2ème MT': f"{stats2['Ecart SUP 2']:.0f}", 'Total': f"{stats2['Ecart SUP T']:.0f}"},
                {'Indicateur': 'Moy Écart SUP', '1ère MT': f"{stats2['Moy Ecart SUP 1']:.1f}", '2ème MT': f"{stats2['Moy Ecart SUP 2']:.1f}", 'Total': f"{stats2['Moy Ecart SUP T']:.1f}"},
                {'Indicateur': 'Moy DMA BHB', '1ère MT': f"{stats2['Moy DMA BHB 1']:.3f}", '2ème MT': f"{stats2['Moy DMA BHB 2']:.3f}", 'Total': f"{stats2['Moy DMA BHB T']:.3f}"},
                {'Indicateur': 'ET DMA BHB', '1ère MT': f"{stats2['ET DMA BHB 1']:.3f}", '2ème MT': f"{stats2['ET DMA BHB 2']:.3f}", 'Total': f"{stats2['ET DMA BHB T']:.3f}"},
                {'Indicateur': 'Moy DMA ADV', '1ère MT': f"{stats2['Moy DMA ADV 1']:.3f}", '2ème MT': f"{stats2['Moy DMA ADV 2']:.3f}", 'Total': f"{stats2['Moy DMA ADV T']:.3f}"},
                {'Indicateur': 'ET DMA ADV', '1ère MT': f"{stats2['ET DMA ADV 1']:.3f}", '2ème MT': f"{stats2['ET DMA ADV 2']:.3f}", 'Total': f"{stats2['ET DMA ADV T']:.3f}"},
                {'Indicateur': 'Rapport de Force', '1ère MT': f"{stats2['RdF 1']:.3f}", '2ème MT': f"{stats2['RdF 2']:.3f}", 'Total': f"{stats2['RdF T']:.3f}"},
            ]
            df_stats2 = pd.DataFrame(data2)
            # Appliquer la colorisation
            styled_df2 = df_stats2.style.apply(lambda x: [
                color_dechet(v) if x['Indicateur'] == 'Taux Déchet' else color_ratio(v) 
                for v in x
            ], subset=['1ère MT', '2ème MT', 'Total'], axis=1)
            st.dataframe(styled_df2, use_container_width=True, hide_index=True, height=700)

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
st.markdown("*BHB Analytics v4.3*")
