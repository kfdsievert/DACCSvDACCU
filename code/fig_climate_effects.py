"""
Figure showing climate effects using GridSpec layout:
- Left: BAU (Business as Usual) emissions breakdown  
- Top Right: DACCS mitigation impact
- Bottom Right: SAF (Synfuels) mitigation impact

Uses data directly from user input (GWP100)
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ============================================================================
# DIRECT DATA INPUT (from user-provided table)
# ============================================================================

# BAU (fossil kerosene baseline) - GWP100
bau_data = {
    "CO2": {"nominal": 1540.99, "uncertainty": 0},
    "netNOx": {"nominal": 242.95, "uncertainty": 0},
    "SO2": {"nominal": -125.60, "uncertainty": 0},
    "BC": {"nominal": 16.16, "uncertainty": 0},
    "H2O": {"nominal": 34.21, "uncertainty": 0},
    "Contrail Cirrus and C-C": {"nominal": 1003.0, "uncertainty": 0}
}

# SAF reductions from BAU
saf_reductions = {
    "CO2": {"nominal": 1540.99, "uncertainty": 0},
    "netNOx": {"nominal": 0.0, "uncertainty": 0},
    "SO2": {"nominal": -125.60, "uncertainty": 0},
    "BC": {"nominal": 5.01, "uncertainty": 0},
    "H2O": {"nominal": -4.11, "uncertainty": 0},
    "Contrail Cirrus and C-C": {"nominal": 22.0, "uncertainty": 18}
}

# DACCS reductions from BAU
daccs_reductions = {
    "CO2": {"nominal": -1386.9, "uncertainty": 50},
    "netNOx": {"nominal": 0.0, "uncertainty": 0},
    "SO2": {"nominal": 0.0, "uncertainty": 0},
    "BC": {"nominal": 0.0, "uncertainty": 0},
    "H2O": {"nominal": 0.0, "uncertainty": 0},
    "Contrail Cirrus and C-C": {"nominal": 0.0, "uncertainty": 0}
}

# Define component list for ordering
emission_components = ['CO2', 'netNOx', 'SO2', 'BC', 'H2O', 'Contrail Cirrus and C-C']

# ============================================================================
# PLOTTING SETUP
# ============================================================================

fig = plt.figure(figsize=(14, 6), dpi=300)
gs = gridspec.GridSpec(2, 2, width_ratios=[1, 1.5], height_ratios=[1, 1], 
                       hspace=0.15, wspace=0.25)

ax_bau = fig.add_subplot(gs[:, 0])  # Left: spans both rows
ax_daccs = fig.add_subplot(gs[0, 1])  # Top right
ax_saf = fig.add_subplot(gs[1, 1])   # Bottom right

axs = [ax_bau, ax_daccs, ax_saf]

# Common settings - FIX XLIM TO MATCH DATA RANGE
for ax in axs:
    ax.set_xlim(-1600, 1800)  # Adjusted for actual data range
    ax.set_xticks(range(-1500, 1801, 500))
    ax.xaxis.grid(True, linestyle='-', alpha=0.3)
    ax.tick_params(axis='x', labelsize=10)
    ax.tick_params(axis='y', which='both', left=False, right=False)
    ax.axvline(0, color="black", linewidth=1.5)
    ax.xaxis.set_ticks_position('top')
    ax.xaxis.set_label_position('top')
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

# ============================================================================
# BAU EMISSIONS (Left panel, full height)
# ============================================================================

labels_bau = {
    "CO2": "Carbon dioxide emissions\n(CO₂)",
    "netNOx": "Net nitrogen oxide emissions\n(NOx)",
    "SO2": "Sulfur dioxide\n(SO₂)",
    "BC": "Soot\n(BC)",
    "H2O": "Water vapor\n(H₂O)",
    "Contrail Cirrus and C-C": "Contrail Cirrus in high humidity regions\n(Contrails)"
}

components_ordered = list(reversed(emission_components))
y_positions_bau = np.arange(len(components_ordered))

color_bau = "#FFA500"  # Orange for BAU/GWP*
bar_height = 0.7  # Increased bar height

for i, comp in enumerate(components_ordered):
    val = bau_data[comp]["nominal"]
    unc = bau_data[comp]["uncertainty"]
    
    ax_bau.barh(i, val, height=bar_height, color=color_bau, alpha=0.8, edgecolor='black', linewidth=1.2)
    ax_bau.errorbar(val, i, xerr=unc, color='black', capsize=4, linewidth=1.2, fmt='none', alpha=0.7)
    
    # Add value labels
    x_pos = val + unc + 80
    ax_bau.text(x_pos, i, f"{val:,.0f}", fontsize=9, va='center', ha='left', fontweight='bold')

ax_bau.set_yticks(y_positions_bau)
ax_bau.set_yticklabels([labels_bau[comp] for comp in components_ordered], fontsize=10)
ax_bau.set_xlabel("Climate effect (MtCO₂e)", fontsize=11, fontweight='bold')
ax_bau.set_title("Estimated emissions of fossil kerosene-based\naviation in 2050 (GWP100)", 
                fontsize=11, fontweight='bold', pad=15)

# ============================================================================
# DACCS PANEL (Top right)
# ============================================================================

labels_short = {
    "CO2": "CO₂",
    "netNOx": "NOx",
    "SO2": "SO₂",
    "BC": "Soot",
    "H2O": "H₂O",
    "Contrail Cirrus and C-C": "Contrails"
}

components_ordered_short = list(reversed(emission_components))
y_positions = np.arange(len(components_ordered_short))

color_daccs = "mediumturquoise"
bar_height = 0.7

for i, comp in enumerate(components_ordered_short):
    bau_val = bau_data[comp]["nominal"]
    bau_unc = bau_data[comp]["uncertainty"]
    reduction = daccs_reductions[comp]["nominal"]
    reduction_unc = daccs_reductions[comp]["uncertainty"]
    remaining = bau_val + reduction  # Remaining after DACCS
    
    # BAU bar (full bar)
    ax_daccs.barh(i, bau_val, height=bar_height, color=color_bau, alpha=0.7, edgecolor='black', linewidth=1.2)
    ax_daccs.errorbar(bau_val, i + 0.15, xerr=bau_unc, color='black', capsize=3, linewidth=0.8, fmt='none', alpha=0.5)
    
    # DACCS reduction bar (goes negative)
    if reduction != 0:
        ax_daccs.barh(i, -reduction, height=bar_height, color=color_daccs, alpha=0.7, edgecolor='black', linewidth=1.2)
        ax_daccs.errorbar(-reduction, i - 0.15, xerr=reduction_unc, color='black', capsize=3, linewidth=0.8, fmt='none', alpha=0.5)
    
    # Remaining point
    if remaining != 0:
        ax_daccs.scatter(remaining, i, s=50, color="black", alpha=0.9, zorder=3, marker='o')

ax_daccs.set_yticks(y_positions)
ax_daccs.set_yticklabels([labels_short[comp] for comp in components_ordered_short], fontsize=10)
ax_daccs.set_title("DACCS", fontsize=11, fontweight='bold')
ax_daccs.text(0.5, 1.18, "Climate effect of mitigation options\nper emission species (GWP100)", 
             transform=ax_daccs.transAxes, fontsize=10, ha='center', fontweight='bold')

# ============================================================================
# SAF PANEL (Bottom right)
# ============================================================================

color_saf = "royalblue"

for i, comp in enumerate(components_ordered_short):
    bau_val = bau_data[comp]["nominal"]
    bau_unc = bau_data[comp]["uncertainty"]
    reduction = saf_reductions[comp]["nominal"]
    reduction_unc = saf_reductions[comp]["uncertainty"]
    remaining = bau_val - reduction  # Remaining after SAF
    
    # BAU bar
    ax_saf.barh(i, bau_val, height=bar_height, color=color_bau, alpha=0.7, edgecolor='black', linewidth=1.2)
    ax_saf.errorbar(bau_val, i + 0.15, xerr=bau_unc, color='black', capsize=3, linewidth=0.8, fmt='none', alpha=0.5)
    
    # SAF reduction bar
    if reduction != 0:
        ax_saf.barh(i, -reduction, height=bar_height, color=color_saf, alpha=0.7, edgecolor='black', linewidth=1.2)
        ax_saf.errorbar(-reduction, i - 0.15, xerr=reduction_unc, color='black', capsize=3, linewidth=0.8, fmt='none', alpha=0.5)
    
    # Remaining point
    if remaining != 0:
        ax_saf.scatter(remaining, i, s=50, color="black", alpha=0.9, zorder=3, marker='o')

ax_saf.set_yticks(y_positions)
ax_saf.set_yticklabels([labels_short[comp] for comp in components_ordered_short], fontsize=10)
ax_saf.set_title("Synfuels (SAF)", fontsize=11, fontweight='bold')

# Side labels
ax_daccs.text(-0.32, 0.5, "DACCS", fontsize=11, fontweight='bold', rotation=90,
             transform=ax_daccs.transAxes, va='center', ha='center')
ax_saf.text(-0.32, 0.5, "Synfuels\n(SAF)", fontsize=11, fontweight='bold', rotation=90,
           transform=ax_saf.transAxes, va='center', ha='center')

# ============================================================================
# ADD PANEL LABELS
# ============================================================================

fig.text(0.02, 0.98, "a", fontsize=16, fontweight='bold', ha='left', va='top')
fig.text(0.55, 0.98, "b", fontsize=16, fontweight='bold', ha='left', va='top')

plt.savefig('climate_effects_figure.png', dpi=300, bbox_inches='tight')
print("✓ Figure saved as 'climate_effects_figure.png'")

# Print summary
print("\n" + "="*80)
print("DATA SUMMARY (GWP100)")
print("="*80)
print("\nBAU (fossil kerosene baseline) - MtCO₂e:")
for comp in emission_components:
    val = bau_data[comp]["nominal"]
    unc = bau_data[comp]["uncertainty"]
    print(f"  {comp:30s}: {val:>10.1f} +/- {unc:>6.1f}")

print("\nSAF reductions from BAU:")
for comp in emission_components:
    val = saf_reductions[comp]["nominal"]
    unc = saf_reductions[comp]["uncertainty"]
    print(f"  {comp:30s}: {val:>10.1f} +/- {unc:>6.1f}")

print("\nDACC reductions from BAU:")
for comp in emission_components:
    val = daccs_reductions[comp]["nominal"]
    unc = daccs_reductions[comp]["uncertainty"]
    print(f"  {comp:30s}: {val:>10.1f} +/- {unc:>6.1f}")

plt.show()
