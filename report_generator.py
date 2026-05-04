"""
Complete Enhanced Report Generator with:
1. Correlation heatmap (displayed in HTML via base64)
2. Yearly correlation tables (5 targets × 9 predictors, with mean)
3. K-Means and HDBSCAN individual graphs (5 graphs each - one per target)
4. Linear Regression individual graphs (5 graphs - one per target)
5. Simple clean table styling (Academic/LaTeX style)
6. Clear data normalization documentation
7. All images embedded in HTML (no local server needed)
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Set global font to Times New Roman for academic look
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['axes.unicode_minus'] = False
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import spearmanr
import base64
from io import BytesIO
from config.db_config import PSQL_CONNECTION_STRING
from utils.logger import get_logger

logger = get_logger(__name__)

class EnhancedReportGenerator:
    """Generate comprehensive enhanced HTML report with all visualizations"""
    
    def __init__(self, ml_results_path='reports/ml_results.json'):
        self.ml_results_path = ml_results_path
        
        try:
            with open(ml_results_path, 'r') as f:
                self.results = json.load(f)
            logger.info(f"Loaded ML results from {ml_results_path}")
        except Exception as e:
            logger.warning(f"Could not load ML results: {e}")
            self.results = {}
        
        # Load ML config for scaling settings
        try:
            with open('config/ml_config.json', 'r') as f:
                self.ml_config = json.load(f)
        except:
            self.ml_config = {}
        
        # Connect to database
        self.engine = create_engine(PSQL_CONNECTION_STRING)
        self.df_timeseries = None
        self.df_clustering = None
        self.load_data()
        
        # Column mappings
        self.target_cols = ['apm_sd', 'apm_smp', 'apm_sm', 'apk_pt', 'rata_rata_lama_sekolah']
        self.predictor_cols = [
            'ekonomi_miskin', 'ekonomi_upah_rata_rata',
            'kesehatan_ahh_perempuan', 'kesehatan_unmet_layanan',
            'ketenagakerjaan_formal', 'ketenagakerjaan_informal',
            'teknologi_telepon_seluler', 'teknologi_internet'
        ]
        
        self.target_names = {
            'apm_sd': 'APMSD',
            'apm_smp': 'APMSMP',
            'apm_sm': 'APMSM',
            'apk_pt': 'APKPT',
            'rata_rata_lama_sekolah': 'RLS'
        }
        
        self.predictor_short_names = {
            'ekonomi_miskin': 'PPM (%)',
            'ekonomi_upah_rata_rata': 'URPJ',
            'kesehatan_ahh_perempuan': 'AHH',
            'kesehatan_unmet_layanan': 'PUPK (%)',
            'ketenagakerjaan_formal': 'PTKF (%)',
            'ketenagakerjaan_informal': 'PTKIN (%)',
            'teknologi_telepon_seluler': 'PMTS (%)',
            'teknologi_internet': 'PAIN (%)',
            # Add mean versions for clustering tables
            'ekonomi_miskin_mean': 'PPM (%) Mean',
            'ekonomi_miskin_trend_pct': 'PPM Trend (%)',
            'ekonomi_upah_mean': 'URPJ Mean',
            'ekonomi_upah_trend_pct': 'URPJ Trend (%)',
            'kesehatan_ahh_perempuan_mean': 'AHH Mean',
            'kesehatan_ahh_perempuan_trend_pct': 'AHH Trend (%)',
            'kesehatan_unmet_mean': 'PUPK (%) Mean',
            'kesehatan_unmet_trend_pct': 'PUPK Trend (%)',
            'ketenagakerjaan_formal_mean': 'PTKF (%) Mean',
            'ketenagakerjaan_formal_trend_pct': 'PTKF Trend (%)',
            'ketenagakerjaan_informal_mean': 'PTKIN (%) Mean',
            'ketenagakerjaan_informal_trend_pct': 'PTKIN Trend (%)',
            'teknologi_telepon_mean': 'PMTS (%) Mean',
            'teknologi_telepon_trend_pct': 'PMTS Trend (%)',
            'teknologi_internet_mean': 'PAIN (%) Mean',
            'teknologi_internet_trend_pct': 'PAIN Trend (%)'
        }
        
        # Clustering columns
        self.predictor_cols_clustering = [
            'ekonomi_miskin_mean', 'ekonomi_miskin_trend_pct',
            'ekonomi_upah_mean', 'ekonomi_upah_trend_pct',
            'kesehatan_ahh_perempuan_mean', 'kesehatan_ahh_perempuan_trend_pct',
            'kesehatan_unmet_mean', 'kesehatan_unmet_trend_pct',
            'ketenagakerjaan_formal_mean', 'ketenagakerjaan_formal_trend_pct',
            'ketenagakerjaan_informal_mean', 'ketenagakerjaan_informal_trend_pct',
            'teknologi_telepon_mean', 'teknologi_telepon_trend_pct',
            'teknologi_internet_mean', 'teknologi_internet_trend_pct'
        ]
        
        self.target_cols_clustering = [
            'apm_sd_mean', 'apm_smp_mean', 'apm_sm_mean', 'apk_pt_mean', 'rata_rata_lama_sekolah_mean'
        ]
    
    def load_data(self):
        """Load both timeseries and clustering data"""
        try:
            # Time series data for correlations and prediction
            query_ts = "SELECT * FROM dm.timeseries_province_year_ml WHERE provinsi != 'INDONESIA' ORDER BY provinsi, tahun"
            self.df_timeseries = pd.read_sql(query_ts, self.engine)
            
            # Clustering data for visualizations
            query_cl = "SELECT * FROM dm.agg_province_ml WHERE provinsi != 'INDONESIA' ORDER BY provinsi"
            self.df_clustering = pd.read_sql(query_cl, self.engine)
            
            logger.info(f"Loaded data: TS={self.df_timeseries.shape}, CL={self.df_clustering.shape}")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")

    def fig_to_base64(self, fig):
        """Convert matplotlib figure to base64-encoded PNG"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    
    def generate_correlation_heatmap(self):
        """Generate Spearman correlation heatmap"""
        logger.info("Generating correlation heatmap...")
        if self.df_timeseries is None: return None
        try:
            data = self.df_timeseries[self.predictor_cols + self.target_cols].dropna()
            if len(data) == 0: return None
            scaler = StandardScaler()
            data_normalized = pd.DataFrame(scaler.fit_transform(data), columns=data.columns, index=data.index)
            corr_matrix = data_normalized.corr(method='spearman')
            fig, ax = plt.subplots(figsize=(14, 10))
            sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r', center=0, vmin=-1, vmax=1, ax=ax, square=True)
            ax.set_title('Matriks Korelasi Spearman', fontsize=13, fontweight='bold', pad=20)
            plt.tight_layout()
            return self.fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating correlation heatmap: {e}")
            return None
    
    def generate_yearly_correlation_tables(self):
        """Generate correlation tables by year"""
        if self.df_timeseries is None: return {}
        tables_html = {}
        try:
            years = sorted(self.df_timeseries['tahun'].unique())
            for target in self.target_cols:
                rows = []
                for pred in self.predictor_cols:
                    row_data = {'Variable': self.predictor_short_names[pred]}
                    corrs = []
                    for year in years:
                        y_data = self.df_timeseries[self.df_timeseries['tahun'] == year][[pred, target]].dropna()
                        if len(y_data) > 2:
                            c, _ = spearmanr(y_data[pred], y_data[target])
                            row_data[str(year)] = round(c, 3); corrs.append(c)
                        else: row_data[str(year)] = 'N/A'
                    row_data['mean'] = round(np.mean(corrs), 3) if corrs else 'N/A'
                    rows.append(row_data)
                # Sort rows by mean correlation (highest to lowest)
                rows.sort(key=lambda x: x['mean'] if isinstance(x['mean'], (int, float)) else -999, reverse=True)
                
                df_corr = pd.DataFrame(rows)
                html = '<table><thead><tr><th>Variabel</th>'
                for y in years: html += f'<th>{y}</th>'
                html += '<th>mean</th></tr></thead><tbody>'
                for _, row in df_corr.iterrows():
                    html += '<tr>'
                    for col in df_corr.columns:
                        val = row[col]
                        html += f'<td>{val:.3f}</td>' if isinstance(val, float) else f'<td>{val}</td>'
                    html += '</tr>'
                html += '</tbody></table>'
                tables_html[target] = html
            return tables_html
        except Exception as e: return {}
    
    def generate_trend_correlation_table(self):
        """Generate correlation table specifically for trend features"""
        if self.df_clustering is None: return ""
        try:
            # Predictor trend columns
            trend_preds = [c for c in self.predictor_cols_clustering if '_trend_pct' in c]
            
            rows = []
            for pred in trend_preds:
                row_data = {'Variable': self.predictor_short_names.get(pred, pred)}
                for target_col in self.target_cols_clustering:
                    target_name = self.target_names.get(target_col.replace('_mean', ''), target_col)
                    y_data = self.df_clustering[[pred, target_col]].dropna()
                    if len(y_data) > 2:
                        c, _ = spearmanr(y_data[pred], y_data[target_col])
                        row_data[target_name] = round(c, 3)
                    else: row_data[target_name] = 'N/A'
                rows.append(row_data)
            
            # Sort by absolute max correlation if possible
            df_corr = pd.DataFrame(rows)
            
            html = '<table><thead><tr><th>Variabel Trend</th>'
            for target_col in self.target_cols_clustering:
                target_name = self.target_names.get(target_col.replace('_mean', ''), target_col)
                html += f'<th>{target_name}</th>'
            html += '</tr></thead><tbody>'
            
            for _, row in df_corr.iterrows():
                html += '<tr>'
                for col in df_corr.columns:
                    val = row[col]
                    html += f'<td>{val:.3f}</td>' if isinstance(val, float) else f'<td>{val}</td>'
                html += '</tr>'
            html += '</tbody></table>'
            return html
        except Exception as e: 
            logger.error(f"Error generating trend correlation table: {e}")
            return ""

    def generate_hdbscan_metrics_table(self, target=None):
        """Simple metrics table"""
        if target: h = self.results.get('per_target_clustering', {}).get(target, {}).get('hdbscan', {})
        else: h = self.results.get('hdbscan', {})
        if not h: return "<p>Data tidak tersedia.</p>"
        html = '<table><thead><tr><th>Metrik</th><th>Nilai</th></tr></thead><tbody>'
        html += f'<tr><td>Jumlah Kluster</td><td>{h.get("n_clusters", "N/A")}</td></tr>'
        html += f'<tr><td>Rasio Noise</td><td>{h.get("noise_ratio", 0):.4f}</td></tr>'
        html += f'<tr><td>Silhouette Score</td><td>{h.get("silhouette", h.get("silhouette_score", 0)):.4f}</td></tr>'
        html += '</tbody></table>'
        return html

    def generate_kmeans_metrics_table(self, target=None):
        """Simple metrics table with Inertia and Silhouette"""
        if target: k = self.results.get('per_target_clustering', {}).get(target, {}).get('kmeans', {})
        else: k = self.results.get('kmeans', {})
        if not k: return "<p>Data tidak tersedia.</p>"
        
        opt_k = k.get("optimal_k", k.get("n_clusters", "N/A"))
        inertia = k.get("inertia")
        if inertia is None and "inertias" in k and "k_range" in k:
            try:
                idx = k["k_range"].index(opt_k)
                inertia = k["inertias"][idx]
            except: inertia = "N/A"
            
        html = '<table><thead><tr><th>Metrik</th><th>Nilai</th></tr></thead><tbody>'
        html += f'<tr><td>Nilai K</td><td>{opt_k}</td></tr>'
        html += f'<tr><td>Inersia</td><td>{f"{inertia:.2f}" if isinstance(inertia, (int, float)) else inertia}</td></tr>'
        html += f'<tr><td>Silhouette Score</td><td>{k.get("final_silhouette", k.get("silhouette", 0)):.4f}</td></tr>'
        html += '</tbody></table>'
        return html

    def generate_cluster_statistics_table(self, method='kmeans', target=None):
        """Comprehensive cluster statistics table"""
        if target: stats = self.results.get('per_target_clustering', {}).get(target, {}).get(method, {}).get('stats', {})
        else: stats = self.results.get(method, {}).get('cluster_statistics', {})
        if not stats: return f'<p>Data tidak tersedia.</p>'
        
        keys = sorted([k for k in stats.keys() if k.startswith('cluster_')], key=lambda x: int(x.split('_')[1]))
        if 'noise' in stats: keys.append('noise')
            
        html = '<table><thead><tr><th>Indikator</th>'
        for k in keys: html += f'<th>{k.replace("cluster_", "Kluster ").replace("noise", "Noise")}</th>'
        html += '</tr></thead><tbody>'
        html += '<tr><td>Jumlah Anggota</td>'
        for k in keys: html += f'<td>{stats[k]["n_members"]}</td>'
        html += '</tr>'
        # Get selected features for this target to highlight
        selected_features = self.results.get('per_target_clustering', {}).get(target, {}).get('selected_features', [])
        
        for p in self.predictor_cols_clustering:
            display_name = self.predictor_short_names.get(p, p)
            if p in selected_features:
                display_name = f'<span style="color: green;">{display_name}</span>'
                
            html += f'<tr><td>{display_name}</td>'
            for k in keys: html += f'<td>{stats[k]["means"].get(p, 0):.2f}</td>'
            html += '</tr>'
        
        # Target Pendidikan section
        html += '<tr><td><strong>Target Pendidikan</strong></td>' + ('<td></td>' * len(keys)) + '</tr>'
        for t_col in self.target_cols_clustering:
            t_name_clean = t_col.replace('_mean', '')
            # If per-target analysis, ONLY show the current target indicator
            if target and t_name_clean != target: continue
            
            html += f'<tr><td>{self.target_names.get(t_name_clean, t_name_clean)}</td>'
            for k in keys: html += f'<td>{stats[k]["means"].get(t_col, 0):.2f}</td>'
            html += '</tr>'
            
        html += '</tbody></table>'
        return html

    def generate_rf_feature_importance_tables(self):
        tables = {}
        for target in self.target_cols:
            rf = self.results.get('random_forest', {}).get(target, {})
            if not rf: continue
            fi = sorted(rf.get('feature_importance', {}).items(), key=lambda x: x[1], reverse=True)
            html = '<table><thead><tr><th>Indikator Sosial</th><th>FI</th></tr></thead><tbody>'
            for f, v in fi: html += f'<tr><td>{self.predictor_short_names.get(f, f)}</td><td>{v:.4f}</td></tr>'
            html += f'<tr><td><strong>R² Disesuaikan</strong></td><td>{rf.get("adj_r2", 0):.4f}</td></tr>'
            html += f'<tr><td><strong>MAE</strong></td><td>{rf.get("mae", 0):.4f}</td></tr></tbody></table>'
            tables[target] = html
        return tables

    def generate_lr_slope_table(self):
        tables = {}
        for target in self.target_cols:
            lr = self.results.get('linear_regression', {}).get(target, {})
            if not lr: continue
            p_vals = lr.get('p_values', {})
            # Prepare data with significance flag for sorting
            data_to_sort = []
            for f, c in lr.get('coefficients', {}).items():
                p = p_vals.get(f, 1.0)
                data_to_sort.append({
                    'f': f,
                    'c': c,
                    'p': p,
                    'sig_val': 1 if p < 0.05 else 0
                })
            
            # Sort: Significance (1 first), then coefficient value (descending)
            sorted_items = sorted(data_to_sort, key=lambda x: (x['sig_val'], x['c']), reverse=True)
            
            html = '<table><thead><tr><th>Indikator Sosial</th><th>Koefisien</th><th>P-Value</th><th>Sig*</th></tr></thead><tbody>'
            for item in sorted_items:
                f, c, p = item['f'], item['c'], item['p']
                sig = 'Ya' if p < 0.05 else 'Tidak'
                html += f'<tr><td>{self.predictor_short_names.get(f, f)}</td><td>{c:.6f}</td><td>{p:.6f}</td><td>{sig}</td></tr>'
            html += f'<tr><td colspan="4"><strong>R² Disesuaikan: {lr.get("adj_r2", 0):.4f} | MAE: {lr.get("mae", 0):.4f}</strong></td></tr></tbody></table>'
            tables[target] = html
        return tables

    def generate_clustering_visualizations(self, method='kmeans'):
        """Generate individual clustering graphs for each target"""
        graphs = {}
        results = self.results.get('per_target_clustering', {})
        if self.df_clustering is None: return {}
        
        for target in self.target_cols:
            t_data = results.get(target, {}).get(method, {})
            if not t_data: continue
            
            t_col = f"{target}_mean"
            df = self.df_clustering[self.predictor_cols_clustering + [t_col]].dropna()
            labels = np.array(t_data.get('labels', []))
            
            if len(df) != len(labels):
                logger.warning(f"Length mismatch for {target} ({method}): df={len(df)}, labels={len(labels)}")
                continue
                
            X = StandardScaler().fit_transform(df[self.predictor_cols_clustering])
            pca = PCA(n_components=2); X_pca = pca.fit_transform(X)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            unique = sorted(set(labels))
            colors = plt.cm.Set3(np.linspace(0, 1, len(unique)))
            for i, l in enumerate(unique):
                mask = labels == l
                ax.scatter(X_pca[mask, 0], X_pca[mask, 1], c=[colors[i]] if l != -1 else ['gray'], 
                           label=f'Kluster {l+1}' if l != -1 else 'Noise', s=120, alpha=0.7, edgecolors='black')
            
            if method == 'kmeans':
                # Centroids calculation in PCA space
                for l in unique:
                    if l == -1: continue
                    centroid_pca = X_pca[labels == l].mean(axis=0)
                    ax.scatter(centroid_pca[0], centroid_pca[1], c='red', marker='X', s=300, edgecolors='darkred')
                ax.scatter([], [], c='red', marker='X', s=100, label='Sentroid')

            ax.set_title(f'Visualisasi Klustering {method.upper()}: {self.target_names[target]}')
            ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})')
            ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})')
            ax.legend(loc='best'); ax.grid(False)
            graphs[target] = self.fig_to_base64(fig)
        return graphs

    def generate_linear_regression_graphs(self):
        graphs = {}
        for target in self.target_cols:
            df = self.df_timeseries[self.predictor_cols + [target]].dropna()
            if len(df) < 5: continue
            
            X = df[self.predictor_cols]
            y = df[target].values
            
            # Use same scaling as ML pipeline if configured
            pred_cfg = self.ml_config.get('prediction', {})
            if pred_cfg.get('use_scaling', False):
                scaler_type = pred_cfg.get('scaler_type', 'robust')
                scaler = RobustScaler() if scaler_type == 'robust' else StandardScaler()
                X = scaler.fit_transform(X)
            
            lr = LinearRegression().fit(X, y); y_p = lr.predict(X)
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.scatter(y, y_p, alpha=0.6, s=80, color='blue')
            ax.plot([y.min(), y.max()], [y.min(), y.max()], 'r--', lw=1)
            ax.set_title(f'Regresi Linear: {self.target_names[target]}')
            ax.set_xlabel('Aktual'); ax.set_ylabel('Prediksi')
            graphs[target] = self.fig_to_base64(fig)
        return graphs

    def generate_html(self, output_file='reports/ml_analysis_report_enhanced.html'):
        """Generate final HTML with booktabs style"""
        logger.info("Building HTML report with booktabs style...")
        
        heatmap = self.generate_correlation_heatmap()
        yearly_corr = self.generate_yearly_correlation_tables()
        km_graphs = self.generate_clustering_visualizations('kmeans')
        hdb_graphs = self.generate_clustering_visualizations('hdbscan')
        lr_graphs = self.generate_linear_regression_graphs()
        lr_tables = self.generate_lr_slope_table()
        rf_tables = self.generate_rf_feature_importance_tables()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Laporan Analisis ML</title>
    <style>
        body {{ font-family: "Times New Roman", Times, serif; max-width: 1000px; margin: 40px auto; color: black; line-height: 1.4; background: white; }}
        h1 {{ text-align: center; text-transform: uppercase; margin-bottom: 30px; padding-bottom: 10px; border-bottom: 2px solid black; }}
        h2 {{ margin-top: 40px; border-bottom: 1px solid black; padding-bottom: 5px; }}
        h3 {{ margin-top: 25px; }}
        .section {{ margin-bottom: 40px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; border-top: 2px solid black; border-bottom: 2px solid black; font-size: 13px; }}
        th, td {{ padding: 6px 4px; text-align: center; border: none; }}
        thead {{ border-bottom: 1px solid black; }}
        th {{ font-weight: bold; }}
        .graph-container {{ text-align: center; margin: 15px 0; }}
        .graph-container img {{ max-width: 85%; height: auto; }}
        .tables-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .timestamp {{ margin-top: 50px; font-size: 11px; text-align: right; font-style: italic; border-top: 1px solid #ccc; padding-top: 10px; }}
        .note {{ border: 1px solid black; padding: 12px; background: #fff; margin: 15px 0; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>Laporan Analisis Machine Learning</h1>

    <div class="note"><strong>Metodologi:</strong> Seluruh analisis dilakukan pada data yang dinormalisasi (StandardScaler). Setiap klustering dilakukan secara independen menggunakan fitur terpilih (dengan korelasi &gt; ±0.5, ditandai dengan <span style="color: green;">teks hijau</span> pada tabel statistik kluster) dan 1 indikator pendidikan terkait.</div>

    <h2>1. Heatmap Korelasi Spearman</h2>
    <div class="section"><div class="graph-container"><img src="data:image/png;base64,{heatmap}"></div></div>

    <h2>2. Korelasi Tahunan (Tingkat Level)</h2>
    <div class="section">
        <div class="tables-grid">
        {''.join([f'<div><h3>Target: {self.target_names[t]}</h3>{yearly_corr[t]}</div>' for t in self.target_cols if t in yearly_corr])}
        </div>
    </div>

    <h2>3. Korelasi Fitur Trend (Laju Perubahan)</h2>
    <div class="section">
        {self.generate_trend_correlation_table()}
    </div>

    <h2>4. Klustering Independen per Target Pendidikan</h2>
    <div class="section">
        {''.join([f'''
        <div style="border-top: 1px solid black; margin-top: 30px; padding-top: 15px;">
            <h3>Target Indikator: {self.target_names[t]}</h3>
            <div class="tables-grid">
                <div><h4>K-Means Metrics</h4>{self.generate_kmeans_metrics_table(t)}</div>
                <div><h4>HDBSCAN Metrics</h4>{self.generate_hdbscan_metrics_table(t)}</div>
            </div>
            <div class="tables-grid">
                <div class="graph-container"><h4>Visualisasi K-Means</h4><img src="data:image/png;base64,{km_graphs.get(t, '')}"></div>
                <div class="graph-container"><h4>Visualisasi HDBSCAN</h4><img src="data:image/png;base64,{hdb_graphs.get(t, '')}"></div>
            </div>
            <h4>Statistik K-Means ({self.target_names[t]})</h4>{self.generate_cluster_statistics_table('kmeans', t)}
            <h4>Statistik HDBSCAN ({self.target_names[t]})</h4>{self.generate_cluster_statistics_table('hdbscan', t)}
        </div>
        ''' for t in self.target_cols])}
    </div>

    <h2>5. Analisis Prediksi dan Regresi</h2>
    <div class="section">
        {''.join([f'''
        <div style="margin-top: 25px;">
            <h3>Target: {self.target_names[t]}</h3>
            <div class="tables-grid">
                <div><h4>Random Forest Importance</h4>{rf_tables.get(t, '')}</div>
                <div><h4>Regresi Linear Coefficients</h4>{lr_tables.get(t, '')}</div>
            </div>
            <div class="graph-container"><h4>Plot Prediksi Regresi Linear</h4><img src="data:image/png;base64,{lr_graphs.get(t, '')}"></div>
        </div>
        ''' for t in self.target_cols])}
    </div>

    <div class="timestamp">Laporan Dibuat: {timestamp}</div>
</body>
</html>
"""
        with open(output_file, 'w', encoding='utf-8') as f: f.write(html)
        return output_file

if __name__ == "__main__":
    EnhancedReportGenerator().generate_html()