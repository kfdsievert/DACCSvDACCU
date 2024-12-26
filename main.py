import functions

#---------------- Load inputs ----------------#

abatement_cost_saf = functions.load_input_abatement_cost("data/Master Standardisation_SAF.xlsx", tech='SAF')
abatement_cost_daccs = functions.load_input_abatement_cost("data/Master Standardisation DACCS.xlsx", tech='DACCS')
base_inputs = functions.load_base_inputs("data/base_input_brazzola.csv")
lee_df = functions.load_lee("data/lee_erf.csv")

#---------------- Setup simulation parameters ----------------#
SIMULATION_START = 2025
SIMULATION_END = 2050
N_YEARS = SIMULATION_END - SIMULATION_START
ANNUAL_DEMAND_GROWTH_RATE = 0.02
ANNUAL_EFFICIENCY_CHANGE = 0.01
DT = 20 # Years for GWP* calculation
# DACCU factors are considered from Brazzola et. al. 2024
# These are multipliers for the level of emissions from DACCU fuelled aircraft.
DACCU_FACTORS = { 
    'CO2': 0, 
    'Net NOx': 0.9,
    'CC': 0.55
}

#---------------- Generate aviation demand ----------------#
df_demand = functions.generate_aviation_demand(
    base_inputs, 
    ANNUAL_DEMAND_GROWTH_RATE, 
    ANNUAL_EFFICIENCY_CHANGE, 
    N_YEARS
)

#---------------- Generate ERF for NOx and C-C till 2050 ----------------#
df_erf = functions.project_erf(
    lee_df, 
    ANNUAL_EFFICIENCY_CHANGE,
    ANNUAL_DEMAND_GROWTH_RATE,
    SIMULATION_START, 
    SIMULATION_END
)

#---------------- Obtain GWP Equivalence for 2050 ----------------#
gwp = functions.generate_equivalence_gwp(
    df_demand,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    metric = "GWP100"
)

#---------------- Obtain GWP* Equivalence for 2050 ----------------#
gwp_star = functions.generate_equivalence_gwp_star(
    df_erf,
    base_inputs, 
    2050,
    DACCU_FACTORS,
    DT
)

# Append the CO2 column to gwp star from gwp.
gwp_star = gwp_star.assign(CO2=gwp['CO2'])

print(gwp)
print(gwp_star)



