#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="BHB Analytics", layout="wide")

st.markdown("""<style>
.stDataFrame thead th:first-child, .stDataFrame tbody td:first-child {
    position: sticky; left: 0; background: white; z-index: 2; border-right: 2px solid #ddd;
}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=0)
def load_data(filepath):
    try:
        return pd.read_excel(filepath)
    except Exception as e:
        st.error(f"Erreur : {e}")
        return None

def aggregate(df, matches):
    if df is None or len(matches) == 0:
        return None
    filtered = df[df['Match'].isin(matches)]
    if len(filtered) == 0:
        return None
    return filtered.groupby('Minute').agg({'DMA BHB': 'mean', 'DMA ADV': 'mean', 'Rapport de force': 'mean'}).reset_index()

def calculate_trend(x, y):
    z = np.polyfit(x, y, 3)
    return np.poly1d(z)(x)

def calculate_general_stats(df, matches):
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
        period_sorted = period_data.sort_index()
        inf_mask = (period_sorted['INF'] == 'INF')
        nb_inf = float((inf_mask.astype(int).diff().fillna(0) == 1).sum())
        inf_possessions = period_sorted[inf_mask]
        ecart_inf = float(len(inf_possessions[(inf_possessions['Equipe'] == 'BHB') & (inf_possessions['Issue'] == 1)]) - len(inf_possessions[(inf_possessions['Equipe'] == 'ADV') & (inf_possessions['Issue'] == 1)])) if len(inf_possessions) > 0 else 0.0
        sup_mask = (period_sorted['SUP'] == 'SUP')
        nb_sup = float((sup_mask.astype(int).diff().fillna(0) == 1).sum())
        sup_possessions = period_sorted[sup_mask]
        ecart_sup = float(len(sup_possessions[(sup_possessions['Equipe'] == 'BHB') & (sup_possessions['Issue'] == 1)]) - len(sup_possessions[(sup_possessions['Equipe'] == 'ADV') & (sup_possessions['Issue'] == 1)])) if len(sup_possessions) > 0 else 0.0
        return {'Buts BHB': buts_bhb, 'Buts ADV': buts_adv, 'Poss BHB': poss_bhb, 'Poss ADV': poss_adv, 'Poss Total': poss_total, 'Déchet': dechet, 'Tirs Effectifs': tirs_effectifs, 'Moy DMA BHB': moy_dma_bhb, 'ET DMA BHB': et_dma_bhb, 'Moy DMA ADV': moy_dma_adv, 'ET DMA ADV': et_dma_adv, 'RdF': moy_dma_bhb - moy_dma_adv, 'Nb INF': nb_inf, 'Ecart INF': ecart_inf, 'Nb SUP': nb_sup, 'Ecart SUP': ecart_sup}

    all_matches = filtered_df['Match'].unique()
    rows_1, rows_2, rows_T = [], [], []
    for match in all_matches:
        match_data = filtered_df[filtered_df['Match'] == match]
        s1, s2, sT = _period_stats(match_data[match_data['Minute'] <= 30]), _period_stats(match_data[match_data['Minute'] > 30]), _period_stats(match_data)
        if s1: rows_1.append(s1)
        if s2: rows_2.append(s2)
        if sT: rows_T.append(sT)

    out = {}
    for suffix, rows in [('1', rows_1), ('2', rows_2), ('T', rows_T)]:
        if len(rows) == 0:
            continue
        for k in ['Buts BHB', 'Buts ADV', 'Poss BHB', 'Poss ADV', 'Poss Total', 'Déchet', 'Moy DMA BHB', 'ET DMA BHB', 'Moy DMA ADV', 'ET DMA ADV', 'RdF', 'Nb INF', 'Ecart INF', 'Nb SUP', 'Ecart SUP']:
            out[f'{k} {suffix}'] = float(np.mean([r.get(k, 0.0) for r in rows]))
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
        duree = 30 if suffix != 'T' else 60
        out[f'Rythme {suffix}'] = sum(r.get('Poss Total', 0.0) for r in rows) / (len(rows) * duree) if len(rows) > 0 else 0.0
    return out

def calculate_shooter_stats(df, matches):
    if df is None or len(matches) == 0:
        return None
    player_mapping = {2: "NAUDIN Paul", 3: "NAUDIN Théo", 25: "FAVERIN Léan", 7: "PLISSONNIER Jean", 8: "PANIC Milan", 9: "MINANA Lilian", 10: "GREGULSKI Vincent", 12: "STEPHAN Corentin", 13: "THELCIDE Axel", 15: "COSNIER Lubin", 16: "MAI François", 19: "GOSTOMSKI Sasha", 21: "CHAZALON Marius", 24: "MINY Gabin", 4: "HERMAND Mathieu", 33: "NAUDIN Hugo", 78: "LAURENCE Samuel", 92: "PHAROSE Kylian"}
    filtered_df = df[df['Match'].isin(matches)].copy()
    if len(filtered_df) == 0:
        return None
    bhb_data = filtered_df[filtered_df['Equipe'] == 'BHB'].copy()
    if len(bhb_data) == 0:
        return None
    bhb_data = bhb_data[(bhb_data['Tireur'].notna()) & (bhb_data['Tireur'] != 0) & (bhb_data['Tireur'] != '')].copy()
    if len(bhb_data) == 0:
        return None
    bhb_data['MT'] = (bhb_data['Minute'] > 30).astype(int) + 1
    bhb_data['Tireur'] = bhb_data['Tireur'].astype(int)
    grouped = bhb_data.groupby(['Tireur', 'MT']).agg({'Issue': ['count', 'sum']}).reset_index()
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
    return result.sort_values('Buts Total', ascending=False).reset_index(drop=True)

def chart(d1, d2, l1, l2, metric, title, show_trend=False):
    fig = go.Figure()
    if d1 is not None:
        fig.add_trace(go.Scatter(x=d1['Minute'], y=d1[metric], name=l1, line=dict(color='#667eea', width=4)))
        if show_trend and len(d1) > 3:
            fig.add_trace(go.Scatter(x=d1['Minute'], y=calculate_trend(d1['Minute'].values, d1[metric].values), name=f'{l1} - Tendance', line=dict(color='#667eea', width=2, dash='dot'), opacity=0.6))
    if d2 is not None:
        fig.add_trace(go.Scatter(x=d2['Minute'], y=d2[metric], name=l2, line=dict(color='#f5576c', width=4, dash='dash')))
        if show_trend and len(d2) > 3:
            fig.add_trace(go.Scatter(x=d2['Minute'], y=calculate_trend(d2['Minute'].values, d2[metric].values), name=f'{l2} - Tendance', line=dict(color='#f5576c', width=2, dash='dot'), opacity=0.6))
    if 'Rapport' in metric:
        fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, opacity=0.5)
    fig.update_layout(title=title, height=600, hovermode='x unified', plot_bgcolor='white', font=dict(family='Inter'), xaxis=dict(title="Minute", gridcolor='rgba(0,0,0,0.1)'), yaxis=dict(title=metric, gridcolor='rgba(0,0,0,0.1)'), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
    return fig

st.title("BHB Analytics")

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
        matches1 = st.multiselect("Matchs", sorted(df['Match'].unique()), default=[sorted(df['Match'].unique())[0]], key="m1")
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
        matches2 = st.multiselect("Matchs", sorted(df['Match'].unique()), default=[sorted(df['Match'].unique())[1]] if len(df['Match'].unique()) > 1 else [], key="m2")
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
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA BHB', 'DMA BHB'), width=None)
with t2:
    st.plotly_chart(chart(d1, d2, label1, label2, 'DMA ADV', 'DMA ADV'), width=None)
with t3:
    show_trend = st.checkbox("Afficher tendances", value=True)
    st.plotly_chart(chart(d1, d2, label1, label2, 'Rapport de force', 'Rapport de Force', show_trend), width=None)

with t4:
    st.markdown("### 📋 Statistiques Générales")
    
    def format_stats(stats):
        if not stats:
            return None
        data = [
            {'Indicateur': 'Score', '1ère MT': f"{stats['Buts BHB 1']:.1f}-{stats['Buts ADV 1']:.1f}", '2ème MT': f"{stats['Buts BHB 2']:.1f}-{stats['Buts ADV 2']:.1f}", 'Total': f"{stats['Buts BHB T']:.1f}-{stats['Buts ADV T']:.1f}"},
            {'Indicateur': 'Buts Pour', '1ère MT': f"{stats['Buts BHB 1']:.1f}", '2ème MT': f"{stats['Buts BHB 2']:.1f}", 'Total': f"{stats['Buts BHB T']:.1f}"},
            {'Indicateur': 'Buts Contre', '1ère MT': f"{stats['Buts ADV 1']:.1f}", '2ème MT': f"{stats['Buts ADV 2']:.1f}", 'Total': f"{stats['Buts ADV T']:.1f}"},
            {'Indicateur': 'Nb Possessions', '1ère MT': f"{stats['Poss Total 1']:.1f}", '2ème MT': f"{stats['Poss Total 2']:.1f}", 'Total': f"{stats['Poss Total T']:.1f}"},
            {'Indicateur': 'Rythme', '1ère MT': f"{stats.get('Rythme 1', 0):.2f}", '2ème MT': f"{stats.get('Rythme 2', 0):.2f}", 'Total': f"{stats.get('Rythme T', 0):.2f}"},
            {'Indicateur': 'Ratio But/Poss', '1ère MT': f"{stats['Ratio But/Poss 1']*100:.1f}%", '2ème MT': f"{stats['Ratio But/Poss 2']*100:.1f}%", 'Total': f"{stats['Ratio But/Poss T']*100:.1f}%"},
            {'Indicateur': 'Taux Déchet', '1ère MT': f"{stats['Taux Déchet 1']*100:.1f}%", '2ème MT': f"{stats['Taux Déchet 2']*100:.1f}%", 'Total': f"{stats['Taux Déchet T']*100:.1f}%"},
            {'Indicateur': 'Eff Défensive', '1ère MT': f"{stats['Eff Def 1']*100:.1f}%", '2ème MT': f"{stats['Eff Def 2']*100:.1f}%", 'Total': f"{stats['Eff Def T']*100:.1f}%"},
            {'Indicateur': 'Eff Tir', '1ère MT': f"{stats['Eff Tir 1']*100:.1f}%", '2ème MT': f"{stats['Eff Tir 2']*100:.1f}%", 'Total': f"{stats['Eff Tir T']*100:.1f}%"},
            {'Indicateur': 'Déchet Tech', '1ère MT': f"{stats['Déchet 1']:.1f}", '2ème MT': f"{stats['Déchet 2']:.1f}", 'Total': f"{stats['Déchet T']:.1f}"},
            {'Indicateur': 'Nb INF', '1ère MT': f"{stats['Nb INF 1']:.0f}", '2ème MT': f"{stats['Nb INF 2']:.0f}", 'Total': f"{stats['Nb INF T']:.0f}"},
            {'Indicateur': 'Écart INF', '1ère MT': f"{stats['Ecart INF 1']:.0f}", '2ème MT': f"{stats['Ecart INF 2']:.0f}", 'Total': f"{stats['Ecart INF T']:.0f}"},
            {'Indicateur': 'Moy Écart INF', '1ère MT': f"{stats['Moy Ecart INF 1']:.1f}", '2ème MT': f"{stats['Moy Ecart INF 2']:.1f}", 'Total': f"{stats['Moy Ecart INF T']:.1f}"},
            {'Indicateur': 'Nb SUP', '1ère MT': f"{stats['Nb SUP 1']:.0f}", '2ème MT': f"{stats['Nb SUP 2']:.0f}", 'Total': f"{stats['Nb SUP T']:.0f}"},
            {'Indicateur': 'Écart SUP', '1ère MT': f"{stats['Ecart SUP 1']:.0f}", '2ème MT': f"{stats['Ecart SUP 2']:.0f}", 'Total': f"{stats['Ecart SUP T']:.0f}"},
            {'Indicateur': 'Moy Écart SUP', '1ère MT': f"{stats['Moy Ecart SUP 1']:.1f}", '2ème MT': f"{stats['Moy Ecart SUP 2']:.1f}", 'Total': f"{stats['Moy Ecart SUP T']:.1f}"},
            {'Indicateur': 'Moy DMA BHB', '1ère MT': f"{stats['Moy DMA BHB 1']:.3f}", '2ème MT': f"{stats['Moy DMA BHB 2']:.3f}", 'Total': f"{stats['Moy DMA BHB T']:.3f}"},
            {'Indicateur': 'ET DMA BHB', '1ère MT': f"{stats['ET DMA BHB 1']:.3f}", '2ème MT': f"{stats['ET DMA BHB 2']:.3f}", 'Total': f"{stats['ET DMA BHB T']:.3f}"},
            {'Indicateur': 'Moy DMA ADV', '1ère MT': f"{stats['Moy DMA ADV 1']:.3f}", '2ème MT': f"{stats['Moy DMA ADV 2']:.3f}", 'Total': f"{stats['Moy DMA ADV T']:.3f}"},
            {'Indicateur': 'ET DMA ADV', '1ère MT': f"{stats['ET DMA ADV 1']:.3f}", '2ème MT': f"{stats['ET DMA ADV 2']:.3f}", 'Total': f"{stats['ET DMA ADV T']:.3f}"},
            {'Indicateur': 'Rapport de Force', '1ère MT': f"{stats['RdF 1']:.3f}", '2ème MT': f"{stats['RdF 2']:.3f}", 'Total': f"{stats['RdF T']:.3f}"},
        ]
        return pd.DataFrame(data)
    
    def color_cell(val):
        if not isinstance(val, str) or '%' not in val:
            return ''
        pct = float(val.replace('%', ''))
        if pct < 20:
            return 'background-color: #ccffcc'
        elif pct == 20:
            return 'background-color: #ffe6cc'
        elif pct < 50:
            return 'background-color: #ffcccc'
        elif pct == 50:
            return 'background-color: #ffe6cc'
        else:
            return 'background-color: #ccffcc'
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown(f"#### {label1}")
        df1 = format_stats(calculate_general_stats(df, matches1))
        if df1 is not None:
            # Coloriser uniquement Taux Déchet
            styled = df1.copy()
            for col in ['1ère MT', '2ème MT', 'Total']:
                mask_dechet = df1['Indicateur'] == 'Taux Déchet'
                mask_ratio = df1['Indicateur'].isin(['Ratio But/Poss', 'Eff Défensive', 'Eff Tir'])
                # Utiliser HTML pour les couleurs
                def apply_color(row):
                    val = row[col]
                    ind = row['Indicateur']
                    if not isinstance(val, str) or '%' not in val:
                        return val
                    pct = float(val.replace('%', ''))
                    if ind == 'Taux Déchet':
                        if pct < 20:
                            color = '#ccffcc'
                        elif pct == 20:
                            color = '#ffe6cc'
                        else:
                            color = '#ffcccc'
                    elif ind in ['Ratio But/Poss', 'Eff Défensive', 'Eff Tir']:
                        if pct < 50:
                            color = '#ffcccc'
                        elif pct == 50:
                            color = '#ffe6cc'
                        else:
                            color = '#ccffcc'
                    else:
                        return val
                    return f'<div style="background-color:{color};padding:5px">{val}</div>'
                styled[col] = df1.apply(apply_color, axis=1)
            st.markdown(styled.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    with col_g2:
        st.markdown(f"#### {label2}")
        df2 = format_stats(calculate_general_stats(df, matches2))
        if df2 is not None:
            styled = df2.copy()
            for col in ['1ère MT', '2ème MT', 'Total']:
                def apply_color(row):
                    val = row[col]
                    ind = row['Indicateur']
                    if not isinstance(val, str) or '%' not in val:
                        return val
                    pct = float(val.replace('%', ''))
                    if ind == 'Taux Déchet':
                        color = '#ccffcc' if pct < 20 else ('#ffe6cc' if pct == 20 else '#ffcccc')
                    elif ind in ['Ratio But/Poss', 'Eff Défensive', 'Eff Tir']:
                        color = '#ffcccc' if pct < 50 else ('#ffe6cc' if pct == 50 else '#ccffcc')
                    else:
                        return val
                    return f'<div style="background-color:{color};padding:5px">{val}</div>'
                styled[col] = df2.apply(apply_color, axis=1)
            st.markdown(styled.to_html(escape=False, index=False), unsafe_allow_html=True)

with t5:
    st.markdown("### 🎯 Buteurs")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f"#### {label1}")
        shooters1 = calculate_shooter_stats(df, matches1)
        if shooters1 is not None and len(shooters1) > 0:
            st.dataframe(shooters1.style.format({'Eff 1': '{:.1%}', 'Eff 2': '{:.1%}', 'Eff Total': '{:.1%}'}), width=None, hide_index=True, height=600)
    with col_s2:
        st.markdown(f"#### {label2}")
        shooters2 = calculate_shooter_stats(df, matches2)
        if shooters2 is not None and len(shooters2) > 0:
            st.dataframe(shooters2.style.format({'Eff 1': '{:.1%}', 'Eff 2': '{:.1%}', 'Eff Total': '{:.1%}'}), width=None, hide_index=True, height=600)

st.markdown("---")
st.markdown("*BHB Analytics v4.5*")
