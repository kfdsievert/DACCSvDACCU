import functions
import numpy as np
import pandas as pd
from uncertainties import unumpy, ufloat


#---------------- Scenario Descriptions ----------------#
# BAU: Business as Usual, fossil fuelled aircraft are used for 100% of flights. Demand growth and efficiency improvements dictate emissions.
# DACCU: SAF is deployed according to the progression curve in Brazzola et al. 2024. DACCS is used to abate residual emissions from synfuel manufacture, leading to "Net-zero" emissions from aviation. 
# NOTE DACCU scenario DOES NOT use DACCS to abate NOx and C-C emissions.
#---------------- Load inputs ----------------#

abatement_curve_saf, residual_emissions_saf = functions.load_input_abatement_cost("data/Master Standardisation_SAF.xlsx", tech='SAF')
abatement_curve_daccs = functions.load_input_abatement_cost("data/Master Standardisation DACCS.xlsx", tech='DACCS')
base_inputs = functions.load_base_inputs("data/base_input_brazzola.csv")
lee_df = functions.load_lee("data/lee_erf.csv")

#---------------- Setup simulation parameters ----------------#
SIMULATION_START = 2025
SIMULATION_END = 2050
N_YEARS = SIMULATION_END - SIMULATION_START
ANNUAL_DEMAND_GROWTH_RATE = 0.02
ANNUAL_EFFICIENCY_CHANGE = 0.01
MJ_PER_L = 34.69 # Standard volumetric energy density of SAF
DT = 20 # Years for GWP* calculation
SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = [1e14, 1e15] # Current average estimate of ice particles per km from Karcher (2018) Fig. 3 (https://www.nature.com/articles/s41467-018-04068-0). The list is lower and upper bound of the estimate.
ICE_PARTICLE_ESTIMATE_PER_KM_2025 = [[2e13,1.5e14], [1e14,1e15]] # Current average estimate of ice particles per km from Karcher (2018) Fig. 3. The lists are the lower and upper bound of the estimate for the two curves.
SAF_SOOT_PARTICLE_REDUCTION = 0.475 # 47.5% reduction in soot particles from SAF compared to fossil fuel (Markl 2024)
# DACCU factors are obtained from Brazzola et. al. 2024 or calculated using Voigt 2024, Karcher 2018 and Lee et. al. 2023
# These are multipliers for the level of emissions from DACCU fuelled aircraft.
DACCU_FACTORS = { 
    'CO2': 0, 
    'netNOx': 0.9,
    'Contrail Cirrus and C-C': 0 # Calculated in the simulation
}

# ERF factors are obtained from Lee et. al. 2021
ERF_FACTORS = {
    # Nitrogen-related factors (mW/m²/TgN)
    "O3 short":  34.44,
    "O3 long":   -9.35,
    "CH4":      -18.69,
    "SWV":       -2.80,
    "netNOx":     5.46,
    
    # Aerosols and particles
    "BC":       100.67,    # mW/m²/Tg BC
    "SO4":      -19.91,    # mW/m²/Tg SO2
    "H2O":        0.0052,  # mW/m²/Tg H2O
    
    # Aviation specific
    "Contrail Cirrus and C-C": 9.36e-10  # mW/m²/km
}


#---------------- Generate aviation demand ----------------#
df_demand = functions.generate_aviation_demand(
    base_inputs, 
    ANNUAL_DEMAND_GROWTH_RATE, 
    ANNUAL_EFFICIENCY_CHANGE, 
    N_YEARS
)

#---------------- Generate Estimated decrease in CC ----------------#
efficiency_improvement = ((1-ANNUAL_EFFICIENCY_CHANGE) ** N_YEARS)
SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = np.array(SOOT_PARTICLE_ESTIMATE_PER_KM_2025)
ICE_PARTICLE_ESTIMATE_PER_KM_2025 = [functions.get_nucleated_ice_crystals(p_count,plot=True) for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2025]

# Future emissions accounting for efficiency improvements
SOOT_PARTICLE_ESTIMATE_PER_KM_2050 = SOOT_PARTICLE_ESTIMATE_PER_KM_2025 * efficiency_improvement
ICE_PARTICLE_ESTIMATE_PER_KM_2050 = [functions.get_nucleated_ice_crystals(p_count,plot=True) for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2050]
ICE_PARTICLE_ESTIMATE_PER_KM_2050 = np.array(ICE_PARTICLE_ESTIMATE_PER_KM_2050)

# Future soot particles and nucleated ice particles from SAF fuelled aircraft
future_soot_particles_daccu = SOOT_PARTICLE_ESTIMATE_PER_KM_2050 * (1-SAF_SOOT_PARTICLE_REDUCTION) # Markl 2024
future_nucleated_ice_particles_daccu = [functions.get_nucleated_ice_crystals(p_count,plot=True) for p_count in future_soot_particles_daccu]
future_nucleated_ice_particles_daccu = np.array(future_nucleated_ice_particles_daccu)

# Account for efficiency improvements
#future_nucleated_ice_particles_daccu = future_nucleated_ice_particles_daccu * efficiency_improvement
normalised_nucleated_ice_particles_daccu = future_nucleated_ice_particles_daccu / ICE_PARTICLE_ESTIMATE_PER_KM_2050

# Normalized RF Factor for Contrails:
vectorized_calculate_normalised_rf = np.vectorize(functions.calculate_normalised_rf)
daccu_factors = vectorized_calculate_normalised_rf(normalised_nucleated_ice_particles_daccu)
nominal_daccu_factor = np.mean(daccu_factors)
std_daccu_factor = np.std(daccu_factors)
daccu_factor = ufloat(nominal_daccu_factor, std_daccu_factor)

DACCU_FACTORS["Contrail Cirrus and C-C"] = daccu_factor

#--------------- Generate CO2 Emissions based on demand ---------------# 
# Future emissions from aviation in BAU scenario
future_emissions_fossil = functions.future_aviation_emissions(
    base_inputs,
    ANNUAL_EFFICIENCY_CHANGE,
    ANNUAL_DEMAND_GROWTH_RATE,
    scenario= "BAU", 
    DACCU_FACTORS=DACCU_FACTORS
)

# Future emissions from aviation in DACCU scenario
future_emissions_daccu = functions.future_aviation_emissions(
    base_inputs,
    ANNUAL_EFFICIENCY_CHANGE,
    ANNUAL_DEMAND_GROWTH_RATE,
    scenario= "DACCU",
    DACCU_FACTORS=DACCU_FACTORS
)

#---------------- Calculate ERF for all species emitted ----------------#
# Calculate ERF from all species emitted
erf_fossil = functions.calculate_ERF(
    future_emissions_fossil,
    ERF_FACTORS
)

erf_daccu = functions.calculate_ERF(
    future_emissions_daccu,
    ERF_FACTORS
)
#---------------- Obtain GWP Equivalence for 2050 ----------------#
gwp_100 = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    DACCU_FACTORS,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    metric = "GWP100"
)

gwp_20 = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    DACCU_FACTORS,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    metric = "GWP20"
)

# Combine into one dataframe
gwp = pd.concat([gwp_100, gwp_20])
# Total emissions by summing up rows
gwp.loc[:,"Total"] = gwp.sum(axis=1)

#---------------- Obtain GWP* Equivalence for 2050 ----------------#
gwp_star = functions.generate_equivalence_gwp_star(
    erf_df_fossil = erf_fossil,
    erf_df_daccu = erf_daccu,
    base_inputs = base_inputs, 
    year = 2050,
    DACCU_FACTORS= DACCU_FACTORS,
    dt = DT
)

# Append the CO2 column to gwp star from gwp as CO2 emissions are the same for both
gwp_star["CO2"] = gwp_star["CO2"].astype(float)
gwp_star.loc["GWP* BAU", "CO2"] = float(gwp_100.loc["GWP100 BAU", "CO2"])
# Total emissions by summing up rows
gwp_star.loc[:,"Total"] = gwp_star.sum(axis=1)

#---------------- Calculate abatement costs ----------------#
# Cost of deploying SAF to abate total emissions from aviation in 2050. 
# The cost is is calculated by multiplying the abatement cost ($/tCO2) with the total emissions (tCO2) in 2050.

abatement_cost_saf = functions.calculate_abatement_cost_saf(
    abatement_curve_saf, 
    gwp_100, 
    2050, 
    SIMULATION_START
)

# Cost of abating residualS SAF emissions using DACCS
residual_abatement_cost_saf = functions.calculate_residual_abatement_saf(
    residual_emissions_saf,
    df_demand,
    abatement_curve_daccs,
    2050,
    MJ_PER_L,
    SIMULATION_START
)

#---------------- Calculate total abatement costs ----------------#
total_abatement_cost_saf = abatement_cost_saf + residual_abatement_cost_saf # In $2050

abatement_costs_saf_per_ton_eq = functions.calculate_total_abatement_cost_saf_non_co2(total_abatement_cost_saf, gwp, gwp_star) # Total abatement cost per tonne of CO2 equivalent [$/tCO2eq.]

abatement_costs_daccs_per_ton_eq = functions.calculate_total_abatemnet_cost_dac_non_co2(abatement_curve_daccs, gwp, gwp_star) # Total abatement cost per tonne of CO2 equivalent [$/tCO2eq.]

#---------------- Export results ----------------#
gwp.to_csv("outputs/gwp.csv")
gwp_star.to_csv("outputs/gwp_star.csv")
for key, value in abatement_costs_saf_per_ton_eq.items():
    value.to_csv(f"outputs/{key}_abatement_cost_saf.csv")

for key, value in abatement_costs_daccs_per_ton_eq.items():
    value.to_csv(f"outputs/{key}_abatement_cost_daccs.csv")

print("Simulation complete. Results exported to outputs folder.")
