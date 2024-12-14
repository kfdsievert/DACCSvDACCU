import functions

#---------------- Load inputs ----------------#

abatement_cost_saf = functions.load_input_abatement_cost("data/Master Standardisation_SAF.xlsx", tech='SAF')
abatement_cost_daccs = functions.load_input_abatement_cost("data/Master Standardisation DACCS.xlsx", tech='DACCS')
base_inputs = functions.load_base_inputs("data/base_input_brazzola.csv")

#---------------- Setup simulation parameters ----------------#
SIMULATION_START = 2025
SIMULATION_END = 2050
N_YEARS = SIMULATION_END - SIMULATION_START
ANNUAL_DEMAND_GROWTH_RATE = 0.02
ANNUAL_EFFICIENCY_CHANGE = 0.01

#---------------- Generate aviation demand ----------------#
df_demand = functions.generate_aviation_demand(
    base_inputs, 
    ANNUAL_DEMAND_GROWTH_RATE, 
    ANNUAL_EFFICIENCY_CHANGE, 
    N_YEARS
)

