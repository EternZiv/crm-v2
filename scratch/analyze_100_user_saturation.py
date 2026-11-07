import pandas as pd
import numpy as np

for tier, name in [(50, 'tx_stage4_50users'), (100, 'tx_stage5_100users')]:
    hist_path = f'load_tests/reports/performance_optimization/{name}_stats_history.csv'
    stats_path = f'load_tests/reports/performance_optimization/{name}_stats.csv'
    telem_path = f'load_tests/reports/performance_optimization/tx_stage{4 if tier==50 else 5}_telemetry.csv'
    
    df_hist = pd.read_csv(hist_path)
    df_stats = pd.read_csv(stats_path)
    df_telem = pd.read_csv(telem_path)
    
    print('==============================')
    print(f'  ANALYSIS FOR {tier} USERS ({name})')
    print('==============================')
    
    # 1. Concurrency ramp and sustain
    t_start = df_hist['Timestamp'].min()
    t_end = df_hist['Timestamp'].max()
    dur = t_end - t_start
    full_concurrency_df = df_hist[df_hist['User Count'] == tier]
    ramp_time = full_concurrency_df['Timestamp'].min() - t_start if len(full_concurrency_df) else 0
    sustain_time = t_end - full_concurrency_df['Timestamp'].min() if len(full_concurrency_df) else 0
    print(f'Start Timestamp: {t_start}, End Timestamp: {t_end}, Total History Duration: {dur}s ({dur/60:.1f}m)')
    print(f'Ramp-up duration to {tier} users: {ramp_time}s')
    print(f'Sustained duration at full {tier} users: {sustain_time}s ({sustain_time/60:.1f}m)')
    
    # 2. RPS over time
    col_rps = 'Requests/s'
    print(f'RPS: min={df_hist[col_rps].min():.2f}, mean={df_hist[col_rps].mean():.2f}, p50={df_hist[col_rps].median():.2f}, max={df_hist[col_rps].max():.2f}')
    
    # 3. Telemetry stats
    print(f'Telemetry rows: {len(df_telem)}')
    print(f'Host CPU: min={df_telem["cpu_percent"].min():.1f}%, mean={df_telem["cpu_percent"].mean():.1f}%, p95={df_telem["cpu_percent"].quantile(0.95):.1f}%, max={df_telem["cpu_percent"].max():.1f}%')
    print(f'Host Mem: min={df_telem["memory_percent"].min():.1f}%, mean={df_telem["memory_percent"].mean():.1f}%')
    print(f'DB Total Conns: min={df_telem["db_total_conns"].min()}, mean={df_telem["db_total_conns"].mean():.1f}, max={df_telem["db_total_conns"].max()}')
    print(f'DB Active Conns: min={df_telem["db_active_conns"].min()}, max={df_telem["db_active_conns"].max()}')
    print(f'DB Idle in TX: {df_telem["db_idle_tx"].max()}')
    print(f'DB Slow Queries: {df_telem["db_slow_queries"].max()}')

    print('\nEndpoint breakdown (Top 5 by request count):')
    agg_row = df_stats[df_stats['Name'] == 'Aggregated']
    print('Total requests:', df_stats['Request Count'].sum() - agg_row['Request Count'].values[0] if len(agg_row) else df_stats['Request Count'].sum())
    
    # Sort endpoints by request count descending
    non_agg = df_stats[df_stats['Name'] != 'Aggregated'].copy()
    non_agg = non_agg.sort_values(by='Request Count', ascending=False)
    for idx, r in non_agg.head(8).iterrows():
        print(f"  {r['Name']}: count={r['Request Count']}, p50={r['50%']}ms, p95={r['95%']}ms, avg={r['Average Response Time']:.1f}ms")
    print('\n')

