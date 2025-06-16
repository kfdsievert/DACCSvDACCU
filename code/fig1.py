import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.table import Table

# Constants
base_font_size = 12

# Load real data
daccs_df = pd.read_excel("./data/Master Standardisation DACCS.xlsx", sheet_name="Standardization Results", skiprows=1)
daccs_df.columns = daccs_df.columns.str.strip()

studies_to_keep_daccs = ["Young et al. 2023", "Sievert et al. 2024", "Fasihi et al. 2019", "Keith et al. 2018", "Pett-Ridge et al. 2024"]
daccs_df = daccs_df[daccs_df['Reference'].isin(studies_to_keep_daccs)]
daccs_df.loc[daccs_df['Year of Assumptions in Study'] < 2025, "Term"] = "Short Term"
daccs_df.loc[daccs_df['Year of Assumptions in Study'] == 2050, "Term"] = "Long Term"

synfuels_df_med = pd.read_excel("./data/Master Standardisation_SAF_Default.xlsx", sheet_name="Standardization Results")
synfuels_df_high = pd.read_excel("./data/Master Standardisation_SAF_Default.xlsx", sheet_name="High CO2")
synfuels_df_low = pd.read_excel("./data/Master Standardisation_SAF_Default.xlsx", sheet_name="Low CO2")

for df in [synfuels_df_med, synfuels_df_high, synfuels_df_low]:
    df.columns = df.columns.str.strip()

studies_to_keep_synfuels = [
    "Brazzola et al. ", "Gray et al.", "Marchese et.al. ", "Martin et. al.",
    "Moretti et al.", "Peacock et. al.", "Schmidt et. al.", "Seymour et al.", "Sherwin"
]
synfuels_df_med = synfuels_df_med[synfuels_df_med['Reference'].isin(studies_to_keep_synfuels)]
synfuels_df_high = synfuels_df_high[synfuels_df_high['Reference'].isin(studies_to_keep_synfuels)]
synfuels_df_low = synfuels_df_low[synfuels_df_low['Reference'].isin(studies_to_keep_synfuels)]

for df in [synfuels_df_med, synfuels_df_high, synfuels_df_low]:
    df["Year of Cost"] = df["Year of Cost"].astype(int)
    df["Term"] = np.where(df["Year of Cost"] <= 2025, "Short Term", "Long Term")

synfuels_df = pd.concat([synfuels_df_med, synfuels_df_high, synfuels_df_low])

# Filter Long Term
daccs_df_2050 = daccs_df[daccs_df["Term"] == "Long Term"].rename(columns={"Fully Harmonized NET REMOVED COST (incl T&S": "Fully Harmonized"})
daccs_df_2050["Tech"] = "DACCS"
daccs_df_2050 = daccs_df_2050.drop_duplicates(subset=["Fully Harmonized"])
synfuels_df_2050 = synfuels_df[synfuels_df["Term"] == "Long Term"]
synfuels_df_2050 = synfuels_df_2050.drop_duplicates(subset=["Fully Harmonized"])
synfuels_df_2050["Tech"] = "SAF"

combined_data = pd.concat([daccs_df_2050, synfuels_df_2050])

manual_study_order = [
    "Keith et al. 2018", "Fasihi et al. 2019", "Young et al. 2023", "Sievert et al. 2024", "Pett-Ridge et al. 2024",
    "Marchese et.al. ", "Sherwin", "Martin et. al.", "Moretti et al.", "Gray et al.", "Peacock et. al.", "Schmidt et. al.", "Seymour et al.", "Brazzola et al. "
]
study_to_y = {study: idx for idx, study in enumerate(manual_study_order)}

# === Violin Plot ===
fig_violin, ax_violin = plt.subplots(figsize=(5, 1.5))

sns.violinplot(
    data=combined_data,
    x='Fully Harmonized',
    y='Tech',
    hue='Tech',
    palette=['#40C6D1', '#EA971D'],
    ax=ax_violin,
    cut=0,
    inner='box',
    zorder=2,
    inner_kws=dict(linewidth=0.5, box_width=5, color='.3')
)

for violin in ax_violin.findobj(matplotlib.collections.PolyCollection):
    violin.set_edgecolor('none')

ax_violin.grid(True, axis='both', linestyle='-', alpha=0.5, zorder=1)
ax_violin.set_axisbelow(True)
ax_violin.set_xlabel("Abatement cost ($/tCO₂)", fontsize=10)
ax_violin.set_ylabel("")
ax_violin.set_yticks([0, 1])
ax_violin.set_yticklabels([])
ax_violin.tick_params(axis='y', left=True, width=0.7, color='lightgrey', length=40)
ax_violin.tick_params(axis='x', bottom=False)

if ax_violin.get_legend() is not None:
    ax_violin.get_legend().remove()

for side in ['top', 'right', 'bottom', 'left']:
    ax_violin.spines[side].set_visible(False)

plt.tight_layout()
fig_violin.savefig("violin_plot.png", dpi=300)
plt.close(fig_violin)

# === Dot Plot ===
fig_dot, ax_dot = plt.subplots(figsize=(5, 4.5))

for y in study_to_y.values():
    ax_dot.axhline(y=y, color='lightgrey', linestyle='-', linewidth=0.7, zorder=1)

for _, row in combined_data.iterrows():
    ref = row['Reference']
    if ref in study_to_y:
        ax_dot.scatter(row['Fully Harmonized'], study_to_y[ref],
                       color='#40C6D1' if row['Tech'] == 'DACCS' else '#EA971D',
                       zorder=2,
                       s=20)

ax_dot.set_yticks(list(study_to_y.values()))
ax_dot.set_yticklabels([])
ax_dot.tick_params(axis='y', left=True, width=0.7, color='lightgrey', length=40)
ax_dot.tick_params(axis='x', bottom=False)
ax_dot.set_axisbelow(True)
ax_dot.invert_yaxis()
for side in ['top', 'right', 'bottom', 'left']:
    ax_dot.spines[side].set_visible(False)

ax_dot.grid(True, axis='x', linestyle='-', alpha=0.5)
ax_dot.set_xlabel("Abatement cost ($/tCO₂)", fontsize=10)

plt.tight_layout()
fig_dot.savefig("dot_plot.png", dpi=300)
plt.close(fig_dot)
