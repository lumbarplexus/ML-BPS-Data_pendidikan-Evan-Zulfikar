#!/usr/bin/env python3
"""Quick test of aggregated tables"""

from etl.aggregator import aggregate_for_clustering, aggregate_for_timeseries

print('='*80)
print('TABLE 1: K-MEANS/HDBSCAN CLUSTERING')
print('='*80)
df_clust = aggregate_for_clustering()
print(f'Shape: {df_clust.shape} (35 provinces × 35 columns)')
print(f'Columns: {list(df_clust.columns)[:8]}...\n')
print('First 5 provinces:')
print(df_clust[['provinsi', 'ekonomi_miskin_mean', 'ekonomi_miskin_trend_pct', 'apm_sd_mean']].head())

print('\n' + '='*80)
print('TABLE 2: SPEARMAN/LR/RF TIME SERIES')
print('='*80)
df_ts = aggregate_for_timeseries()
print(f'Shape: {df_ts.shape} ({len(df_ts)} province-year records × {len(df_ts.columns)} columns)')
print(f'Columns: {list(df_ts.columns)[:10]}...\n')
print(f'Years: {sorted(df_ts["tahun"].unique())}')
print(f'Provinces: {df_ts["provinsi"].nunique()}')
print('\nFirst 5 records:')
print(df_ts[['provinsi', 'tahun', 'ekonomi_miskin', 'apm_sd']].head())

print('\n' + '='*80)
print('DATA QUALITY CHECK')
print('='*80)
print(f'Table 1 NULL values: {df_clust.isnull().sum().sum()} total')
print(f'Table 2 NULL values: {df_ts.isnull().sum().sum()} total')
print(f'  Missing by column:')
for col in df_ts.columns:
    null_count = df_ts[col].isnull().sum()
    if null_count > 0:
        print(f'    - {col}: {null_count} NULLs')
