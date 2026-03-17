import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from linearmodels.panel import PanelOLS, PooledOLS
from linearmodels.iv import IV2SLS

BLUE   = '#2563EB'
ORANGE = '#EA580C'
GREEN  = '#16A34A'
GREY   = '#6B7280'
plt.rcParams.update({
    'figure.dpi': 130,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'font.family': 'sans-serif',
})

## Coefficient plot

def coef_plot(ax, params, ci_low, ci_high, labels, color=BLUE, title=''):
    y = np.arange(len(labels))
    ax.axvline(0, color=GREY, lw=0.8, ls='--')
    ax.errorbar(params, y,
                xerr=[params - ci_low, ci_high - params],
                fmt='o', color=color, ecolor=color,
                capsize=4, ms=6, lw=1.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_title(title)
    ax.set_xlabel('Coefficient estimate')

def extract_ci(result, var_names):
    """Pull params and 95% CI from a linearmodels result."""
    params  = result.params[var_names].values
    ci_low  = result.conf_int(level=0.95).loc[var_names, 'lower'].values
    ci_high = result.conf_int(level=0.95).loc[var_names, 'upper'].values
    return params, ci_low, ci_high


T = pd.read_csv('fixedeffect.csv')

T['debt']           = T['dlc'] + T['dltt']
T['profitability']  = T['oibdp'] / T['at']
T['tangibility']    = T['ppent'] / T['at']
T['bookleverage']   = T['debt'] / T['at']
T['marketleverage'] = T['debt'] / T['mkvalt']
T['lsales']         = np.log(T['sale'])
T['mktbook']        = T['mkvalt'] / T['at']

T = T[(T['bookleverage'] <= 1) & (T['marketleverage'] <= 1)].copy()
T.loc[T['sale'] <= 0, 'lsales'] = np.nan
T = T.dropna(subset=['bookleverage', 'marketleverage', 'lsales',
                     'mktbook', 'profitability', 'tangibility'])

print("=" * 60)
print("SUMMARY STATISTICS")
print("=" * 60)
print(T[['bookleverage', 'marketleverage', 'lsales',
         'mktbook', 'profitability', 'tangibility']].describe())

## Distribution of leverage measures - chart

fig, axes = plt.subplots(1, 2, figsize=(10, 4))
fig.suptitle('Chart 1 — Distribution of Leverage Measures', fontweight='bold')

for ax, col, color, label in zip(
        axes,
        ['bookleverage', 'marketleverage'],
        [BLUE, ORANGE],
        ['Book Leverage  (Debt / Assets)', 'Market Leverage  (Debt / Market Value)']):
    ax.hist(T[col], bins=60, color=color, alpha=0.75, edgecolor='white', linewidth=0.3)
    ax.axvline(T[col].mean(),   color='black', lw=1.2, ls='--',
               label=f'Mean = {T[col].mean():.3f}')
    ax.axvline(T[col].median(), color=GREY,    lw=1.2, ls=':',
               label=f'Median = {T[col].median():.3f}')
    ax.set_xlabel(label)
    ax.set_ylabel('Firm-year observations')
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('chart1_leverage_distributions.png', bbox_inches='tight')
plt.show()

T = T.set_index(['gvkey', 'fyear'])
X_vars         = ['lsales', 'mktbook', 'profitability', 'tangibility']
labels_pretty  = ['Log Sales', 'Mkt-to-Book', 'Profitability', 'Tangibility']

# Pooled OLS
print("\n" + "=" * 60)
print("POOLED OLS — Book Leverage")
print("=" * 60)
po_book = PooledOLS(T['bookleverage'],  T[X_vars].assign(const=1)
                    ).fit(cov_type='clustered', cluster_entity=True)
print(po_book.summary)

print("\n" + "=" * 60)
print("POOLED OLS — Market Leverage")
print("=" * 60)
po_mkt = PooledOLS(T['marketleverage'], T[X_vars].assign(const=1)
                   ).fit(cov_type='clustered', cluster_entity=True)
print(po_mkt.summary)

# Pooled OLS coefficient plots - chart

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
fig.suptitle('Chart 2 — Pooled OLS Coefficients (95% CI, clustered by firm)',
             fontweight='bold')

for ax, result, color, title in zip(
        axes,
        [po_book, po_mkt],
        [BLUE, ORANGE],
        ['Book Leverage', 'Market Leverage']):
    p, lo, hi = extract_ci(result, X_vars)
    coef_plot(ax, p, lo, hi, labels_pretty, color=color, title=title)

plt.tight_layout()
plt.savefig('chart2_pooled_ols_coefs.png', bbox_inches='tight')
plt.show()



# Fixed Effects
print("\n" + "=" * 60)
print("FIXED EFFECTS — Book Leverage")
print("=" * 60)
fe_book = PanelOLS(T['bookleverage'],  T[X_vars], entity_effects=True
                   ).fit(cov_type='clustered', cluster_entity=True)
print(fe_book.summary)

print("\n" + "=" * 60)
print("FIXED EFFECTS — Market Leverage")
print("=" * 60)
fe_mkt = PanelOLS(T['marketleverage'], T[X_vars], entity_effects=True
                  ).fit(cov_type='clustered', cluster_entity=True)
print(fe_mkt.summary)

# Pooled OLS vs FE chart - clearly there is like an omitted-var vias

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle('Chart 3 — Pooled OLS vs Fixed Effects: Coefficient Comparison\n'
             '(divergence = omitted-variable bias absorbed by firm FE)',
             fontweight='bold')

for ax, po, fe, title in zip(
        axes,
        [po_book, po_mkt],
        [fe_book, fe_mkt],
        ['Book Leverage', 'Market Leverage']):
    y     = np.arange(len(X_vars))
    width = 0.28

    p_po, lo_po, hi_po = extract_ci(po, X_vars)
    p_fe, lo_fe, hi_fe = extract_ci(fe, X_vars)

    ax.axvline(0, color=GREY, lw=0.8, ls='--')
    ax.errorbar(p_po, y + width,
                xerr=[p_po - lo_po, hi_po - p_po],
                fmt='s', color=BLUE, ecolor=BLUE,
                capsize=4, ms=6, lw=1.6, label='Pooled OLS')
    ax.errorbar(p_fe, y - width,
                xerr=[p_fe - lo_fe, hi_fe - p_fe],
                fmt='o', color=ORANGE, ecolor=ORANGE,
                capsize=4, ms=6, lw=1.6, label='Fixed Effects')
    ax.set_yticks(y)
    ax.set_yticklabels(labels_pretty)
    ax.set_title(title)
    ax.set_xlabel('Coefficient estimate')
    ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig('chart3_ols_vs_fe_comparison.png', bbox_inches='tight')
plt.show()

# FE model — fitted vs residuals chart 

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
fig.suptitle('Chart 4 — Fixed Effects: Fitted Values vs Residuals\n'
             '(heteroskedasticity / influential observations check)',
             fontweight='bold')

for ax, result, color, title in zip(
        axes,
        [fe_book, fe_mkt],
        [BLUE, ORANGE],
        ['Book Leverage', 'Market Leverage']):
    fitted = result.fitted_values.values.flatten()
    resid  = result.resids.values.flatten()

    rng  = np.random.default_rng(42)
    samp = rng.choice(len(fitted), size=min(5000, len(fitted)), replace=False)

    ax.scatter(fitted[samp], resid[samp],
               alpha=0.25, s=8, color=color, edgecolors='none')
    ax.axhline(0, color='black', lw=0.9, ls='--')
    ax.set_xlabel('Fitted values')
    ax.set_ylabel('Residuals')
    ax.set_title(title)

plt.tight_layout()
plt.savefig('chart4_fe_fitted_vs_residuals.png', bbox_inches='tight')
plt.show()


# 
# IV WITH FIXED EFFECTS 
# 

try:
    T2 = pd.read_csv('data_intensive_1y_HS4.csv')
except FileNotFoundError:
    print("\n[INFO] 'data_intensive_1y_HS4.csv' not found — skipping Part 2.")
    raise SystemExit

T2 = T2.sort_values(['pcf', 'post'])

def panel_first_diff(df, value_col, group_col, time_col):
    return (df.sort_values([group_col, time_col])
              .groupby(group_col)[value_col]
              .diff())

for var in ['lsaldotot', 'lpeso']:
    T2[f'D{var}'] = panel_first_diff(T2, var, 'pc', 'ruc')

idx    = T2['Dlpeso'].notna() & T2['Dlsaldotot'].notna()
T2_fe  = T2[idx].set_index(['pc', 'ruc'])

print("\n" + "=" * 60)
print("OLS with PC Fixed Effects (Table 5, col 1)")
print("=" * 60)
ols_fe = PanelOLS(T2_fe['Dlpeso'], T2_fe[['Dlsaldotot']], entity_effects=True
                  ).fit(cov_type='clustered', cluster_entity=True)
print(ols_fe.summary)

y_fs = T2_fe['Dlsaldotot']

print("\n" + "=" * 60); print("FIRST STAGE 1: fexposure_2006")
fs1 = PanelOLS(y_fs, T2_fe[['fexposure_2006']], entity_effects=True
               ).fit(cov_type='clustered', cluster_entity=True)
print(fs1.summary)

print("\n" + "=" * 60); print("FIRST STAGE 2: wexposure1_2006")
fs2 = PanelOLS(y_fs, T2_fe[['wexposure1_2006']], entity_effects=True
               ).fit(cov_type='clustered', cluster_entity=True)
print(fs2.summary)

print("\n" + "=" * 60); print("FIRST STAGE 3: wexposure1/2/3_2006")
fs3 = PanelOLS(y_fs,
               T2_fe[['wexposure1_2006', 'wexposure2_2006', 'wexposure3_2006']],
               entity_effects=True
               ).fit(cov_type='clustered', cluster_entity=True)
print(fs3.summary)

# First-stage scatter — instrument chart

def within_transform(series, group):
    return series - series.groupby(group).transform('mean')

pc_idx   = T2_fe.index.get_level_values('pc')
inst_dm  = within_transform(T2_fe['fexposure_2006'], pc_idx)
endog_dm = within_transform(T2_fe['Dlsaldotot'],     pc_idx)

rng  = np.random.default_rng(42)
samp = rng.choice(len(inst_dm), size=min(4000, len(inst_dm)), replace=False)

fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(inst_dm.values[samp], endog_dm.values[samp],
           alpha=0.20, s=8, color=BLUE, edgecolors='none')

m, b    = np.polyfit(inst_dm.values[samp], endog_dm.values[samp], 1)
x_line  = np.linspace(inst_dm.values[samp].min(), inst_dm.values[samp].max(), 200)
ax.plot(x_line, m * x_line + b, color=ORANGE, lw=2,
        label=f'Slope = {m:.4f}  (first-stage coef)')
ax.axhline(0, color=GREY, lw=0.7, ls='--')
ax.axvline(0, color=GREY, lw=0.7, ls='--')
ax.set_xlabel('fexposure_2006  (within-demeaned)')
ax.set_ylabel('Δlog(credit)  (within-demeaned)')
ax.set_title('Chart 5 — First Stage: Instrument Relevance\n'
             'Pre-crisis bank exposure (2006) → Change in credit supply',
             fontweight='bold')
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig('chart5_first_stage_scatter.png', bbox_inches='tight')
plt.show()

idx2   = (T2['post'] == 1) & T2['Dlpeso'].notna() & T2['Dlsaldotot'].notna()
T2_iv  = T2[idx2].set_index(['pc', 'ruc'])

def within_demean(df, cols):
    return df[cols] - df.groupby(level='pc')[cols].transform('mean')

T2_dm  = within_demean(T2_iv, ['Dlpeso', 'Dlsaldotot', 'fexposure_2006'])

print("\n" + "=" * 60)
print("IV / 2SLS with PC Fixed Effects")
print("Instrument: fexposure_2006  |  Endogenous: Dlsaldotot")
print("=" * 60)
iv_fe = IV2SLS(
    dependent   = T2_dm['Dlpeso'],
    exog        = None,
    endog       = T2_dm[['Dlsaldotot']],
    instruments = T2_dm[['fexposure_2006']]
).fit(cov_type='robust')
print(iv_fe.summary)

ols_post = PanelOLS(T2_iv['Dlpeso'], T2_iv[['Dlsaldotot']], entity_effects=True
                    ).fit(cov_type='clustered', cluster_entity=True)

# OLS vs IV endogeneity bias correction chart 

ols_coef = ols_post.params['Dlsaldotot']
ols_lo   = ols_post.conf_int().loc['Dlsaldotot', 'lower']
ols_hi   = ols_post.conf_int().loc['Dlsaldotot', 'upper']
iv_coef  = iv_fe.params['Dlsaldotot']
iv_lo    = iv_fe.conf_int().loc['Dlsaldotot', 'lower']
iv_hi    = iv_fe.conf_int().loc['Dlsaldotot', 'upper']

fig, ax = plt.subplots(figsize=(7, 3.5))
ax.axvline(0, color=GREY, lw=0.8, ls='--')

for i, (coef, lo, hi, color, label) in enumerate([
        (ols_coef, ols_lo, ols_hi, BLUE,   'OLS + FE'),
        (iv_coef,  iv_lo,  iv_hi,  ORANGE, 'IV (2SLS) + FE  [fexposure_2006]')]):
    ax.errorbar(coef, i,
                xerr=[[coef - lo], [hi - coef]],
                fmt='o', color=color, ecolor=color,
                capsize=6, ms=9, lw=2, label=label)
    ax.text(coef, i + 0.18, f'{coef:.4f}',
            ha='center', va='bottom', fontsize=9, color=color)

ax.set_yticks([0, 1])
ax.set_yticklabels(['OLS + FE', 'IV + FE'], fontsize=10)
ax.set_xlabel('Coefficient on Δlog(credit)')
ax.set_title('Chart 6 — OLS vs IV Estimate of Credit-Export Elasticity\n'
             '(gap = endogeneity bias corrected by instrument)',
             fontweight='bold')
ax.legend(fontsize=8, loc='lower right')
plt.tight_layout()
plt.savefig('chart6_ols_vs_iv.png', bbox_inches='tight')
plt.show()

print("\n✓ All 6 charts saved to the working directory.")
