import functions
import numpy as np
import pandas as pd
from uncertainties import unumpy, ufloat
import copy


# ---------------- Scenario Descriptions ----------------#
# BAU: Business as Usual, fossil fuelled aircraft are used for 100% of flights. Demand growth and efficiency improvements dictate emissions.
# SAF: SAF is deployed according to the progression curve in Brazzola et al. 2024. DACCS is used to abate residual emissions from synfuel manufacture, leading to "Net-zero" emissions from aviation.
# NOTE SAF scenario DOES NOT use DACCS to abate remaining NOx and C-C emissions.
# ---------------- Load inputs ----------------#

abatement_curve_saf, residual_emissions_saf = functions.load_input_abatement_cost(
    "data/Master Standardisation_SAF.xlsx", tech="SAF"
)
abatement_curve_daccs = functions.load_input_abatement_cost(
    "data/Master Standardisation DACCS.xlsx", tech="DACCS"
)
base_inputs = functions.load_base_inputs("data/base_input_brazzola.csv")
lee_df = functions.load_lee("data/lee_erf.csv")

# ---------------- Setup simulation parameters ----------------#
SIMULATION_START = 2025
SIMULATION_END = 2050
N_YEARS = SIMULATION_END - SIMULATION_START
WACC = 0.07
ANNUAL_DEMAND_GROWTH_RATE = 0.02
ANNUAL_EFFICIENCY_CHANGE = 0.01
MJ_PER_L = 34.69  # Standard volumetric energy density of Jet A-1 fuel (and SAF)
DENSITY_SAF = 0.803  # kg/L density of SAF
DT = 20  # Years for GWP* calculation
SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = [
    1.29e14,
    1.29e14,
]  # Current estimate of ice particles per km from Karcher (2018) Fig. 3 (https://www.nature.com/articles/s41467-018-04068-0) or Markl (2024) Fig. 3 (https://acp.copernicus.org/articles/24/3813/2024/acp-24-3813-2024.pdf) The list is lower and upper bound of the estimate.
SAF_SOOT_PARTICLE_REDUCTION = 0.31  # 31% reduction in soot particles from SAF compared to fossil fuel (Markl 2024)
CONTRAIL_REDUCTION = 0.64  # 80% reduction using maneuvers and 80% successful maneuvers = 64% reduction in contrails overall.
REROUTING_FUEL_PENALTY = 0.001  # 0.1% increase in fuel burn (A Martin Frias et. al. (2024): https://iopscience.iop.org/article/10.1088/2634-4505/ad310c#erisad310cs3,  Google (2023): https://blog.google/technology/ai/ai-airlines-contrails-climate-change/)
FUEL_PRICE_2050 = 1.54  # $/L standard assumption for average fuel price from various scenarios in from Master Standardization SAF (2024)
FLEET_SIZE_2025 = 28400  # Approximate fleet size of passenger aircraft in 2025 (Oliver Wyman: https://www.oliverwyman.com/our-expertise/insights/2024/feb/global-fleet-and-mro-market-forecast-2024-2034.html)
HUMIDITY_SENSOR_COST = 100000  # CAPEX of humidity sensor per aircraft in $
HUMIDITY_SENSOR_LIFE = 5  # Life of humidity sensor in years
SENSOR_REQUIREMENT = (
    0.3  # 30% of aircraft are equipped with humidity sensors (Multiple interviews)
)
INFRA_COST_MULTIPLIER = (
    1.25  # 25% additional cost of satellite infrastructure (Multiple interviews)
)


# Whether contrail avoidance is applied or not. Contrail Avoidance is ONLY applied in 2050 and not before.
CONTRAIL_AVOIDANCE = {"Fossil": False, "SAF": False}

# Whether Hydrotreatment is applied or not. Only in 2050.
HYDROTREATMENT = {"Fossil": True, "SAF": True}

# SAF factors are obtained from Brazzola et. al. 2024 or calculated using Markl 2024, Karcher 2018 and Lee et. al. 2023

# These are multipliers for the level of emissions from SAF fuelled aircraft.
saf_factors = {
    "CO2": 0,  # Assumed net neutral fuel
    "netNOx": 1,  # Own research
    "Contrail Cirrus and C-C": 0,  # Calculated in the simulation
    "BC": 1
    - SAF_SOOT_PARTICLE_REDUCTION,  # 31% reduction in soot particles from SAF compared to fossil fuel (interviews)
    "SO2": 0,  # Brazzola 2024
    "H2O": 1.12,  # Brazzola 2024
}

fossil_factors = {"Contrail Cirrus and C-C": 1}

emission_factors = {"Fossil": fossil_factors, "SAF": saf_factors}

emission_factors_base = {
    "Fossil": copy.deepcopy(fossil_factors),
    "SAF": copy.deepcopy(saf_factors),
}

hydrotreatment_cost_params = (
    functions.initialize_hydrotreatment_cost_params()
)  # Initializes cost parameters for hydrotreatment
hydrotreatment_emission_params = functions.initialize_hydrotreatment_emission_params()  # Initializes emission parameters for hydrotreatment, returns the ratio of emissions from hydrotreated fuel to fossil fuel


# ERF factors are obtained from Lee et. al. 2021. Used in GWP* calculation.
ERF_FACTORS = {
    # Nitrogen-related factors (mW/m²/TgN)
    "O3 short": 34.44,
    "O3 long": -9.35,
    "CH4": -18.69,
    "SWV": -2.80,
    "netNOx": 5.46,
    # Aerosols and particles
    "BC": 100.67,  # mW/m²/Tg BC
    "SO4": -19.91,  # mW/m²/Tg SO4
    "H2O": 0.0052,  # mW/m²/Tg H2O
    # Aviation specific
    "Contrail Cirrus and C-C": 9.36e-10,  # mW/m²/km
}

# ---------------- Generate aviation demand ----------------#
df_demand = functions.generate_aviation_demand(
    base_inputs, ANNUAL_DEMAND_GROWTH_RATE, ANNUAL_EFFICIENCY_CHANGE, N_YEARS
)

# ---------------- Generate Estimated decrease in CC ----------------#
# Efficiency improvement + Reduced soot from SAF, rf_factor_ht_saf is the ratio of emissions from hydrotreated fuel to base fuel (either SAF or Fossil)
emission_factors["SAF"]["Contrail Cirrus and C-C"], rf_factor_ht_saf = (
    functions.update_emission_factors(
        N_YEARS,
        ANNUAL_EFFICIENCY_CHANGE,
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
        SAF_SOOT_PARTICLE_REDUCTION,
        CONTRAIL_AVOIDANCE,
        CONTRAIL_REDUCTION,
        HYDROTREATMENT,
        hydrotreatment_emission_params,
        show_plots=False,
        tech="SAF",
    )
)
# Efficiency improvement
emission_factors["Fossil"]["Contrail Cirrus and C-C"], rf_factor_ht_fossil = (
    functions.update_emission_factors(
        N_YEARS,
        ANNUAL_EFFICIENCY_CHANGE,
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
        SAF_SOOT_PARTICLE_REDUCTION,
        CONTRAIL_AVOIDANCE,
        CONTRAIL_REDUCTION,
        HYDROTREATMENT,
        hydrotreatment_emission_params,
        show_plots=False,
        tech="Fossil",
    )
)
# Base condition is when contrail avoidance and hydrotreatment are not applied, hence Contrail Reduction is set to 0.
emission_factors_base["SAF"]["Contrail Cirrus and C-C"], rf_factor_ht_saf_base = (
    functions.update_emission_factors(
        N_YEARS,
        ANNUAL_EFFICIENCY_CHANGE,
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
        SAF_SOOT_PARTICLE_REDUCTION,
        CONTRAIL_AVOIDANCE,
        CONTRAIL_REDUCTION=0,
        HYDROTREATMENT={"Fossil": False, "SAF": False},
        ht_emission_params=hydrotreatment_emission_params,
        show_plots=False,
        tech="SAF",
    )
)

emission_factors_base["Fossil"]["Contrail Cirrus and C-C"], rf_factor_h_fossil_base = (
    functions.update_emission_factors(
        N_YEARS,
        ANNUAL_EFFICIENCY_CHANGE,
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
        SAF_SOOT_PARTICLE_REDUCTION,
        CONTRAIL_AVOIDANCE,
        CONTRAIL_REDUCTION=0,
        HYDROTREATMENT={"Fossil": False, "SAF": False},
        ht_emission_params=hydrotreatment_emission_params,
        show_plots=False,
        tech="Fossil",
    )
)

# --------------- Generate CO2 Emissions based on demand ---------------#
# Future emissions from aviation in BAU scenario. NOTE: These are NOT adjusted for contrail avoidance as it is only applied in 2050 and not applied for GWP*
future_emissions_fossil = functions.future_aviation_emissions(
    base_inputs,
    ANNUAL_EFFICIENCY_CHANGE,
    ANNUAL_DEMAND_GROWTH_RATE,
    tech="Fossil",
    emission_factors=emission_factors,
)

# Future emissions from aviation in SAF scenario
future_emissions_saf = functions.future_aviation_emissions(
    base_inputs,
    ANNUAL_EFFICIENCY_CHANGE,
    ANNUAL_DEMAND_GROWTH_RATE,
    tech="SAF",
    emission_factors=emission_factors,
)

# ---------------- Calculate ERF for all species emitted ----------------#
# Calculate ERF from all species emitted in BAU and SAF scenarios
erf_fossil = functions.calculate_ERF(future_emissions_fossil, ERF_FACTORS)

erf_saf = functions.calculate_ERF(future_emissions_saf, ERF_FACTORS)
# ---------------- Obtain GWP Equivalence for 2050 ----------------#
gwp_100 = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    emission_factors,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    CONTRAIL_AVOIDANCE,
    REROUTING_FUEL_PENALTY,
    metric="GWP100",
)

gwp_20 = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    emission_factors,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    CONTRAIL_AVOIDANCE,
    REROUTING_FUEL_PENALTY,
    metric="GWP20",
)

# Combine into one dataframe
gwp = pd.concat([gwp_100, gwp_20])
# Total emissions by summing up rows
gwp.loc[:, "Total"] = gwp.sum(axis=1)

# Baseline equivalents generated to keep baseline emissions without additional measures such as contrail avoidance. Contrail Avoidance is set to false here.
gwp_100_baseline = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    emission_factors_base,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    CONTRAIL_AVOIDANCE={"Fossil": False, "SAF": False},
    REROUTING_FUEL_PENALTY=REROUTING_FUEL_PENALTY,
    metric="GWP100",
)

gwp_20_baseline = functions.generate_equivalence_gwp(
    df_demand,
    base_inputs,
    2050,
    emission_factors_base,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    CONTRAIL_AVOIDANCE={"Fossil": False, "SAF": False},
    REROUTING_FUEL_PENALTY=REROUTING_FUEL_PENALTY,
    metric="GWP20",
)

# Combine into one dataframe
gwp_baseline = pd.concat([gwp_100_baseline, gwp_20_baseline])
# Total emissions by summing up rows
gwp_baseline.loc[:, "Total"] = gwp_baseline.sum(axis=1)

# ---------------- Obtain GWP* Equivalence for 2050 ----------------#
gwp_star = functions.generate_equivalence_gwp_star(
    erf_df_fossil=erf_fossil,
    erf_df_saf=erf_saf,
    base_inputs=base_inputs,
    year=2050,
    emission_factors=saf_factors,
    dt=DT,
)

# Append the CO2 column to gwp star from gwp as CO2 emissions are the same for both
gwp_star["CO2"] = gwp_star["CO2"].astype(float)
gwp_star.loc["GWP* BAU", "CO2"] = float(gwp_100.loc["GWP100 BAU", "CO2"])
# Total emissions by summing up rows
gwp_star.loc[:, "Total"] = gwp_star.sum(axis=1)

# ---------------- Calculate abatement costs ----------------#
# Cost of deploying SAF to abate total emissions from aviation in 2050.
# The cost is is calculated by multiplying the abatement cost ($/tCO2) with the total emissions (tCO2) in 2050.
abatement_cost_saf = functions.calculate_abatement_cost_saf(
    abatement_curve_saf, gwp_100_baseline, 2050, SIMULATION_START
)

# Cost of abating residualS SAF emissions using DACCS
residual_abatement_cost_saf = functions.calculate_residual_abatement_saf(
    residual_emissions_saf,
    df_demand,
    abatement_curve_daccs,
    2050,
    MJ_PER_L,
    SIMULATION_START,
)

# ---------------- Calculate total abatement costs ----------------#
total_abatement_cost_saf = abatement_cost_saf + residual_abatement_cost_saf  # In $2050

# Contrail Avoidance Calculation
contrail_avoidance_capex = functions.calculate_investment_contrail_avoidance(
    df_demand,
    FLEET_SIZE_2025,
    HUMIDITY_SENSOR_COST,
    SENSOR_REQUIREMENT,
    INFRA_COST_MULTIPLIER,
    WACC,
    HUMIDITY_SENSOR_LIFE,
)

abatement_costs_saf_per_ton_eq, abated_emissions_saf = (
    functions.calculate_total_abatement_cost_saf_non_co2(
        total_abatement_cost_saf, gwp_baseline, gwp_star
    )
)  # Total abatement cost per tonne of CO2 equivalent [$/tCO2eq.] excl. contrail avoidance

abatement_costs_daccs_per_ton_eq = functions.calculate_total_abatement_cost_dac_non_co2(
    abatement_curve_daccs, gwp_baseline, gwp_star
)  # Total abatement cost per tonne of CO2 equivalent [$/tCO2eq.] excl. contrail avoidance

abated_emissions_daccs = copy.deepcopy(
    abated_emissions_saf
)  # Equal emissions must be abated by both technologies.
if CONTRAIL_AVOIDANCE["Fossil"] or CONTRAIL_AVOIDANCE["SAF"]:
    (
        additional_abatement_costs_contrails_per_ton_eq,
        abated_emissions_contrail_avoidance,
        additional_cost_breakdown,
    ) = functions.calculate_additional_abatement_cost_contrail_avoidance(
        df_demand,
        gwp,
        gwp_baseline,
        contrail_avoidance_capex,
        REROUTING_FUEL_PENALTY,
        FUEL_PRICE_2050,
        MJ_PER_L,
    )


# ---------------- Calculate abatement from hydrotreatment ----------------#

ht_abatement_dfs = functions.calculate_additional_abatement_hydrotreatment(
    df_demand,
    hydrotreatment_emission_params,
    rf_factor_ht_saf,
    rf_factor_ht_fossil,
    gwp,
    MJ_PER_L,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    abate_so2=False,
    year=2050,
)

# ---------------- Add hydrotreatment costs ----------------#

hydrotreatment_costs = functions.calculate_hydrotreatment_cost(
    df_demand, hydrotreatment_cost_params, DENSITY_SAF, MJ_PER_L
)

hydrotreatment_costs["Green"] = (
    hydrotreatment_costs["Green"] + 0.35 * hydrotreatment_costs["Grey"]
)  # 35% additional CAPEX for green H2

abatement_costs_hydrotreatment = (
    functions.claculate_additional_abatement_cost_hydrotreatment(
        hydrotreatment_costs, ht_abatement_dfs
    )
)

# Update abatement costs for contrail avoidance and hydrotreatment.
gwp_final = copy.deepcopy(gwp)
if CONTRAIL_AVOIDANCE["SAF"]:
    if HYDROTREATMENT["SAF"]:
        gwp_final.loc[gwp_final.index.str.contains("SAF"),:] = gwp.loc[gwp.index.str.contains("SAF"),:]  - ht_abatement_dfs["Green"].loc[ht_abatement_dfs["Green"].index.str.contains("SAF"), :]
        for metric in abatement_costs_saf_per_ton_eq.keys():
            if metric != "GWP_star":
                if ht_abatement_dfs["Green"].loc[f"{metric} SAF", "Total"] > 0:
                    abatement_costs_saf_per_ton_eq[metric] = (
                        functions.calculate_total_abatement_cost(
                            [
                                (
                                    abatement_costs_saf_per_ton_eq[metric],
                                    abated_emissions_saf[metric],
                                ),
                                (
                                    additional_abatement_costs_contrails_per_ton_eq[
                                        f"{metric} SAF"
                                    ],
                                    abated_emissions_contrail_avoidance.loc[
                                        f"{metric} SAF", "Total"
                                    ],
                                ),
                                (
                                    abatement_costs_hydrotreatment["Green"][
                                        f"{metric} SAF"
                                    ],
                                    ht_abatement_dfs["Green"].loc[
                                        f"{metric} SAF", "Total"
                                    ],
                                ),
                            ]
                        )
                    )
    else:
        for metric in abatement_costs_saf_per_ton_eq.keys():
            if metric != "GWP_star":
                abatement_costs_saf_per_ton_eq[metric] = (
                    functions.calculate_total_abatement_cost(
                        [
                            (
                                abatement_costs_saf_per_ton_eq[metric],
                                abated_emissions_saf[metric],
                            ),
                            (
                                additional_abatement_costs_contrails_per_ton_eq[
                                    f"{metric} SAF"
                                ],
                                abated_emissions_contrail_avoidance.loc[
                                    f"{metric} SAF", "Total"
                                ],
                            ),
                        ]
                    )
                )
if CONTRAIL_AVOIDANCE["Fossil"]:
    if HYDROTREATMENT["Fossil"]:
        gwp_final.loc[gwp_final.index.str.contains("BAU"),:] = gwp.loc[gwp.index.str.contains("BAU"),:]  - ht_abatement_dfs["Green"].loc[ht_abatement_dfs["Green"].index.str.contains("BAU"), :]
        for metric in abatement_costs_daccs_per_ton_eq.keys():
            if metric != "GWP_star":
                if ht_abatement_dfs["Green"].loc[f"{metric} BAU", "Total"] > 0:
                    abatement_costs_daccs_per_ton_eq[metric] = (
                        functions.calculate_total_abatement_cost(
                            [
                                (
                                    abatement_costs_daccs_per_ton_eq[metric],
                                    abated_emissions_daccs[metric],
                                ),
                                (
                                    additional_abatement_costs_contrails_per_ton_eq[
                                        f"{metric} BAU"
                                    ],
                                    abated_emissions_contrail_avoidance.loc[
                                        f"{metric} BAU", "Total"
                                    ],
                                ),
                                (
                                    abatement_costs_hydrotreatment["Green"][
                                        f"{metric} BAU"
                                    ],
                                    ht_abatement_dfs["Green"].loc[
                                        f"{metric} BAU", "Total"
                                    ],
                                ),
                            ]
                        )
                    )
    else:
        for metric in abatement_costs_daccs_per_ton_eq.keys():
            if metric != "GWP_star":
                abatement_costs_daccs_per_ton_eq[metric] = (
                    functions.calculate_total_abatement_cost(
                        [
                            (
                                abatement_costs_daccs_per_ton_eq[metric],
                                abated_emissions_daccs[metric],
                            ),
                            (
                                additional_abatement_costs_contrails_per_ton_eq[
                                    f"{metric} BAU"
                                ],
                                abated_emissions_contrail_avoidance.loc[
                                    f"{metric} BAU", "Total"
                                ],
                            ),
                        ]
                    )
                )


# ---------------- Export results ----------------#
gwp_final.to_csv("outputs/gwp.csv")
gwp_star.to_csv("outputs/gwp_star.csv")
abated_emissions_contrail_avoidance.to_csv(
    "outputs/abated_emissions_contrail_avoidance.csv"
)
for df_name, df in abatement_costs_hydrotreatment.items():
    df.to_csv(f"outputs/{df_name}_Hydrogen_abatement_costs_hydrotreatment.csv")
for df_name, df in ht_abatement_dfs.items():
    df.to_csv(f"outputs/{df_name}_Hydrogen_abatement_hydrotreatment.csv")
for key, value in abatement_costs_saf_per_ton_eq.items():
    value.to_csv(f"outputs/{key}_abatement_cost_saf.csv")
for key, value in abatement_costs_daccs_per_ton_eq.items():
    value.to_csv(f"outputs/{key}_abatement_cost_daccs.csv")

print("Simulation complete. Results exported to outputs folder.")
