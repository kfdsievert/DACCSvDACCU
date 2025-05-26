import functions
import pandas as pd
import copy
from datetime import datetime
import os
import itertools
import time
from uncertainties import ufloat

# Determine if the script should run for each sensitivity (electricity price, fossil fuel price, and contrail avoidance.)
RUN_SENSITIVITES = False


def main(
    contrail_avoidance,
    hydrotreatment,
    abate_so2,
    saf_input,
    daccs_input,
    sensitivities=False,
    sensitivity_name="Default",
):
    # ---------------- Scenario Descriptions ----------------#
    # BAU: Business as Usual, fossil fuelled aircraft are used for 100% of flights. Demand growth and efficiency improvements dictate emissions.
    # SAF: SAF is deployed according to the progression curve in Brazzola et al. 2024. DACCS is used to abate residual emissions from synfuel manufacture, leading to "Net-zero" emissions from aviation.
    # ---------------- Load inputs ----------------#

    abatement_curve_saf, residual_emissions_saf = functions.load_input_abatement_cost(
        f"data/{saf_input}", tech="SAF"
    )
    # daccs_input = "Master Standardisation DACCS_LE.xlsx" # Testing for low electricity price
    abatement_curve_daccs = functions.load_input_abatement_cost(
        f"data/{daccs_input}", tech="DACCS"
    )
    base_inputs = functions.load_base_inputs("data/base_input_brazzola.csv")
    lee_df = functions.load_lee("data/lee_erf.csv")

    # abatement_curve_saf.iloc[-1] = [984, 501, 1467] # Update for Blue hydrogen in SAF production. 

    # ---------------- Setup simulation parameters ----------------#
    SIMULATION_START = 2025
    SIMULATION_END = 2050
    N_YEARS = SIMULATION_END - SIMULATION_START
    WACC = 0.07
    ANNUAL_DEMAND_GROWTH_RATE = 0.02
    ANNUAL_EFFICIENCY_CHANGE = 0.01
    DEMAND_SHARE = "Global" # To restrict the simulation to a specific region
    MJ_PER_L = 34.69  # Standard volumetric energy density of Jet A-1 fuel (and SAF)
    DENSITY_SAF = 0.803  # kg/L density of SAF
    DT = 20  # Years for GWP* calculation
    SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = [
        1e15
    ]  # Current estimate of soot particles per km from Karcher (2018) Fig. 3 (https://www.nature.com/articles/s41467-018-04068-0) or Markl (2024) Fig. 3 (https://acp.copernicus.org/articles/24/3813/2024/acp-24-3813-2024.pdf) The list is lower and upper bound of the estimate.

    BLENDING_RATIO = 1  # Blending ratio of SAF in the fuel mix. This shifts the progression curve. Default is 1 (100% SAF by 2050)

    # Contrail avoidance is picked to avoid negative emissions when CA sensitivity is applied.
    if sensitivity_name != "CA":
        CONTRAIL_REDUCTION = ufloat(
            0.57, 0.07
        )  # 50-64% Contrails reduced by re-routing (Multiple interviews)
    else: 
        CONTRAIL_REDUCTION = ufloat(
            0.48, 0.06
        )
    REROUTING_FUEL_PENALTY = ufloat(
        0.003, 0.002
    )  # 0.1-0.5% increase in fuel burn (A Martin Frias et. al. (2024): https://iopscience.iop.org/article/10.1088/2634-4505/ad310c#erisad310cs3,  Google (2023): https://blog.google/technology/ai/ai-airlines-contrails-climate-change/)
    FUEL_PRICE_2050 = 0.8  # $/L standard assumption for average fuel price from various scenarios in from Master Standardization SAF (2024)
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
    CONTRAIL_AVOIDANCE = contrail_avoidance

    # Whether Hydrotreatment is applied or not. Only in 2050.
    HYDROTREATMENT = hydrotreatment

    # SAF factors are obtained from Brazzola et. al. 2024 or calculated using Markl 2024, Karcher 2018 and Lee et. al. 2023

    # These are multipliers for the level of emissions from SAF fuelled aircraft.
    saf_factors = {
        "CO2": 0,  # Assumed net neutral fuel
        "netNOx": 1,  # Own research
        "Contrail Cirrus and C-C": 0,  # Calculated in the simulation
        "BC": 1
        - 0.31,  # 31% reduction in soot particles from SAF compared to fossil fuel (interviews)
        "SO2": 0.03,  # Brazzola 2024
        "H2O": 1.07,  # Brazzola 2024
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

    demand_shares = {
        "Global" : 1, 
        "Europe" : 0.17, 
        "North America": 0.17,
        "Asia Pacific" : 0.44,
    }

    df_demand = df_demand * demand_shares[DEMAND_SHARE]

    # ---------------- Generate Estimated decrease in CC ----------------#
    # Efficiency improvement + Reduced soot from SAF, rf_factor_ht_saf is the ratio of emissions from hydrotreated fuel to base fuel (either SAF or Fossil)
    emission_factors["SAF"]["Contrail Cirrus and C-C"], rf_factor_ht_saf = (
        functions.update_emission_factors(
            N_YEARS,
            ANNUAL_EFFICIENCY_CHANGE,
            SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
            0.31,
            CONTRAIL_AVOIDANCE,
            CONTRAIL_REDUCTION,
            HYDROTREATMENT,
            hydrotreatment_emission_params,
            show_plots=False,
            tech="SAF",
            sensitivity_name=sensitivity_name,
        )
    )
    # Efficiency improvement
    emission_factors["Fossil"]["Contrail Cirrus and C-C"], rf_factor_ht_fossil = (
        functions.update_emission_factors(
            N_YEARS,
            ANNUAL_EFFICIENCY_CHANGE,
            SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
            0.31,
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
            0.31,
            CONTRAIL_AVOIDANCE,
            CONTRAIL_REDUCTION=0,
            HYDROTREATMENT={"Fossil": False, "SAF": False},
            ht_emission_params=hydrotreatment_emission_params,
            show_plots=False,
            tech="SAF",
        )
    )

    (
        emission_factors_base["Fossil"]["Contrail Cirrus and C-C"],
        rf_factor_ht_fossil_base,
    ) = functions.update_emission_factors(
        N_YEARS,
        ANNUAL_EFFICIENCY_CHANGE,
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
        0.31,
        CONTRAIL_AVOIDANCE,
        CONTRAIL_REDUCTION=0,
        HYDROTREATMENT={"Fossil": False, "SAF": False},
        ht_emission_params=hydrotreatment_emission_params,
        show_plots=False,
        tech="Fossil",
    )

    if "CA" in sensitivity_name:
        emission_factors["SAF"]["Contrail Cirrus and C-C"] = 0.

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
        blending_ratio=BLENDING_RATIO,
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
        blending_ratio=BLENDING_RATIO,
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
        blending_ratio=BLENDING_RATIO,
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
        blending_ratio=BLENDING_RATIO,
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
    gwp_star["CO2"] = gwp_star["CO2"].astype("O")
    gwp_star.loc["GWP* BAU", "CO2"] = gwp_100.loc["GWP100 BAU", "CO2"]
    # Total emissions by summing up rows
    gwp_star.loc[:, "Total"] = gwp_star.sum(axis=1)

    # ---------------- Initialize abated emissions storage ----------------#
    abated_emissions_index = [
        "GWP100 SAF",
        "GWP20 SAF",
        "GWP* SAF",
        "GWP100 Contrail Avoidance BAU",
        "GWP100 Contrail Avoidance SAF",
        "GWP20 Contrail Avoidance BAU",
        "GWP20 Contrail Avoidance SAF",
        "GWP100 Hydrotreatment",
        "GWP20 Hydrotreatment",
    ]
    abated_emissions_cols = gwp.columns
    abated_emissions_main_df_abs = pd.DataFrame(
        index=abated_emissions_index, columns=abated_emissions_cols
    )  # Shows absolute abated emissions for each abatement method.
    abated_emissions_main_df_pct = pd.DataFrame(
        index=abated_emissions_index, columns=abated_emissions_cols
    )  # Shows percentage change in CO2 equivalents for each abatement method.

    abated_emissions_main_df_abs.loc["GWP100 SAF", :] = (
        gwp_baseline.loc["GWP100 BAU", :] - gwp_baseline.loc["GWP100 SAF", :]
    )
    abated_emissions_main_df_abs.loc["GWP20 SAF", :] = (
        gwp_baseline.loc["GWP20 BAU", :] - gwp_baseline.loc["GWP20 SAF", :]
    )
    abated_emissions_main_df_abs.loc["GWP* SAF", :] = (
        gwp_star.loc["GWP* BAU", :] - gwp_star.loc["GWP* SAF", :]
    )

    abated_emissions_main_df_pct.loc["GWP100 SAF", :] = (
        (gwp_baseline.loc["GWP100 SAF", :] - gwp_baseline.loc["GWP100 BAU", :]) * 100
    ) / gwp_baseline.loc["GWP100 BAU", :]
    abated_emissions_main_df_pct.loc["GWP20 SAF", :] = (
        (gwp_baseline.loc["GWP20 SAF", :] - gwp_baseline.loc["GWP20 BAU", :]) * 100
    ) / gwp_baseline.loc["GWP20 BAU", :]
    abated_emissions_main_df_pct.loc["GWP* SAF", :] = (
        (gwp_star.loc["GWP* SAF", :] - gwp_star.loc["GWP* BAU", :])
        * 100
        / gwp_star.loc["GWP* BAU", :]
    )

    abated_emissions_main_df_pct.loc[
        :, "SO2"
    ] *= -1  # Account for cooling effect of SO2

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
    total_abatement_cost_saf = (
        abatement_cost_saf + residual_abatement_cost_saf
    )  # In $2050

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

    abatement_cost_saf_only = copy.deepcopy(abatement_costs_saf_per_ton_eq)


    abatement_costs_daccs_per_ton_eq = {"GWP100": pd.DataFrame(), "GWP20": pd.DataFrame(), "GWP_star": pd.DataFrame()}
    
    # Abatement costs for DACCS are the same in $/tCO2 and $/tCO2eq.
    for metric in ["GWP100", "GWP20", "GWP_star"]:
        abatement_costs_daccs_per_ton_eq[metric] = abatement_curve_daccs.iloc[-1]

    abatement_cost_daccs_only = copy.deepcopy(abatement_costs_daccs_per_ton_eq)

    abated_emissions_daccs = copy.deepcopy(
        abated_emissions_saf
    )  # Equal emissions are abated by both technologies.

    abated_emissions_main_df_abs.loc["GWP100 BAU DACCS", "Total"] = (
        abated_emissions_daccs["GWP100"]
    )
    abated_emissions_main_df_abs.loc["GWP20 BAU DACCS", "Total"] = (
        abated_emissions_daccs["GWP20"]
    )

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
        # Absolute Abated Emissions in MtCO2eq
        abated_emissions_main_df_abs.loc["GWP100 Contrail Avoidance BAU", :] = (
            abated_emissions_contrail_avoidance.loc["GWP100 BAU", :]
        )
        abated_emissions_main_df_abs.loc["GWP100 Contrail Avoidance SAF", :] = (
            abated_emissions_contrail_avoidance.loc["GWP100 SAF", :]
        )
        abated_emissions_main_df_abs.loc["GWP20 Contrail Avoidance BAU", :] = (
            abated_emissions_contrail_avoidance.loc["GWP20 BAU", :]
        )
        abated_emissions_main_df_abs.loc["GWP20 Contrail Avoidance SAF", :] = (
            abated_emissions_contrail_avoidance.loc["GWP20 SAF", :]
        )

        # Abated emissions w.r.t baseline as a percentage (Business as Usual scenario)
        abated_emissions_main_df_pct.loc["GWP100 Contrail Avoidance BAU", :] = (
            abated_emissions_contrail_avoidance.loc["GWP100 BAU", :] * -100
        ) / gwp_baseline.loc["GWP100 BAU", :]
        abated_emissions_main_df_pct.loc["GWP100 Contrail Avoidance SAF", :] = (
            abated_emissions_contrail_avoidance.loc["GWP100 BAU", :] * -100
        ) / gwp_baseline.loc["GWP100 BAU", :]
        abated_emissions_main_df_pct.loc["GWP20 Contrail Avoidance BAU", :] = (
            abated_emissions_contrail_avoidance.loc["GWP20 BAU", :] * -100
        ) / gwp_baseline.loc["GWP20 BAU", :]
        abated_emissions_main_df_pct.loc["GWP20 Contrail Avoidance SAF", :] = (
            abated_emissions_contrail_avoidance.loc["GWP20 BAU", :] * -100
        ) / gwp_baseline.loc["GWP20 BAU", :]

    # ---------------- Calculate abatement from hydrotreatment ----------------#

    ht_abatement_dfs = functions.calculate_additional_abatement_hydrotreatment(
        df_demand,
        hydrotreatment_emission_params,
        rf_factor_ht_saf,
        rf_factor_ht_fossil,
        gwp_baseline,
        MJ_PER_L,
        ANNUAL_EFFICIENCY_CHANGE,
        N_YEARS,
        abate_so2=abate_so2,  # Whether SO2 abatement is considered in this simulation. Save file is named accordingly
        year=2050,
    )

    # ---------------- Calculate abatement cost for hydrotreatment ----------------#

    hydrotreatment_costs = functions.calculate_hydrotreatment_cost(
        df_demand, hydrotreatment_cost_params, DENSITY_SAF, MJ_PER_L
    )

    hydrotreatment_costs["Green"] = (
        hydrotreatment_costs["Green"] + 0.35 * hydrotreatment_costs["Grey"]
    )  # 35% additional CAPEX for green H2

    abatement_costs_hydrotreatment = (
        functions.calculate_additional_abatement_cost_hydrotreatment(
            hydrotreatment_costs, ht_abatement_dfs
        )
    )

    if HYDROTREATMENT["Fossil"]:
        # Absolute Abated Emissions in MtCO2eq
        abated_emissions_main_df_abs.loc["GWP100 Hydrotreatment", :] = ht_abatement_dfs[
            "Green"
        ].loc["GWP100 BAU", :]
        abated_emissions_main_df_abs.loc["GWP20 Hydrotreatment", :] = ht_abatement_dfs[
            "Green"
        ].loc["GWP20 BAU", :]

        # Abated emissions w.r.t baseline as a percentage (Business as Usual scenario)
        abated_emissions_main_df_pct.loc["GWP100 Hydrotreatment", :] = (
            ht_abatement_dfs["Green"].loc["GWP100 BAU", :] * -100
        ) / gwp.loc["GWP100 BAU", :]
        abated_emissions_main_df_pct.loc["GWP20 Hydrotreatment", :] = (
            ht_abatement_dfs["Green"].loc["GWP20 BAU", :] * -100
        ) / gwp.loc["GWP20 BAU", :]

    # Update abatement costs for contrail avoidance and hydrotreatment.
    gwp_final = copy.deepcopy(gwp)

    for fuel_type in ["SAF", "Fossil"]:
        fuel_label = "BAU" if fuel_type == "Fossil" else "SAF"
        abatement_costs = (
            abatement_costs_daccs_per_ton_eq
            if fuel_type == "Fossil"
            else abatement_costs_saf_per_ton_eq
        )
        abated_emissions = (
            abated_emissions_daccs if fuel_type == "Fossil" else abated_emissions_saf
        )

        for metric in abatement_costs.keys():
            if metric == "GWP_star":
                continue

            cost_components = [(abatement_costs[metric], abated_emissions[metric])]

            if CONTRAIL_AVOIDANCE[fuel_type]:
                abated_emissions[metric] += abated_emissions_contrail_avoidance.loc[
                    f"{metric} {fuel_label}", "Total"
                ]
                cost_components.append(
                    (
                        additional_abatement_costs_contrails_per_ton_eq[
                            f"{metric} {fuel_label}"
                        ],
                        abated_emissions_contrail_avoidance.loc[
                            f"{metric} {fuel_label}", "Total"
                        ],
                    )
                )

            if (
                HYDROTREATMENT[fuel_type]
                and ht_abatement_dfs["Green"].loc[f"{metric} {fuel_label}", "Total"] > 0
            ):
                abated_emissions[metric] += ht_abatement_dfs["Green"].loc[
                    f"{metric} {fuel_label}", "Total"
                ]
                gwp_final.loc[gwp_final.index.str.contains(fuel_label), :] = (
                    gwp.loc[gwp.index.str.contains(fuel_label), :]
                    - ht_abatement_dfs["Green"].loc[
                        ht_abatement_dfs["Green"].index.str.contains(fuel_label), :
                    ]
                )
                cost_components.append(
                    (
                        abatement_costs_hydrotreatment["Green"][
                            f"{metric} {fuel_label}"
                        ],
                        ht_abatement_dfs["Green"].loc[
                            f"{metric} {fuel_label}", "Total"
                        ],
                    )
                )

            abatement_costs[metric] = functions.calculate_weighted_abatement_cost(
                cost_components
            )

    abated_emissions_dict = {
        "SAF": abated_emissions_saf,
        "DACCS": abated_emissions_daccs,
    }
    # ---------------- Abate remaining emissions with DACCS ----------------#
    remaining_emissions_saf, remaining_emissions_daccs = (
        functions.calculate_daccs_cost_remaining_emissions(
            gwp_baseline, gwp_star, abated_emissions_dict, abatement_curve_daccs
        )
    )

    abated_emissions_main_df_abs.loc["GWP100 BAU DACCS", "Total"] += (
        remaining_emissions_daccs["GWP100"]
    )
    abated_emissions_main_df_abs.loc["GWP20 BAU DACCS", "Total"] += (
        remaining_emissions_daccs["GWP20"]
    )
    abated_emissions_main_df_abs.loc["GWP100 SAF DACCS", "Total"] = (
        remaining_emissions_saf["GWP100"]
    )
    abated_emissions_main_df_abs.loc["GWP20 SAF DACCS", "Total"] = (
        remaining_emissions_saf["GWP20"]
    )

    abated_emissions_main_df_pct.loc["GWP100 BAU DACCS", "Total"] = (
        abated_emissions_main_df_abs.loc["GWP100 BAU DACCS", "Total"] * -100
    ) / gwp_baseline.loc["GWP100 BAU", "Total"]
    abated_emissions_main_df_pct.loc["GWP20 BAU DACCS", "Total"] = (
        abated_emissions_main_df_abs.loc["GWP20 BAU DACCS", "Total"] * -100
    ) / gwp_baseline.loc["GWP20 BAU", "Total"]
    abated_emissions_main_df_pct.loc["GWP100 SAF DACCS", "Total"] = (
        abated_emissions_main_df_abs.loc["GWP100 SAF DACCS", "Total"] * -100
    ) / gwp_baseline.loc["GWP100 BAU", "Total"]
    abated_emissions_main_df_pct.loc["GWP20 SAF DACCS", "Total"] = (
        abated_emissions_main_df_abs.loc["GWP20 SAF DACCS", "Total"] * -100
    ) / gwp_baseline.loc["GWP20 BAU", "Total"]

    for tech in ["SAF", "DACCS"]:
        abated_emissions = (
            abated_emissions_saf if tech == "SAF" else abated_emissions_daccs
        )
        remaining_emissions = (
            remaining_emissions_saf if tech == "SAF" else remaining_emissions_daccs
        )
        abatement_cost = (
            abatement_costs_saf_per_ton_eq
            if tech == "SAF"
            else abatement_costs_daccs_per_ton_eq
        )
        abatement_cost_daccs = abatement_curve_daccs.iloc[-1, :]

        for metric in abatement_cost.keys():
            if metric == "GWP_star":
                continue
            abatement_cost[metric] = (
                abatement_cost[metric] * abated_emissions[metric]
                + abatement_cost_daccs * remaining_emissions[metric]
            ) / (abated_emissions[metric] + remaining_emissions[metric])
            abated_emissions[metric] += remaining_emissions[metric]

    # ----------------- Calculate abatement cost contributions for each method of abatement -----------------#

    if contrail_avoidance["Fossil"] or contrail_avoidance["SAF"]:
        abatement_contributions = functions.calculate_contribution_to_abatement_cost(
            abated_emissions_main_df_abs,
            abatement_cost_saf_only,
            abatement_cost_daccs_only,
            abatement_costs_hydrotreatment,
            abated_emissions,
            additional_abatement_costs_contrails_per_ton_eq,
        )

    else:
        abatement_contributions = functions.calculate_contribution_to_abatement_cost(
            abated_emissions_main_df_abs,
            abatement_cost_saf_only,
            abatement_cost_daccs_only,
            abatement_costs_hydrotreatment,
            abated_emissions,
        )

    # ---------------- Export results ----------------#

    folder_name = datetime.now().strftime("%Y-%m-%d")
    scenario_name = ""
    if CONTRAIL_AVOIDANCE["Fossil"] or CONTRAIL_AVOIDANCE["SAF"]:
        if CONTRAIL_AVOIDANCE["Fossil"] and CONTRAIL_AVOIDANCE["SAF"]:
            scenario_name += "CA_both"
        elif CONTRAIL_AVOIDANCE["Fossil"]:
            scenario_name += "CA_Fossil"
        elif CONTRAIL_AVOIDANCE["SAF"]:
            scenario_name += "CA_SAF"
        else:
            scenario_name += "CA_none"

    if HYDROTREATMENT["Fossil"] or HYDROTREATMENT["SAF"]:
        if CONTRAIL_AVOIDANCE["Fossil"] or CONTRAIL_AVOIDANCE["SAF"]:
            scenario_name += "_"
        if HYDROTREATMENT["Fossil"]:
            scenario_name += "HT_Fossil"
        elif HYDROTREATMENT["SAF"]:
            scenario_name += "HT_SAF"
        else:
            scenario_name += "HT_both"

        if abate_so2:
            scenario_name += "_SO2_y"
        else:
            scenario_name += "_SO2_n"

    if scenario_name == "":
        scenario_name = "Base Case"

    if sensitivities:
        save_path = f"outputs/{folder_name}/{sensitivity_name}"

    else:
        save_path = f"outputs/{folder_name}"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    functions.save_excel(
        gwp_baseline,
        f"{save_path}/gwp_baseline.xlsx",
        index=True,
        scenario_name=scenario_name[:31],
    )
    functions.save_excel(
        gwp_star,
        f"{save_path}/gwp_star.xlsx",
        index=True,
        scenario_name=scenario_name[:31],
    )

    for df_name, abated_emissions in abated_emissions_dict.items():
        abated_emissions = pd.DataFrame(abated_emissions, index=[0])

        functions.save_excel(
            abated_emissions,
            f"{save_path}/abated_emissions_{df_name}.xlsx",
            index=False,
            scenario_name=scenario_name[:31],
        )

    if CONTRAIL_AVOIDANCE["Fossil"] or CONTRAIL_AVOIDANCE["SAF"]:
        functions.save_excel(
            abated_emissions_contrail_avoidance,
            f"{save_path}/abated_emissions_contrail_avoidance.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )

    if HYDROTREATMENT["SAF"] or HYDROTREATMENT["Fossil"]:
        for df_name, df in abatement_costs_hydrotreatment.items():
            functions.save_excel(
                df,
                f"{save_path}/{df_name}_Hydrogen_abatement_costs_hydrotreatment.xlsx",
                index=True,
                scenario_name=scenario_name[:31],
            )

        for df_name, df in ht_abatement_dfs.items():
            functions.save_excel(
                df,
                f"{save_path}/{df_name}_Hydrogen_abated_emissions_hydrotreatment.xlsx",
                index=True,
                scenario_name=scenario_name[:31],
            )

    if CONTRAIL_AVOIDANCE["Fossil"] or CONTRAIL_AVOIDANCE["SAF"]:
        functions.save_excel(
            additional_abatement_costs_contrails_per_ton_eq,
            f"{save_path}/abatement_cost_contrails.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )


    # Abatement costs for SAF and DACCS. The values are ufloats, which are then mapped to the ranges as nominal value +/- std deviation.

    for key, value in abatement_costs_saf_per_ton_eq.items():
        value = pd.DataFrame(value, index=value.index)
        value.rename(columns={24: "Abatement Cost $ per tCO2eq"}, inplace=True)
        value["Abatement Cost Range"] = value.index.map(
            lambda x: value.loc[x, "Abatement Cost $ per tCO2eq"].n
            - value.loc[x, "Abatement Cost $ per tCO2eq"].s
            if x == "25%"
            else value.loc[x, "Abatement Cost $ per tCO2eq"].n
            if x == "50%"
            else value.loc[x, "Abatement Cost $ per tCO2eq"].n
            + value.loc[x, "Abatement Cost $ per tCO2eq"].s
            if x == "75%"
            else None
        )

        functions.save_excel(
            value,
            f"{save_path}/abatement_costs_saf_{key}.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )
    
    for key,value in abatement_costs_daccs_per_ton_eq.items():
        value = pd.DataFrame(value, index=value.index)
        value.rename(columns={24: "Abatement Cost $ per tCO2eq"}, inplace=True)
        try: 
            value["Abatement Cost Range"] = value.index.map(
                lambda x: value.loc[x, "Abatement Cost $ per tCO2eq"].n
                - value.loc[x, "Abatement Cost $ per tCO2eq"].s
                if x == "25%"
                else value.loc[x, "Abatement Cost $ per tCO2eq"].n
                if x == "50%"
                else value.loc[x, "Abatement Cost $ per tCO2eq"].n
                + value.loc[x, "Abatement Cost $ per tCO2eq"].s
                if x == "75%"
                else None
            )
        except AttributeError:
            value["Abatement Cost Range"] = value["Abatement Cost $ per tCO2eq"]

        functions.save_excel(
            value,
            f"{save_path}/abatement_costs_daccs_{key}.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )


    # Abated emissions by technology as absolute values (MtCO2eq) and percentage change from BAU

    functions.save_excel(
        abated_emissions_main_df_abs,
        f"{save_path}/abated_emissions_abs.xlsx",
        index=True,
        scenario_name=scenario_name[:31],
    )

    abated_emissions_main_df_abs = abated_emissions_main_df_abs * -1

    functions.save_excel(
        abated_emissions_main_df_pct,
        f"{save_path}/abated_emissions_pct.xlsx",
        index=True,
        scenario_name=scenario_name[:31],
    )

    for key, value in abatement_contributions.items():
        #
        functions.save_excel(
            value,
            f"{save_path}/abatement_contributions_{key}.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )

    for key, value in abatement_cost_saf_only.items():
        value = pd.DataFrame(value, index=value.index)
        value.rename(columns={24: "Abatement Cost $ per tCO2eq"}, inplace=True)
        value["Abatement Cost Range"] = value.index.map(
            lambda x: value.loc[x, "Abatement Cost $ per tCO2eq"].n
            - value.loc[x, "Abatement Cost $ per tCO2eq"].s
            if x == "25%"
            else value.loc[x, "Abatement Cost $ per tCO2eq"].n
            if x == "50%"
            else value.loc[x, "Abatement Cost $ per tCO2eq"].n
            + value.loc[x, "Abatement Cost $ per tCO2eq"].s
            if x == "75%"
            else None
        )
        functions.save_excel(
            value,
            f"{save_path}/abatement_cost_saf_only_{key}.xlsx",
            index=True,
            scenario_name=scenario_name[:31],
        )

    print(
        f"Simulation completed for scenario: {scenario_name}. Results exported to the outputs folder."
    )


# For sensitivity runs, determine sheets to be used as input

sensitivity_scenarios = {
    "Default": {
        "SAF": "Master Standardisation_SAF_Default.xlsx",
        "DACCS": "Master Standardisation DACCS.xlsx",
    },

    "CA": {
        "SAF": "Master Standardisation_SAF_Default.xlsx",
        "DACCS": "Master Standardisation DACCS.xlsx",
    },

    "LE": {
        "SAF": "Master Standardisation_SAF_LE.xlsx",
        "DACCS": "Master Standardisation DACCS_LE.xlsx",
    },
    "HF": {
        "SAF": "Master Standardisation_SAF_HF.xlsx",
        "DACCS": "Master Standardisation DACCS.xlsx",
    },
    "HF_LE": {
        "SAF": "Master Standardisation_SAF_HF_LE.xlsx",
        "DACCS": "Master Standardisation DACCS_LE.xlsx",
    },
    "HF_LE_CA": {
        "SAF": "Master Standardisation_SAF_HF_LE.xlsx",
        "DACCS": "Master Standardisation DACCS_LE.xlsx",
    },
    "LE_CA": {
        "SAF": "Master Standardisation_SAF_LE.xlsx",
        "DACCS": "Master Standardisation DACCS_LE.xlsx",
    },
    "HF_CA": {
        "SAF": "Master Standardisation_SAF_HF.xlsx",
        "DACCS": "Master Standardisation DACCS.xlsx",
    }
}


contrail_avoidance_options = [
    {"Fossil": False, "SAF": False},
    {"Fossil": True, "SAF": True},
]
hydrotreatment_options = [
    {"Fossil": False, "SAF": False},
    {"Fossil": True, "SAF": False},
]
so2_abatement_options = [True, False]


if RUN_SENSITIVITES:
    print("Running Sensitivities...\n")
    for sensitivity, input_names in sensitivity_scenarios.items():
        print("Running sensitivity: ", sensitivity)
        for contrail_avoidance, hydrotreatment, abate_so2 in itertools.product(
            contrail_avoidance_options, hydrotreatment_options, so2_abatement_options
        ):
            if abate_so2 and hydrotreatment == {"Fossil": False, "SAF": False}:
                continue
            main(
                contrail_avoidance,
                hydrotreatment,
                abate_so2,
                input_names["SAF"],
                input_names["DACCS"],
                sensitivities=True,
                sensitivity_name=sensitivity,
            )
            # Sleep 2 seconds to avoid conflicting save files
            time.sleep(2)
else:
    for contrail_avoidance, hydrotreatment, abate_so2 in itertools.product(
        contrail_avoidance_options, hydrotreatment_options, so2_abatement_options
    ):
        if abate_so2 and hydrotreatment == {"Fossil": False, "SAF": False}:
            continue
        main(
            contrail_avoidance,
            hydrotreatment,
            abate_so2,
            "Master Standardisation_SAF_Default.xlsx",
            "Master Standardisation DACCS.xlsx",
            sensitivities=False,
            sensitivity_name="Default",
        )
        # Sleep 2 seconds to avoid conflicting save files
        time.sleep(2)

print ("All simulations completed.")
