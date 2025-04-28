import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
from matplotlib.table import Table


# Constants
base_font_size = 12

# Load real data
daccs_df = pd.read_excel("./data/Master Standardisation DACCS.xlsx", sheet_name="Standardization Results", skiprows=1)
daccs_df.columns = daccs_df.columns.str.strip()

studies_to_keep_daccs = ["Young et al. 2023", "Sievert et al. 2024", "Fasihi et al. 2019", "Keith et al. 2018", "Pett-Ridge et al. 2024"]
daccs_df = daccs_df[daccs_df['Reference'].isin(studies_to_keep_daccs)]
daccs_df.loc[daccs_df['Year of Assumptions in Study'] < 2025, "Term"] = "Short Term"
daccs_df.loc[daccs_df['Year of Assumptions in Study'] >= 2025, "Term"] = "Long Term"

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
    df["Term"] = np.where(df["Year of Cost"] < 2030, "Short Term", "Long Term")

synfuels_df = pd.concat([synfuels_df_med, synfuels_df_high, synfuels_df_low])

# Filter Long Term
daccs_df_2050 = daccs_df[daccs_df["Term"] == "Long Term"].rename(columns={"Fully Harmonized NET REMOVED COST (incl T&S": "Fully Harmonized"})
daccs_df_2050["Tech"] = "DACCS"
synfuels_df_2050 = synfuels_df[synfuels_df["Term"] == "Long Term"]
synfuels_df_2050["Tech"] = "SAF"

combined_data = pd.concat([daccs_df_2050, synfuels_df_2050])

manual_study_order = [
    "Keith et al. 2018", "Fasihi et al. 2019", "Young et al. 2023", "Sievert et al. 2024", "Pett-Ridge et al. 2024",
    "Marchese et.al. ", "Sherwin", "Martin et. al.", "Moretti et al.", "Gray et al.", "Peacock et. al.", "Schmidt et. al.", "Seymour et al.", "Brazzola et al. "
]
study_to_y = {study: idx for idx, study in enumerate(manual_study_order)}

# Table data
top_table_header = pd.DataFrame([
    ["T & S", "Heat", "Electricity", "Capital", "CO₂", "Jet Fuel", "Source"],
    ["[$/tCO₂]", "[$/MWh]", "[$/MWh]", "[%]", "[$/tCO₂]", "[$/l]", ""]
])

top_table_studies = pd.DataFrame([
    ["n/a", "11", "30-60", "5.6-11.7", "", "", "[1]"],
    ["n/a", "22-28", "61", "7", "", "", "[2]"],
    ["12.4", "11-410", "11-300", "7.5-12.5", "", "", "[3]"],
    ["5-12", "20.2", "39", "7", "", "", "[4]"],
    ["10", "10", "60-309", "12.5", "", "", "[5]"],
    ["", "", "41-210", "7.5", "", "", "[6]"],
    ["", "", "19", "5", "100", "0.55", "[7]"],
    ["", "", "30-48", "8", "90", "0.28-0.52", "[8]"],
    ["", "", "50", "5.2", "237", "n/a", "[9]"],
    ["", "", "40", "6", "160", "n/a", "[10]"],
    ["", "", "38-118", "8", "200", "n/a", "[11]"],
    ["", "", "52", "8", "151", "n/a", "[12]"],
    ["", "", "30", "5", "199", "0.8", "[13]"],
    ["", "", "20", "7", "88", "X", "[14]"]
])


bottom_table_header = pd.DataFrame([
    ["T & S", "Heat", "Electricity", "Capital", "CO₂", "Jet Fuel", "Technology"],
    ["[$/tCO₂]", "[$/MWh]", "[$/MWh]", "[%]", "[$/tCO₂]", "[$/l]", ""]
])
bottom_table_data = pd.DataFrame([
    ["25", "21", "29", "7", "", "", "DACCS"],
    ["", "", "29", "7", "250-500", "0.8", "SAF"]
])

# Drawing and plotting
def draw_table(ax, dataframe, font_size=9, row_height=0.22, grey_background=False, bold_header=False, header_lines=False):
    ax.axis('off')
    table = Table(ax, bbox=[0, 0, 1, 1])
    n_rows, n_cols = dataframe.shape
    widths = [1.6 / n_cols] * n_cols
    for i in range(n_rows):
        for j in range(n_cols):
            cell = table.add_cell(i, j, widths[j], row_height, text=str(dataframe.iat[i, j]), loc='center')
            cell.set_fontsize(font_size)
            if header_lines:

                if i == n_rows-1:
                    cell.set_edgecolor('black')
                    cell.set_linewidth(1)
                    cell.visible_edges = 'B'
                else:
                    cell.set_linewidth(0)
            else:
                cell.set_linewidth(0)
            if grey_background:
                cell.set_facecolor('white')
            else:
                cell.set_facecolor('white')
            if bold_header:
                cell.set_text_props(weight='bold')
    table.auto_set_font_size(False)
    ax.add_table(table)

# Plot
fig = plt.figure(figsize=(12, 7))
gs = gridspec.GridSpec(6, 2, width_ratios=[4,3], height_ratios=[0.1,0.5,4,0.3,0.5,1.5], hspace=0.2)
gs.update(wspace=0.13)  # <<< ADD THIS LINE

# Top titles
ax0 = plt.subplot(gs[0,0])
ax0.axis('off')
ax0.text(0.5,0.5,"Study assumptions and standardized parameters",ha='center',va='center',fontsize=11, fontweight='bold')
ax1 = plt.subplot(gs[0,1])
ax1.axis('off')
ax1.text(0.5,0.5,"Harmonized long-term cost projections",ha='center',va='center',fontsize=11, fontweight='bold')

# Top tables
ax2 = plt.subplot(gs[1,0])
draw_table(ax2, top_table_header, grey_background=False, bold_header=True, header_lines=True)
ax3 = plt.subplot(gs[2,0])
draw_table(ax3, top_table_studies, grey_background=True)

# Dot plot
ax4 = plt.subplot(gs[2,1])

# 1. Draw the lightgrey horizontal lines first
for y in study_to_y.values():
    ax4.axhline(y=y, color='lightgrey', linestyle='-', linewidth=0.7, zorder=1)

# 2. Now scatter the dots *on top*
for _, row in combined_data.iterrows():
    ref = row['Reference']
    if ref in study_to_y:
        ax4.scatter(row['Fully Harmonized'], study_to_y[ref],
                    color='#9ED9E5' if row['Tech']=='DACCS' else '#FFB133',
                    zorder=2,   # Give dots a higher zorder
                    s=20)

# 3. Other settings
ax4.set_yticks(list(study_to_y.values()))
ax4.set_yticklabels(labels=())
#ax4.set_yticklabels([f'[{i+1}]' for i in study_to_y.values()], fontsize=9)
ax4.tick_params(axis='y', left=True, width=0.7, color='lightgrey', length=40)
ax4.tick_params(axis='x', bottom=False)
ax4.set_axisbelow(True)
ax4.invert_yaxis()
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.spines['bottom'].set_visible(False)
ax4.spines['left'].set_visible(False)
ax4.grid(True, axis='x', linestyle='-', alpha=0.5)
ax4.set_xlabel("Abatement cost ($/tCO₂)", fontsize=10)


# Bottom tables
ax5 = plt.subplot(gs[4,0])
draw_table(ax5, bottom_table_header, grey_background=False, bold_header=True, header_lines=True)
ax6 = plt.subplot(gs[5,0])
draw_table(ax6, bottom_table_data, grey_background=True)

# Violin plot
ax7 = plt.subplot(gs[5,1])

# 1. Plot the violinplot FIRST
sns.violinplot(
    data=combined_data,
    x='Fully Harmonized',
    y='Tech',
    hue='Tech',
    palette=['#9ED9E5', '#FFB133'],
    ax=ax7,
    cut=0,
    inner='box',
    zorder=2,
    inner_kws=dict(linewidth=0.5, box_width=5, color='.5')
)

# Remove the outer lines of the violins
for violin in ax7.findobj(matplotlib.collections.PolyCollection):
    violin.set_edgecolor('none')

# 2. Now bring back the grid for both x and y
ax7.grid(True, axis='both', linestyle='-', alpha=0.5, zorder=1)
ax7.set_axisbelow(True)

# 3. Style
ax7.set_xlabel("Abatement cost ($/tCO₂)", fontsize=10)
ax7.set_ylabel("")
ax7.set_yticks([0, 1])
ax7.set_yticklabels(labels=())
ax7.tick_params(axis='y', left=True, width=0.7, color='lightgrey', length=40)
ax7.tick_params(axis='x', bottom=False)

if ax7.get_legend() is not None:
    ax7.get_legend().remove()

ax7.spines['top'].set_visible(False)
ax7.spines['right'].set_visible(False)
ax7.spines['bottom'].set_visible(False)
ax7.spines['left'].set_visible(False)



plt.tight_layout()
plt.show()