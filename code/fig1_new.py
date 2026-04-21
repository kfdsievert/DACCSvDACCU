import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle

plt.rcParams['font.family'] = 'Trebuchet MS'


# ------------------------------
# Load and preprocess data
# ------------------------------
daccs_df = pd.read_excel(
    "./data/Master Standardisation DACCS.xlsx",
    sheet_name="Standardization Results",
    skiprows=1,
)
daccs_df.columns = daccs_df.columns.str.strip()

studies_to_keep_daccs = [
    "Young et al. 2023",
    "Sievert et al. 2024",
    "Fasihi et al. 2019",
    "Keith et al. 2018",
    "Pett-Ridge et al. 2024",
]
daccs_df = daccs_df[daccs_df["Reference"].isin(studies_to_keep_daccs)]
daccs_df.loc[daccs_df["Year of Assumptions in Study"] < 2025, "Term"] = "Short Term"
daccs_df.loc[daccs_df["Year of Assumptions in Study"] == 2050, "Term"] = "Long Term"

daccs_df = daccs_df.rename(
    columns={"Fully Harmonized NET REMOVED COST (incl T&S": "Fully Harmonized"}
)
daccs_df["Tech"] = "DACCS"

synfuels_df_med = pd.read_excel(
    "./data/Master Standardisation_SAF_Default.xlsx", sheet_name="Standardization Results"
)
synfuels_df_high = pd.read_excel(
    "./data/Master Standardisation_SAF_Default.xlsx", sheet_name="High CO2"
)
synfuels_df_low = pd.read_excel(
    "./data/Master Standardisation_SAF_Default.xlsx", sheet_name="Low CO2"
)

for df in [synfuels_df_med, synfuels_df_high, synfuels_df_low]:
    df.columns = df.columns.str.strip()

studies_to_keep_synfuels = [
    "Brazzola et al. ",
    "Gray et al.",
    "Marchese et.al. ",
    "Martin et. al.",
    "Moretti et al.",
    "Peacock et. al.",
    "Schmidt et. al.",
    "Seymour et al.",
    "Sherwin",
]

synfuels_df_med = synfuels_df_med[synfuels_df_med["Reference"].isin(studies_to_keep_synfuels)]
synfuels_df_high = synfuels_df_high[synfuels_df_high["Reference"].isin(studies_to_keep_synfuels)]
synfuels_df_low = synfuels_df_low[synfuels_df_low["Reference"].isin(studies_to_keep_synfuels)]

for df in [synfuels_df_med, synfuels_df_high, synfuels_df_low]:
    df["Year of Cost"] = pd.to_numeric(df["Year of Cost"], errors="coerce")
    df["Term"] = np.where(df["Year of Cost"] <= 2025, "Short Term", "Long Term")

synfuels_df = pd.concat([synfuels_df_med, synfuels_df_high, synfuels_df_low], ignore_index=True)
synfuels_df["Tech"] = "Synfuels"

# Long-term rows for charting
plot_data = pd.concat(
    [
        daccs_df[daccs_df["Term"] == "Long Term"],
        synfuels_df[synfuels_df["Term"] == "Long Term"],
    ],
    ignore_index=True,
)
plot_data["Fully Harmonized"] = pd.to_numeric(plot_data["Fully Harmonized"], errors="coerce")
plot_data = plot_data.dropna(subset=["Fully Harmonized"])

manual_study_order = [
    "Keith et al. 2018",
    "Fasihi et al. 2019",
    "Young et al. 2023",
    "Sievert et al. 2024",
    "Pett-Ridge et al. 2024",
    "Marchese et.al. ",
    "Sherwin",
    "Martin et. al.",
    "Moretti et al.",
    "Gray et al.",
    "Peacock et. al.",
    "Schmidt et. al.",
    "Seymour et al.",
    "Brazzola et al. ",
]
study_to_y = {study: idx for idx, study in enumerate(manual_study_order)}

# ------------------------------
# Synthetic table data (manually editable)
# ------------------------------
table_columns = [
    ("cost_of_capital", "Cost of\nCapital\n(%)"),
    ("electricity_cost", "Electricity\n cost\n(USD/MWh)"),
    ("heat_cost", "Heat Cost\n(USD/MWh)"),
    ("jet_fuel_cost", "Jet Fuel Cost\n(USD/l)"),
    ("co2_cost", "CO2 cost\n(USD/tCO2)"),
]

study_numbers_daccs = [32, 33, 34, 35, 36]
study_numbers_synfuels = [17, 18, 19, 20, 21, 22, 23, 24, 25]
study_numbers = study_numbers_daccs + study_numbers_synfuels

# Filled from screenshot. Edit any values manually as needed.
synthetic_table_data = {
    "Study": study_numbers,
    "cost_of_capital": [
        "5.6-11.7", "7", "7.5-12.5", "7", "12.5",
        "7.5", "5", "8", "5.2", "6", "8", "8", "5", "7",
    ],
    "electricity_cost": [
        "30-60", "61", "11-300", "39", "60-309",
        "41-210", "19", "30-48", "50", "40", "38-118", "52", "30", "24",
    ],
    "heat_cost": [
        "11", "22-28", "11-410", "20.2", "10",
        "", "", "", "", "", "", "", "", "",
    ],
    "jet_fuel_cost": [
        "", "", "", "", "",
        "n/a", "0.55", "0.28-0.52", "0.34-0.6", "0.76", "1.16", "n/a", "0.5", "0.82",
    ],
    "co2_cost": [
        "", "", "", "", "",
        "endogenous", "100", "90", "237", "160", "200", "151", "199", "200",
    ],
}

summary_df = pd.DataFrame(synthetic_table_data)

# ------------------------------
# Figure layout (table left, violin+dot right)
# ------------------------------
fig = plt.figure(figsize=(12.6, 5.4))
grid = fig.add_gridspec(
    nrows=2,
    ncols=2,
    width_ratios=[1.8, 1.0],
    height_ratios=[0.95, 4.05],
    wspace=0.06,
    hspace=0.08,
)

ax_table = fig.add_subplot(grid[:, 0])
ax_violin = fig.add_subplot(grid[0, 1])
ax_dot = fig.add_subplot(grid[1, 1], sharex=ax_violin)

# ------------------------------
# Top-right violin plot
# ------------------------------
sns.violinplot(
    data=plot_data,
    x="Fully Harmonized",
    y="Tech",
    hue="Tech",
    order=["DACCS", "Synfuels"],
    palette={"DACCS": "#40C6D1", "Synfuels": "#EA971D"},
    cut=0,
    inner=None,
    linewidth=0,
    ax=ax_violin,
    zorder=2,
)

for violin in ax_violin.findobj(PolyCollection):
    violin.set_edgecolor("none")

for tech, ypos in [("DACCS", 0), ("Synfuels", 1)]:
    vals = plot_data.loc[plot_data["Tech"] == tech, "Fully Harmonized"].dropna()
    if vals.empty:
        continue
    q25, q50, q75 = np.percentile(vals, [25, 50, 75])
    box_h = 0.14
    rect = Rectangle(
        (q25, ypos - box_h / 2),
        q75 - q25,
        box_h,
        edgecolor="#444343",
        facecolor="#444343",
        linewidth=1.2,
        zorder=3,
    )
    ax_violin.add_patch(rect)
    ax_violin.plot([q50, q50], [ypos - box_h / 2, ypos + box_h / 2], color="white", linewidth=2.2, zorder=4)

legend = ax_violin.get_legend()
if legend is not None:
    legend.remove()

ax_violin.set_xlabel("")
ax_violin.set_ylabel("")
ax_violin.set_yticks([0, 1])
ax_violin.set_yticklabels(["DACCS", "Synfuels"], fontsize=11)
ax_violin.tick_params(axis="x", labelbottom=False, length=0)
ax_violin.grid(True, axis="x", linestyle="-", alpha=0.45, zorder=1)
ax_violin.set_axisbelow(True)
for side in ["top", "right", "bottom", "left"]:
    ax_violin.spines[side].set_visible(False)

# ------------------------------
# Bottom-right dot plot
# ------------------------------
for y in study_to_y.values():
    ax_dot.axhline(y=y, color="lightgrey", linestyle="-", linewidth=0.7, zorder=1)

for _, row in plot_data.iterrows():
    ref = row["Reference"]
    if ref in study_to_y:
        ax_dot.scatter(
            row["Fully Harmonized"],
            study_to_y[ref],
            color="#40C6D1" if row["Tech"] == "DACCS" else "#EA971D",
            zorder=2,
            s=18,
            linewidths=0,
        )

ax_dot.set_yticks(list(study_to_y.values()))
ax_dot.set_yticklabels([""] * len(study_to_y))
ax_dot.tick_params(axis="y", left=True, width=0.7, color="lightgrey", length=36)
ax_dot.invert_yaxis()
ax_dot.grid(True, axis="x", linestyle="-", alpha=0.45)
ax_dot.set_axisbelow(True)
ax_dot.set_xlabel("Abatement cost ($/tCO2)", fontsize=12)
ax_dot.tick_params(axis="x", labelsize=12)
for side in ["top", "right", "bottom", "left"]:
    ax_dot.spines[side].set_visible(False)

# ------------------------------
# Left text table panel
# ------------------------------
ax_table.axis("off")

# Negative values move all table elements left; positive values move right.
table_x_shift = -0.06

# Column coordinates in axis fraction.
# Wider first column for study labels, then compact numeric columns.
x_positions = [0.015, 0.205, 0.385, 0.545, 0.725, 0.895]
x_positions = [x + table_x_shift for x in x_positions]
headers = ["Study"] + [label for _, label in table_columns]

# Align table rows to the exact y-positions of dot-plot rows.
y_values = []
for y in range(len(manual_study_order)):
    _, y_display = ax_dot.transData.transform((0.0, y))
    _, y_table = ax_table.transAxes.inverted().transform((0.0, y_display))
    y_values.append(y_table)

header_y = min(0.98, y_values[0] + 0.10)
for x, text in zip(x_positions, headers):
    ax_table.text(
        x,
        header_y,
        text,
        ha="center",
        va="bottom",
        fontsize=9.2,
        fontweight="bold",
        transform=ax_table.transAxes,
        linespacing=1.2,
    )

ax_table.plot(
    [0.00 + table_x_shift, 0.94 + table_x_shift],
    [min(0.95, y_values[0] + 0.055), min(0.95, y_values[0] + 0.055)],
    transform=ax_table.transAxes,
    color="black",
    lw=1.2,
)

for i, row_data in enumerate(summary_df.to_dict("records")):
    y = y_values[i]
    ref_label = f"[{int(row_data['Study'])}]"
    ax_table.text(
        x_positions[0],
        y,
        ref_label,
        ha="center",
        va="center",
        fontsize=10,
        transform=ax_table.transAxes,
    )

    for idx, (col_key, _) in enumerate(table_columns, start=1):
        value = row_data.get(col_key, "")
        ax_table.text(
            x_positions[idx],
            y,
            str(value),
            ha="center",
            va="center",
            fontsize=9.5,
            transform=ax_table.transAxes,
        )

# Group labels and separator between DACCS and Synfuels
sep_y = (y_values[len(study_numbers_daccs) - 1] + y_values[len(study_numbers_daccs)]) / 2
ax_table.plot(
    [-1 + table_x_shift, 0.95 + table_x_shift],
    [sep_y, sep_y],
    transform=ax_table.transAxes,
    color="lightgrey",
    lw=1.0,
)

daccs_mid = float(np.mean(y_values[: len(study_numbers_daccs)]))
syn_mid = float(np.mean(y_values[len(study_numbers_daccs) :]))
ax_table.text(
    -0.07 + table_x_shift,
    daccs_mid,
    "DACCS",
    ha="center",
    va="center",
    fontsize=10,
    transform=ax_table.transAxes,
)
ax_table.text(
    -0.07 + table_x_shift,
    syn_mid,
    "Synfuels",
    ha="center",
    va="center",
    fontsize=10,
    transform=ax_table.transAxes,
)

# Add panel labels
ax_table.text(
    -0.12 + table_x_shift,
    1.02,
    "a",
    ha="left",
    va="bottom",
    fontsize=12,
    fontweight="bold",
    transform=ax_table.transAxes,
)

ax_violin.text(
    -0.08,
    1.08,
    "b",
    ha="left",
    va="bottom",
    fontsize=12,
    fontweight="bold",
    transform=ax_violin.transAxes,
)

fig.savefig("combined_cost_panel.png", dpi=300, bbox_inches="tight")
plt.show()
plt.close(fig)
