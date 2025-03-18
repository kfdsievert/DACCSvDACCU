import pandas as pd
import numpy as np
from uncertainties import ufloat, nominal_value
from fair.forward import fair_scm
from fair.inverse import inverse_fair_scm
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from typing import List, Tuple
global EUR_USD
EUR_USD = 1.12 # 1 EUR = 1.12 USD, FRED (2024)


def load_input_abatement_cost(file_path, tech):
    """Loads data on abatement costs from master excel sheet and formulates into a dataframe with min, 25%, median, 75%, and max values for each technology.

    Params:
    - file_path: Path to the file containing abatement cost data from Master Standardization sheets on SAF and DACCS carried out for this study by Katrin Sievert and Yash Dubey in 2024.
    - tech: Technology for which abatement cost data is to be loaded. Valid options are DACCS and SAF.

    Returns:
    - DataFrame with Interquartile range of interpolated yearly abatement costs for the technology specified in 2025 and 2050.
    - DataFrame with residual emissions for SAF technology. Only valid for SAF.

    """

    # Flag to return residual emissions. Only valid for SAF

    return_residual_emissions = False

    # Final cost column varies by technology
    if tech not in ["DACCS", "SAF"]:
        raise ValueError("Technology not recognized. Please enter either DACCS or SAF.")

    if tech == "DACCS":
        cost_col = "Fully Harmonized NET REMOVED COST (incl T&S"
        skiprows = 1
        year_col = "Year of Assumptions in Study"
        filter_rows = ["Young et al. 2023", "Sievert et al. 2024", "Fasihi et al. 2019", "Pett-Ridge et al. 2024", "Keith et al. 2018"]
    elif tech == "SAF":
        cost_col = "Fully Harmonized"
        skiprows = 0
        year_col = "Year of Cost"
        filter_rows = ["Brazzola et al. ","Gray et al.","Marchese et.al. ","Martin et. al.","Moretti et al.","Peacock et. al.",
                       "Schmidt et. al.","Seymour et al.","Sherwin"]
        return_residual_emissions = True

    # First row is headers and is skipped
    input_abatement_cost = pd.read_excel(
        file_path, sheet_name="Standardization Results", skiprows=skiprows, index_col=0
    )

    if tech == "SAF":
        input_abatement_cost_low = pd.read_excel(
            file_path, sheet_name="Low CO2", skiprows=skiprows, index_col=0
        )
        input_abatement_cost_low = input_abatement_cost_low.loc[input_abatement_cost_low.index.isin(filter_rows),:]
        input_abatement_cost_high = pd.read_excel(
            file_path, sheet_name="High CO2", skiprows=skiprows, index_col=0
        )

    # Filter studies with both current (<=2025) and future (2050) costs. The lambda function is used with the filter here.
    input_abatement_cost = input_abatement_cost.groupby(
        input_abatement_cost.index
    ).filter(lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050))
    if tech == "SAF":
        input_abatement_cost_low = input_abatement_cost_low.groupby(
            input_abatement_cost_low.index
        ).filter(lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050))
        input_abatement_cost_high = input_abatement_cost_high.groupby(
            input_abatement_cost_high.index
        ).filter(lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050))

    # Filter data for short- and long-term costs
    input_abatement_cost_short = input_abatement_cost[
        input_abatement_cost[year_col] <= 2025
    ]
    input_abatement_cost_long = input_abatement_cost[
        input_abatement_cost[year_col] == 2050
    ]

    if tech == "SAF":
        input_abatement_cost_short_low = input_abatement_cost_low[
            input_abatement_cost_low[year_col] <= 2025
        ]
        input_abatement_cost_long_low = input_abatement_cost_low[
            input_abatement_cost_low[year_col] == 2050
        ]
        input_abatement_cost_short_high = input_abatement_cost_high[
            input_abatement_cost_high[year_col] <= 2025
        ]
        input_abatement_cost_long_high = input_abatement_cost_high[
            input_abatement_cost_high[year_col] == 2050
        ]

    # Descriptive statistics
    input_abatement_cost_short = input_abatement_cost_short[cost_col].describe()
    input_abatement_cost_long = input_abatement_cost_long[cost_col].describe()

    # For SAF, descriptive statistics are taken from High (75th percentile) and Low(25th percentile) CO2 prices
    if tech == "SAF":
        input_abatement_cost_short_low = input_abatement_cost_short_low[
            cost_col
        ].describe()
        input_abatement_cost_long_low = input_abatement_cost_long_low[
            cost_col
        ].describe()
        input_abatement_cost_short_high = input_abatement_cost_short_high[
            cost_col
        ].describe()
        input_abatement_cost_long_high = input_abatement_cost_long_high[
            cost_col
        ].describe()

    # Generate yearly abatement cost interpolations
    if tech == "DACCS":
        yearly_abatement_cost = pd.DataFrame()
        yearly_abatement_cost["50%"] = np.linspace(
            input_abatement_cost_short["50%"], input_abatement_cost_long["50%"], 25
        )
        yearly_abatement_cost["25%"] = np.linspace(
            input_abatement_cost_short["25%"], input_abatement_cost_long["25%"], 25
        )
        yearly_abatement_cost["75%"] = np.linspace(
            input_abatement_cost_short["75%"], input_abatement_cost_long["75%"], 25
        )

    # For SAF, the minimum value is the 25th percentile of results for low CO2 prices and the maximum value is the 75th percentile of results for high CO2 prices.
    elif tech == "SAF":
        yearly_abatement_cost = pd.DataFrame()
        yearly_abatement_cost["50%"] = np.linspace(
            input_abatement_cost_short["50%"], input_abatement_cost_long["50%"], 25
        )
        yearly_abatement_cost["25%"] = np.linspace(
            input_abatement_cost_short_low["25%"],
            input_abatement_cost_long_low["25%"],
            25,
        )
        yearly_abatement_cost["75%"] = np.linspace(
            input_abatement_cost_short_high["75%"],
            input_abatement_cost_long_high["75%"],
            25,
        )

    yearly_abatement_cost.to_excel(f"outputs/abatement_cost_curve_{tech}.xlsx")

    # Only activated for SAF, residual emissions are abated using DACCS.
    if return_residual_emissions:
        residual_emissions = input_abatement_cost.loc[
            :, ["Residual Emissions (gCO2eq/L fuel)", "Year of Cost"]
        ]

        return yearly_abatement_cost, residual_emissions

    return yearly_abatement_cost


def load_base_inputs(file_path):
    """Loads base inputs from an excel file and returns a dataframe.

    Params:
    - file_path: Path to the file containing base inputs from Brazzola et. al. 2024

    Returns:
    - DataFrame with base inputs for aviation demand in EJ and million KMs as well as SAF progression curve from Brazzola et. al. 2024

    """

    base_inputs = pd.read_csv(file_path, index_col=0)

    # Select all rows but only the first two columns
    base_inputs = base_inputs.iloc[:, :3]

    return base_inputs


def load_lee(file_path):
    """Loads data from Lee et al. 2021 for aviation emissions.

    Params:
    - file_path: Path to the file containing data from Lee et al. 2021

    Returns:
    - DataFrame with data on ERFs and historic emissions from aviation as in Lee et al. 2021

    """

    lee = pd.read_csv(file_path, index_col=0)

    return lee


def generate_aviation_demand(
    df_input, DEMAND_GROWTH_RATE, ANNUAL_EFFICIENCY_CHANGE, N_YEARS
):
    """
    Generate future aviation demand based on historical data and future projections using linear demand growth rate and efficiency improvements.

    Params:
    - df_input: Input DataFrame with base demand values
    - DEMAND_GROWTH_RATE: Annual demand growth rate
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - N_YEARS: Number of years to project

    Returns:
    - DataFrame with projected aviation demand for each year from 2025 to N_YEARS years in the future.

    """

    # Validate input
    if 2025 not in df_input.index:
        raise ValueError("Input DataFrame must contain data for the year 2025")

    # Initial demand for fuel in exajoules
    initial_demand_ej = df_input.loc[2025, "DEMAND_EJ_BASE"]
    # Initial aviation demand in million kilometres
    initial_demand_km = df_input.loc[2025, "DEMAND_M_KM_BASE"]

    # Vectors for demand growth and efficiency improvement
    demand_growth_vector = (1 + DEMAND_GROWTH_RATE) ** np.arange(N_YEARS + 1)
    efficiency_growth_vector = (1 - ANNUAL_EFFICIENCY_CHANGE) ** np.arange(N_YEARS + 1)

    # Fuel demand is affected by both growth in demand and efficiency improvements
    demand_ej_vector = (
        initial_demand_ej * demand_growth_vector * efficiency_growth_vector
    )
    # Kilometre demand is only affected by growth in demand
    demand_km_vector = initial_demand_km * demand_growth_vector

    # Create output DataFrame
    df_output = pd.DataFrame(
        {"DEMAND_EJ": demand_ej_vector, "DEMAND_M_KM": demand_km_vector},
        index=range(2025, 2025 + N_YEARS + 1),
    )

    return df_output


def generate_equivalence_gwp(
    demand_df,
    base_inputs,
    year,
    emission_factors,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    CONTRAIL_AVOIDANCE,
    REROUTING_FUEL_PENALTY,
    metric="GWP100",
):
    """
    Calculates Equivalent CO2 emissions from GWP metrics as in Lee et. al. 2021

    Params:
    - demand_df: DataFrame with projected aviation demand
    - base_inputs: DataFrame with base inputs for progression curve of SAF from Brazzola et. al. 2024
    - year: Year for which GWP values are to be calculated
    - emission_factors: Dictionary with multipliers for emissions addopted from Brazzola et. al. 2024 or calculated directly
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - N_YEARS: Number of years to project
    - metric: GWP metric to use. Default is GWP100

    Returns:
    - DataFrame with equivalent CO2 emissions equivalent in Mt CO2 (Tg CO2) for each GWP metric for net NOx, CO2, and Contrail Cirrus and C-C cloud formation in BAU and SAF scenarios.

    """

    # GWP metrics derived from Table 5 of Lee et. al. 2021: https://doi.org/10.1016/j.atmosenv.2020.117834
    GWP_metrics = {
        "GWP100": {
            "CO2": 1,
            "netNOx": 114,
            "Contrail Cirrus and C-C": 11,  # km basis
            "BC": 1166,
            "SO2": -226,
            "H2O": 0.06,
        },
        "GWP20": {
            "CO2": 1,
            "netNOx": 619,
            "Contrail Cirrus and C-C": 39,  # km basis
            "BC": 4288,
            "SO2": -832,
            "H2O": 0.22,
        },
    }

    # Values below are obtained from the Time Series sheet of the Supplmentary Material of Lee et. al. 2021

    # SAF deployment in selected year
    saf_deployed_current = base_inputs.loc[year, "PROGRESSION_CURVE"]
    fossil_share_current = 1 - saf_deployed_current

    dist_net_2018 = 61333  # Million kms in 2018 from Lee et. al. 2021
    co2_net_2018 = 1034  # Tg CO2 in 2018 from Lee et. al. 2021 (1Tg = 1Mt)
    nox_net_2018 = 1.43  # Tg N in 2018 from Lee et. al. 2021
    so2_net_2018 = 0.3729  # Tg SO2 in 2018 from Lee et. al. 2021
    bc_net_2018 = 0.0093  # Tg BC in 2018 from Lee et. al. 2021
    h2o_net_2018 = 382.6  # Tg H2O in 2018 from Lee et. al. 2021
    contrail_cc_dist_2018 = (
        6.13 * 10**10
    )  # Contrail Cirrus and C-C cloud km in 2018 from Lee et. al. 2021

    dist_net_year = demand_df.loc[
        year, "DEMAND_M_KM"
    ]  # Total distance covered in given year in million kms
    co2_net_year = (
        co2_net_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # CO2 emissions in given year in Mt corrected for demand and efficiency changes
    nox_net_year = (
        nox_net_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # NOx emissions in given year in Mt corrected for demand and efficiency changes

    so2_net_year = (
        so2_net_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # SO2 emissions in given year in Mt corrected for demand and efficiency changes

    bc_net_year = (
        bc_net_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # BC emissions in given year in Mt corrected for demand and efficiency changes

    h2o_net_year = (
        h2o_net_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # H2O emissions in given year in Mt corrected for demand and efficiency changes

    contrail_cc_dist_year = (
        contrail_cc_dist_2018
        * (dist_net_year / dist_net_2018)
        * (1 - ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS)
    )  # Contrail Cirrus and C-C distance in km in given year corrected for demand and efficiency changes

    # Formulae below are adopted from the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)

    # BAU scenario
    co2_equiv_bau = (
        co2_net_year
        * GWP_metrics[metric]["CO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["Fossil"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied
    nox_equiv_bau = (
        nox_net_year
        * GWP_metrics[metric]["netNOx"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["Fossil"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied
    contrail_cc_equiv_bau = (
        (contrail_cc_dist_year / 10**9)
        * GWP_metrics[metric]["Contrail Cirrus and C-C"]
        * emission_factors["Fossil"]["Contrail Cirrus and C-C"]
    )

    so2_equiv_bau = (
        so2_net_year
        * GWP_metrics[metric]["SO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["Fossil"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    bc_equiv_bau = (
        bc_net_year
        * GWP_metrics[metric]["BC"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["Fossil"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    h2o_equiv_bau = (
        h2o_net_year
        * GWP_metrics[metric]["H2O"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["Fossil"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    # SAF scenario Fossil component
    co2_equiv_fossil = (
        co2_net_year
        * GWP_metrics[metric]["CO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
        * fossil_share_current
    )
    nox_equiv_fossil = (
        nox_net_year
        * GWP_metrics[metric]["netNOx"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
        * fossil_share_current
    )

    so2_equiv_fossil = (
        so2_net_year
        * GWP_metrics[metric]["SO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
        * fossil_share_current
    )

    bc_equiv_fossil = (
        bc_net_year
        * GWP_metrics[metric]["BC"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
        * fossil_share_current
    )

    h2o_equiv_fossil = (
        h2o_net_year
        * GWP_metrics[metric]["H2O"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
        * fossil_share_current
    )

    contrail_cc_equiv_fossil = contrail_cc_equiv_bau * fossil_share_current

    # SAF scenario SAF component
    co2_equiv_saf = (
        co2_equiv_bau
        * saf_deployed_current
        * emission_factors["SAF"]["CO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied
    nox_equiv_saf = (
        nox_equiv_bau
        * saf_deployed_current
        * emission_factors["SAF"]["netNOx"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    so2_equiv_saf = (
        so2_equiv_bau
        * saf_deployed_current
        * emission_factors["SAF"]["SO2"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    bc_equiv_saf = (
        bc_equiv_bau
        * saf_deployed_current
        * emission_factors["SAF"]["BC"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    h2o_equiv_saf = (
        h2o_equiv_bau
        * saf_deployed_current
        * emission_factors["SAF"]["H2O"]
        * (1 + REROUTING_FUEL_PENALTY * CONTRAIL_AVOIDANCE["SAF"])
    )  # Add fuel penalty for rerouting if contrail avoidance is applied

    contrail_cc_equiv_saf = (
        contrail_cc_equiv_bau
        * saf_deployed_current
        * (
            emission_factors["SAF"]["Contrail Cirrus and C-C"]
            / emission_factors["Fossil"]["Contrail Cirrus and C-C"]
        )
    )

    # Total CO2 equivalent emissions SAF scenario
    co2_equiv_total = co2_equiv_fossil + co2_equiv_saf
    nox_equiv_total = nox_equiv_fossil + nox_equiv_saf
    so2_equiv_total = so2_equiv_fossil + so2_equiv_saf
    bc_equiv_total = bc_equiv_fossil + bc_equiv_saf
    h2o_equiv_total = h2o_equiv_fossil + h2o_equiv_saf
    contrail_cc_equiv_total = contrail_cc_equiv_fossil + contrail_cc_equiv_saf

    df_equivalents_saf = pd.DataFrame(
        {
            "CO2": co2_equiv_total,
            "netNOx": nox_equiv_total,
            "SO2": so2_equiv_total,
            "BC": bc_equiv_total,
            "H2O": h2o_equiv_total,
            "Contrail Cirrus and C-C": contrail_cc_equiv_total,
        },
        index=[f"{metric} SAF"],
    )

    df_equivalents_bau = pd.DataFrame(
        {
            "CO2": co2_equiv_bau,
            "netNOx": nox_equiv_bau,
            "SO2": so2_equiv_bau,
            "BC": bc_equiv_bau,
            "H2O": h2o_equiv_bau,
            "Contrail Cirrus and C-C": contrail_cc_equiv_bau,
        },
        index=[f"{metric} BAU"],
    )

    df_equivalents = pd.concat([df_equivalents_bau, df_equivalents_saf], axis=0)

    return df_equivalents


def make_CO2aviation_hist():
    """
    Makes CO2 emissions from aviation from 1940-2018 from concentrations reported in Lee et al. 2021
    :return: historical aviation CO2 emissions and forcing due to CO2 emissions
    """
    CO2_C_1940_2018 = np.array(
        [
            0.0042,
            0.0078,
            0.0113,
            0.0149,
            0.0187,
            0.0227,
            0.0269,
            0.0314,
            0.0362,
            0.0413,
            0.0468,
            0.0527,
            0.0590,
            0.0658,
            0.0731,
            0.0810,
            0.0894,
            0.0986,
            0.1085,
            0.1192,
            0.1308,
            0.1437,
            0.1579,
            0.1724,
            0.1870,
            0.2024,
            0.2193,
            0.2409,
            0.2657,
            0.2907,
            0.3143,
            0.3386,
            0.3647,
            0.3916,
            0.4162,
            0.4404,
            0.4643,
            0.4908,
            0.5185,
            0.5475,
            0.5762,
            0.6038,
            0.6319,
            0.6598,
            0.6898,
            0.7213,
            0.7558,
            0.7924,
            0.8315,
            0.8725,
            0.9130,
            0.9507,
            0.9872,
            1.0216,
            1.0596,
            1.0997,
            1.1434,
            1.1892,
            1.2361,
            1.2853,
            1.3382,
            1.3869,
            1.4357,
            1.4843,
            1.5381,
            1.5956,
            1.6530,
            1.7123,
            1.7704,
            1.8227,
            1.8803,
            1.9401,
            2.0004,
            2.0633,
            2.1291,
            2.2002,
            2.2737,
            2.3496,
            2.4281,
        ]
    )  # CO2 concentrations in ppm above 278 ppm (pre-industrial average)
    CO2_C_1940_2018 += 278  # Add to get actual atmospheric effect
    E1, F1, T1 = inverse_fair_scm(C=CO2_C_1940_2018, rt=0)
    return E1, F1


def future_aviation_emissions(
    base_inputs, ANNUAL_EFFICIENCY_CHANGE, DEMAND_GROWTH_RATE, tech, emission_factors
):
    """
    Function to generate future CO2 emissions from aviation
    """

    co2_net_2018 = 1034  # Tg CO2 in 2018 from Lee et. al. 2021 (1Tg = 1Mt)
    nox_net_2018 = 1.43  # Tg NOx in 2018 from Lee et. al. 2021
    bc_net_2018 = 0.0093  # Tg BC in 2018 from Lee et. al. 2021
    so2_net_2018 = 0.3729  # Tg SO2 in 2018 from Lee et. al. 2021
    h2o_net_2018 = 382.6  # Tg H2O in 2018 from Lee et. al. 2021
    contrail_net_2018 = 6.13e10  # km in 2018 from Lee et. al. 2021
    n_years = 2050 - 2018

    demand_growth_vector = (1 + DEMAND_GROWTH_RATE) ** np.arange(n_years + 1)
    efficiency_growth_vector = (1 - ANNUAL_EFFICIENCY_CHANGE) ** np.arange(n_years + 1)

    co2_emissions = np.zeros(n_years)
    nox_emissions = np.zeros(n_years)
    bc_emissions = np.zeros(n_years)
    so2_emissions = np.zeros(n_years)
    h2o_emissions = np.zeros(n_years)
    contrail_emissions = np.zeros(n_years)

    saf_share = base_inputs["PROGRESSION_CURVE"].loc["2018" : str(2018 + n_years)]
    fossil_share = 1 - saf_share

    if tech == "Fossil":
        co2_emissions = co2_net_2018 * demand_growth_vector * efficiency_growth_vector
        nox_emissions = nox_net_2018 * demand_growth_vector * efficiency_growth_vector
        bc_emissions = bc_net_2018 * demand_growth_vector * efficiency_growth_vector
        so2_emissions = so2_net_2018 * demand_growth_vector * efficiency_growth_vector
        h2o_emissions = h2o_net_2018 * demand_growth_vector * efficiency_growth_vector
        contrail_emissions = (
            contrail_net_2018
            * demand_growth_vector
            * efficiency_growth_vector
            * emission_factors["Fossil"]["Contrail Cirrus and C-C"]
        )

    elif tech == "SAF":
        co2_emissions = (
            co2_net_2018
            * demand_growth_vector
            * efficiency_growth_vector
            * (fossil_share + saf_share * emission_factors["SAF"]["CO2"])
        )
        nox_emissions = (
            nox_net_2018
            * demand_growth_vector
            * efficiency_growth_vector
            * (fossil_share + saf_share * emission_factors["SAF"]["netNOx"])
        )
        bc_emissions = bc_net_2018 * demand_growth_vector * efficiency_growth_vector
        so2_emissions = so2_net_2018 * demand_growth_vector * efficiency_growth_vector
        h2o_emissions = h2o_net_2018 * demand_growth_vector * efficiency_growth_vector
        contrail_emissions = (
            contrail_net_2018
            * demand_growth_vector
            * efficiency_growth_vector
            * (
                fossil_share
                + saf_share * emission_factors["SAF"]["Contrail Cirrus and C-C"]
            )
        )

    df_emissions = pd.DataFrame(
        index=np.arange(2018, 2051),
        columns=["CO2", "NOx", "BC", "SO2", "H2O", "Contrail"],
        data=np.array(
            [
                co2_emissions,
                nox_emissions,
                bc_emissions,
                so2_emissions,
                h2o_emissions,
                contrail_emissions,
            ]
        ).T,
    )

    return df_emissions


def calc_ERF_CO2(E, start_year=1990):
    """
    Calculate the ERF of CO2
    :param E: dataframe with future emissions
    :param start_year: start date of future emissions
    :return: forcing of CO2 emissions from start date
    """
    E_CO2_hist = make_CO2aviation_hist()[0]
    E_GtC = E.loc[str(start_year) :, "CO2"].values / (3.677 * 10**3)
    E_input = np.concatenate((E_CO2_hist[: start_year - 1940], E_GtC), axis=0)
    C_CO2, F_CO2, T_CO2 = fair_scm(emissions=E_input, useMultigas=False)
    return F_CO2[start_year - 1940 :] * 10**3  # in mW/m2


def calculate_ERF(df, e_factors):
    """
    Function to calculate ERF from sensitivity to emissions reported in Lee et al. 2021
    :param df: dataframe with emissions
    :param e_factors: sensitivity to emissions reported in Lee et al. 2021
    :return: ERF of each species in each year
    """
    # Index is datetime 2018 - 2050
    index = pd.date_range(start="2018", end="2051", freq="Y")
    columns = e_factors.keys()
    # sensitivity to emissions for other species + uncertainties (as in Lee et al. 2021)
    erf_data = np.array(
        [
            ufloat(34.44, 9.90),
            ufloat(-18.60, 6.90),
            ufloat(-9.35, 3.40),
            ufloat(-2.80, 1.00),
            ufloat(5.46, 8.10),
            ufloat(100.67, 165.50),
            ufloat(-19.91, 16.00),
            ufloat(0.0052, 0.0026),
            ufloat(9.36 * 10 ** (-10), 6.57 * 10 ** (-10)),
        ]
    )
    erf_factors = pd.DataFrame(index=columns, columns=["ERF factors"], data=erf_data)
    ERF_df = pd.DataFrame(index=index, columns=columns)
    ERF_df = ERF_df.fillna(0.0)
    ERF_df["CO2"] = calc_ERF_CO2(df, start_year=index[0].year)
    ERF_df["O3 short"] = df["NOx"].values * erf_factors.loc["O3 short", :].values
    ERF_df["CH4"] = df["NOx"].values * erf_factors.loc["CH4", :].values
    ERF_df["O3 long"] = df["NOx"].values * erf_factors.loc["O3 long", :].values
    ERF_df["SWV"] = df["NOx"].values * erf_factors.loc["SWV", :].values
    ERF_df["netNOx"] = df["NOx"].values * erf_factors.loc["netNOx", :].values
    ERF_df["BC"] = df["BC"].values * erf_factors.loc["BC", :].values
    ERF_df["SO4"] = df["SO2"].values * erf_factors.loc["SO4", :].values
    ERF_df["H2O"] = df["H2O"].values * erf_factors.loc["H2O", :].values
    ERF_df["Contrail Cirrus and C-C"] = (
        df["Contrail"].values * erf_factors.loc["Contrail Cirrus and C-C", :].values
    )
    ERF_df["non-CO2"] = ERF_df.loc[
        :, ["netNOx", "BC", "SO4", "H2O", "Contrail Cirrus and C-C"]
    ].sum(axis=1)
    ERF_df["Tot"] = ERF_df.loc[
        :, ["netNOx", "BC", "SO4", "H2O", "Contrail Cirrus and C-C", "CO2"]
    ].sum(axis=1)
    return ERF_df


def generate_equivalence_gwp_star(
    erf_df_fossil, erf_df_saf, base_inputs, year, emission_factors, dt
):
    """
    Generate GWP100* values for NOx and C-C based on ERF values.

    Params:
    - erf_df: DataFrame with projected ERF values for NOx and C-C
    - base_inputs: DataFrame with base inputs for progression curve of SAF from Brazzola et. al. 2024
    - year: Year for which GWP* values are to be calculated
    - emission_factors: Dictionary with multipliers for SAF emissions addopted from Brazzola et. al. 2024
    - dt: Time span between emission pulses in GWP*. Default is 20 years.

    Returns:
    - DataFrame with GWP* values for NOx and C-C in Tg CO2 eq. for SAF and BAU scenarios.

    """

    H = 100  # 100 year time span. This is the default value for GWP100* in the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)
    AGWP_CO2 = 0.088  # Absolute GWP of CO2 in mWm-2 yr Mt-1 from Lee et. al. 2021 Supplementary Material AGWP-CO2 sheet

    erf_df_fossil.index = erf_df_fossil.index.year
    erf_df_saf.index = erf_df_saf.index.year

    # ERF values for BAU scenario - Current year
    nox_erf_current_bau = erf_df_fossil.loc[year, "netNOx"]
    so2_erf_current_bau = erf_df_fossil.loc[year, "SO4"]
    bc_erf_current_bau = erf_df_fossil.loc[year, "BC"]
    h2o_erf_current_bau = erf_df_fossil.loc[year, "H2O"]
    cc_erf_current_bau = erf_df_fossil.loc[year, "Contrail Cirrus and C-C"]

    # ERF values for BAU scenario - "DT" years ago.
    nox_erf_past_bau = erf_df_fossil.loc[year - dt, "netNOx"]
    so2_erf_past_bau = erf_df_fossil.loc[year - dt, "SO4"]
    bc_erf_past_bau = erf_df_fossil.loc[year - dt, "BC"]
    h2o_erf_past_bau = erf_df_fossil.loc[year - dt, "H2O"]
    cc_erf_past_bau = erf_df_fossil.loc[year - dt, "Contrail Cirrus and C-C"]

    # ERF values for SAF scenario - Current year
    nox_erf_current_saf = erf_df_saf.loc[year, "netNOx"] * emission_factors["netNOx"]
    so2_erf_current_saf = erf_df_saf.loc[year, "SO4"] * emission_factors["SO2"]
    bc_erf_current_saf = erf_df_saf.loc[year, "BC"] * emission_factors["BC"]
    h2o_erf_current_saf = erf_df_saf.loc[year, "H2O"] * emission_factors["H2O"]
    cc_erf_current_saf = (
        erf_df_saf.loc[year, "Contrail Cirrus and C-C"]
        * emission_factors["Contrail Cirrus and C-C"]
    )

    # ERF values for SAF scenario - "DT" years ago.
    nox_erf_past_saf = erf_df_saf.loc[year - dt, "netNOx"] * emission_factors["netNOx"]
    so2_erf_past_saf = erf_df_saf.loc[year - dt, "SO4"] * emission_factors["SO2"]
    bc_erf_past_saf = erf_df_saf.loc[year - dt, "BC"] * emission_factors["BC"]
    h2o_erf_past_saf = erf_df_saf.loc[year - dt, "H2O"] * emission_factors["H2O"]
    cc_erf_past_saf = (
        erf_df_saf.loc[year - dt, "Contrail Cirrus and C-C"]
        * emission_factors["Contrail Cirrus and C-C"]
    )

    # Calulate GWP* values in Tg CO2 eq. for NOx and Contrail Cirrus and C-C - BAU scenario
    nox_gwp_star_bau = ((nox_erf_current_bau - nox_erf_past_bau) / dt) * (
        H / AGWP_CO2
    )  # Formula for GWP* calculation adopted from Brazzola et. al. 2022
    so2_gwp_star_bau = ((so2_erf_current_bau - so2_erf_past_bau) / dt) * (H / AGWP_CO2)
    bc_gwp_star_bau = ((bc_erf_current_bau - bc_erf_past_bau) / dt) * (H / AGWP_CO2)
    h2o_gwp_star_bau = ((h2o_erf_current_bau - h2o_erf_past_bau) / dt) * (H / AGWP_CO2)
    cc_gwp_star_bau = ((cc_erf_current_bau - cc_erf_past_bau) / dt) * (H / AGWP_CO2)

    # Calulate GWP* values in Tg CO2 eq. for NOx and Contrail Cirrus and C-C - SAF scenario
    nox_gwp_star_saf = ((nox_erf_current_saf - nox_erf_past_saf) / dt) * (
        H / AGWP_CO2
    )  # Formula for GWP* calculation adopted from Brazzola et. al. 2022
    so2_gwp_star_saf = ((so2_erf_current_saf - so2_erf_past_saf) / dt) * (H / AGWP_CO2)
    bc_gwp_star_saf = ((bc_erf_current_saf - bc_erf_past_saf) / dt) * (H / AGWP_CO2)
    h2o_gwp_star_saf = ((h2o_erf_current_saf - h2o_erf_past_saf) / dt) * (H / AGWP_CO2)
    cc_gwp_star_saf = ((cc_erf_current_saf - cc_erf_past_saf) / dt) * (H / AGWP_CO2)

    gwp_star_saf_df = pd.DataFrame(
        {
            "NOx": nox_gwp_star_saf,
            "SO2": so2_gwp_star_saf,
            "BC": bc_gwp_star_saf,
            "H2O": h2o_gwp_star_saf,
            "Contrail Cirrus and C-C": cc_gwp_star_saf,
            "CO2": 0,
        },
        index=["GWP* SAF"],
    )

    gwp_star_bau_df = pd.DataFrame(
        {
            "NOx": nox_gwp_star_bau,
            "SO2": so2_gwp_star_bau,
            "BC": bc_gwp_star_bau,
            "H2O": h2o_gwp_star_bau,
            "Contrail Cirrus and C-C": cc_gwp_star_bau,
            "CO2": 0,
        },
        index=["GWP* BAU"],
    )

    gwp_star_df = pd.concat([gwp_star_saf_df, gwp_star_bau_df], axis=0)

    return gwp_star_df


def calculate_abatement_cost_saf(abatement_cost_saf, gwp_df, year, SIMULATION_START):
    """
    Function to calculate total abatement cost for aviation using SAF.

    This cost is calculated using the total CO2 emissions and the abatement cost of SAF. This cost does NOT account for non-CO2 emissions being abated.

    Params:
    - abatement_cost_saf: DataFrame with abatement cost data for SAF
    - gwp_df: DataFrame with GWP values for CO2, NOx, and C-C
    - year: Year for which abatement cost is to be calculated
    - SIMULATION_START: Start year of simulation
    """

    # Total CO2 emissions in 2050 (same for GWP and GWP*)
    total_co2 = gwp_df.loc["GWP100 BAU", "CO2"] * 10**6  # In T of CO2

    # Abatement cost for SAF in 2050 (same for GWP and GWP*)
    abatement_cost = abatement_cost_saf.loc[year - SIMULATION_START - 1] * total_co2

    return abatement_cost


def calculate_residual_abatement_saf(
    residual_emissions,
    df_demand,
    abatement_curve_daccs,
    year,
    MJ_PER_L,
    SIMULATION_START,
):
    """
    Function to calculate average abatement cost for residual emissions from SAF using DACCS.

    This cost is calculated using the residual emissions from SAF and the abatement cost of DACCS.

    Params:
    - residual_emissions: Array of residual emissions in gCO2/L of fuel
    - df_demand: DataFrame with projected aviation demand
    - abatement_curve_daccs: DataFrame with abatement cost data for DACCS
    - year: Year for which abatement cost is to be calculated
    - MJ_PER_L: Standard volumetric energy density of SAF
    - SIMULATION_START: Start year of simulation

    Returns:
    - Average abatement cost for residual emissions from SAF in 2050
    """

    residual_emissions_l = np.mean(
        residual_emissions.loc[
            residual_emissions["Year of Cost"] == year,
            "Residual Emissions (gCO2eq/L fuel)",
        ]
    )  # Residual emissions in gCO2/L of fuel
    residual_emissions_mj = (
        residual_emissions_l / MJ_PER_L
    )  # Residual emissions in gCO2/MJ of fuel
    residual_emissions_ej = (
        residual_emissions_mj * 10**12
    )  # Residual emissions in gCO2/EJ of fuel

    # Total Residual Emissions from SAF in 2050:
    residual_emissions_total = (
        residual_emissions_ej * df_demand.loc[year, "DEMAND_EJ"]
    )  # in g of CO2
    residual_emissions_total = residual_emissions_total / 10**9  # in T of CO2

    # Calculate abatement cost for residual emissions using DACCS
    abatement_cost_residual = (
        abatement_curve_daccs.loc[year - SIMULATION_START - 1]
        * residual_emissions_total
    )

    return abatement_cost_residual


def calculate_total_abatement_cost_saf_non_co2(total_abatement_cost_saf, gwp, gwp_star):
    """Function to calculate the abatement cost of SAF when non-CO2 effects are included

    Params:
    - total_abatement_cost_saf: Total abatement cost of SAF in 2050 in $
    - gwp: DataFrame with GWP20 and GWP100 values for CO2, NOx, and C-C in BAU and SAF scenarios
    - gwp_star: DataFrame with GWP* values for CO2, NOx, and C-C in BAU and SAF scenarios

    Returns:
    - Dictionary with abatement costs for GWP100, GWP20, and GWP* in $/ton of CO2 eq.
    """

    # Calculate abated emissions for each GWP metric. This is done by taking the difference between SAF and BAU scenarios for each GWP metric and multiplying by 10^6 to convert to T of CO2 eq.
    abated_emissions_gwp_100 = (
        gwp.loc["GWP100 BAU", "Total"] - gwp.loc["GWP100 SAF", "Total"]
    ) * 10**6  # in T of CO2 eq.
    abated_emissions_gwp_20 = (
        gwp.loc["GWP20 BAU", "Total"] - gwp.loc["GWP20 SAF", "Total"]
    ) * 10**6
    abated_emissions_gwp_star = (
        gwp_star.loc["GWP* BAU", "Total"] - gwp_star.loc["GWP* SAF", "Total"]
    ) * 10**6

    # Calculate abatement cost per ton of CO2 eq. for each GWP metric
    abatement_cost_saf_per_ton_gwp_100 = (
        total_abatement_cost_saf / abated_emissions_gwp_100
    )
    abatement_cost_saf_per_ton_gwp_20 = (
        total_abatement_cost_saf / abated_emissions_gwp_20
    )
    abatement_cost_saf_per_ton_gwp_star = (
        total_abatement_cost_saf / abated_emissions_gwp_star
    )

    abatement_costs_saf = {
        "GWP100": abatement_cost_saf_per_ton_gwp_100,
        "GWP20": abatement_cost_saf_per_ton_gwp_20,
        "GWP_star": abatement_cost_saf_per_ton_gwp_star,
    }

    abated_emissions_saf = {
        "GWP100": abated_emissions_gwp_100 / 10**6,
        "GWP20": abated_emissions_gwp_20 / 10**6,
        "GWP_star": abated_emissions_gwp_star / 10**6,
    } # Abated emissions in Mt

    return abatement_costs_saf, abated_emissions_saf


def calculate_total_abatement_cost_dac_non_co2(abatement_curve_daccs, gwp, gwp_star):
    """Function to calculate the abatement cost of DACCS when non-CO2 effects are included. DACCS must abate the same amount of emissions as SAF.

    Params:
    - abatement_curve_daccs: DataFrame with abatement cost data for DACCS
    - gwp: DataFrame with GWP20 and GWP100 values for CO2, NOx, and C-C in BAU and SAF scenarios
    - gwp_star: DataFrame with GWP* values for CO2, NOx, and C-C in BAU and SAF scenarios

    Returns:
    - Dictionary with abatement costs for GWP100, GWP20, and GWP* in $/ton of CO2 eq.
    """

    # Calculate total cost of abatement of CO2 emissions using DACCS in 2050 (same for all scenarios)
    total_abatement_daccs = gwp.loc[
        "GWP100 BAU", "CO2"
    ]  # Same for all scenarios, in MT CO2

    non_co2_emissions_to_abate_gwp_100 = (
        gwp.loc["GWP100 BAU", "Total"]
        - gwp.loc["GWP100 SAF", "Total"]
        - total_abatement_daccs
    ) * 10**6  # in T of CO2 eq.
    ratio_gwp_100 = non_co2_emissions_to_abate_gwp_100 / (
        total_abatement_daccs * 10**6
    )  # Ratio of non-CO2 emissions to CO2 emissions abated

    non_co2_emissions_to_abate_gwp_20 = (
        gwp.loc["GWP20 BAU", "Total"]
        - gwp.loc["GWP20 SAF", "Total"]
        - total_abatement_daccs
    ) * 10**6
    ratio_gwp_20 = non_co2_emissions_to_abate_gwp_20 / (total_abatement_daccs * 10**6)

    non_co2_emissions_to_abate_gwp_star = (
        gwp_star.loc["GWP* BAU", "Total"]
        - gwp_star.loc["GWP* SAF", "Total"]
        - total_abatement_daccs
    ) * 10**6
    ratio_gwp_star = non_co2_emissions_to_abate_gwp_star / (
        total_abatement_daccs * 10**6
    )

    abatement_cost_per_ton_co2_2050 = abatement_curve_daccs.iloc[-1]  # in $/T CO2

    # Calculate abatement cost per ton of CO2 eq. for each GWP metric. This is done by multiplying the abatement cost of CO2 emissions in 2050 by the ratio of non-CO2 emissions to CO2 emissions abated.
    # Rationale: Extra deployment of DACCS is required to abate equivalent emissions from non-CO2 species.
    abatement_cost_daccs_per_ton_gwp_100 = abatement_cost_per_ton_co2_2050 * (
        1 + ratio_gwp_100
    )
    abatement_cost_daccs_per_ton_gwp_20 = abatement_cost_per_ton_co2_2050 * (
        1 + ratio_gwp_20
    )
    abatement_cost_daccs_per_ton_gwp_star = abatement_cost_per_ton_co2_2050 * (
        1 + ratio_gwp_star
    )

    abatement_costs_daccs = {
        "GWP100": abatement_cost_daccs_per_ton_gwp_100,
        "GWP20": abatement_cost_daccs_per_ton_gwp_20,
        "GWP_star": abatement_cost_daccs_per_ton_gwp_star,
    }


    return abatement_costs_daccs


def get_nucleated_ice_crystals(
    emitted_soot_particles, curve="both", plot=False, tech="SAF", year=2050
):
    """
    Calculate nucleated ice crystal number for a given emitted soot particle number.

    Parameters:
    emitted_soot_particles (float or array): Number of emitted soot particles per kg fuel
    curve (str): Which curve to calculate - 'upper', 'lower', or 'both' (default)
    plot (bool): Whether to generate a plot of the curves and interpolated points
    tech (str): Technology type for plot title
    year (int): Year for plot title

    Returns:
    float or tuple: Nucleated ice crystal number(s) per kg fuel
    """

    # Construct x points for the curve
    x = np.logspace(12, 16, 1000)

    # Initialize arrays
    y1 = np.zeros_like(x, dtype=float)
    y2 = np.zeros_like(x, dtype=float)

    # Upper curve calculations (unchanged)
    mask1 = x < 2e13
    mask2 = (x >= 2e13) & (x <= 4.5e14)  # Quadratic decline section
    mask3 = (x > 4.5e14) & (x <= 1e16)  # Linear section from 4.5e14 to 1e16

    # Small linear decline from 1e16 to 9e15 for x < 2e13
    if np.any(mask1):
        log_x_min = np.log10(np.min(x[mask1]))
        log_x_max = np.log10(2e13)
        log_range = log_x_max - log_x_min
        y1[mask1] = 1e16 - (1e16 - 9e15) * (np.log10(x[mask1]) - log_x_min) / log_range

    if np.any(mask2):
        x1, y1_start = 2e13, 9e15
        x2, y1_end = 4.5e14, 6e14
        log_x1, log_y1 = np.log10(x1), np.log10(y1_start)
        log_x2, log_y2 = np.log10(x2), np.log10(y1_end)
        a = -0.5
        b = (log_y2 - log_y1 - a * (log_x2 - log_x1) ** 2) / (log_x2 - log_x1)
        log_x = np.log10(x[mask2])
        log_y = a * (log_x - log_x1) ** 2 + b * (log_x - log_x1) + log_y1
        y1[mask2] = 10**log_y

    if np.any(mask3):
        log_x_start, log_y_start = np.log10(4.5e14), np.log10(6e14)
        log_x_end, log_y_end = np.log10(1e16), np.log10(8e15)
        log_x = np.log10(x[mask3])
        slope = (log_y_end - log_y_start) / (log_x_end - log_x_start)
        log_y = log_y_start + slope * (log_x - log_x_start)
        y1[mask3] = 10**log_y

    # Lower curve - MODIFIED for smooth transitions with monotonically increasing behavior
    # Define key points for the curve
    key_points_x = [1e12, 4e13, 8e14, 1e16]
    key_points_y = [4.5e12, 9e12, 1e14, 1.25e14]

    # Convert to log space
    log_key_x = np.log10(key_points_x)
    log_key_y = np.log10(key_points_y)

    # Use monotonic cubic interpolation to ensure the curve never decreases
    from scipy.interpolate import PchipInterpolator

    # PchipInterpolator preserves monotonicity
    pchip = PchipInterpolator(log_key_x, log_key_y)

    # Apply the interpolation to the entire range
    log_x_values = np.log10(x)
    log_y_values = pchip(log_x_values)
    y2 = 10**log_y_values

    # Create interpolation functions for the input values
    f1 = interp1d(x, y1, kind="linear", fill_value="extrapolate")
    f2 = interp1d(x, y2, kind="linear", fill_value="extrapolate")

    y1_interp = f1(emitted_soot_particles)
    y2_interp = f2(emitted_soot_particles)

    if plot:
        plt.figure(figsize=(10, 6))
        plt.loglog(x, y1, "b-", label="Upper curve")
        plt.loglog(x, y2, "g-", label="Lower curve")
        plt.plot(emitted_soot_particles, y1_interp, "bo", label="Upper interpolated")
        plt.plot(emitted_soot_particles, y2_interp, "go", label="Lower interpolated")

        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.xlabel("Emitted Soot Particle number per kg of fuel")
        plt.ylabel("Nucleated Ice Crystal number per kg of fuel")
        plt.title(
            f"Ice Crystal Nucleation Curves for {tech}-fuelled aircraft in {year}"
        )
        plt.legend()
        plt.show()

    if curve.lower() == "upper":
        return y1_interp
    elif curve.lower() == "lower":
        return y2_interp
    else:
        return np.array([y2_interp, y1_interp])


# Define polynomial function for fitting Fig 19 of DS Lee 2023 et. al.
def poly_func(x, a, b, c):
    return a * x**2 + b * x + c


def calculate_normalised_rf(normalized_ice_particle_number):
    if normalized_ice_particle_number > 1.0:
        return 1.0  # Normalized RF is 1 for values greater than 1 as no data is available for values greater than 1

    x = np.array(
        [0.1, 0.2, 0.5, 1.0]
    )  # From Fig. 19 of DS Lee 2023 et. al. (https://pubs.rsc.org/en/content/articlehtml/2023/ea/d3ea00091e)
    y = np.array([0.3, 0.5, 0.8, 1.0])  # From Fig. 19 of DS Lee 2023 et. al.

    # Fit curve to 4 data points, using a 2nd degree polynomial
    popt, _ = curve_fit(poly_func, x, y)

    # Generate x values for smooth curve
    x_smooth = np.linspace(0.1, 1.0, 100)

    # Generate y values for smooth curve
    y_smooth = poly_func(x_smooth, *popt)

    # Perform interpolation with the normalized
    normalized_rf = np.interp(normalized_ice_particle_number, x_smooth, y_smooth)

    return normalized_rf


def update_emission_factors(
    N_YEARS,
    ANNUAL_EFFICIENCY_CHANGE,
    SOOT_PARTICLE_ESTIMATE_PER_KM_2025,
    SAF_SOOT_PARTICLE_REDUCTION,
    CONTRAIL_AVOIDANCE,
    CONTRAIL_REDUCTION,
    HYDROTREATMENT,
    ht_emission_params,
    show_plots=False,
    tech="SAF",
):
    """

    Function to update emission factors for Contrail Cirrus and C-C based on soot particle emissions and associated ice particle formation per km of distance flown.

    The references used for this are: Karcher (2018) and Markl et. al. (2024)

    Params:
    - N_YEARS: Number of years for which the emissions are to be calculated
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency change for aviation
    - SOOT_PARTICLE_ESTIMATE_PER_KM_2025: Estimate of soot particles emitted per km of distance flown in 2025
    - SAF_SOOT_PARTICLE_REDUCTION: Reduction in soot particles due to SAF
    - show_plots: Whether to show plots for new ice particles. Default is False.
    - tech: Technology for which the emissions are to be calculated. Default is SAF.

    Returns:
    - Updated contrail factor for the given technology

    """

    efficiency_improvement_factor = (
        1 - ANNUAL_EFFICIENCY_CHANGE
    ) ** N_YEARS  # Improvement in combustion efficiency reduces soot particle emissions

    SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = np.array(SOOT_PARTICLE_ESTIMATE_PER_KM_2025)
    # Estimate Ice particles in 2025 based on soot particles emitted per km of distance flown and Karcher (2018) Fig 3
    ICE_PARTICLE_ESTIMATE_PER_KM_2025 = [
        get_nucleated_ice_crystals(p_count, plot=show_plots, tech="Fossil", year=2025)
        for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2025
    ]

    # New soot particle count for 2050 based on efficiency improvement in burn,
    SOOT_PARTICLE_ESTIMATE_PER_KM_2050 = (
        SOOT_PARTICLE_ESTIMATE_PER_KM_2025 * efficiency_improvement_factor
    )

    ICE_PARTICLE_ESTIMATE_PER_KM_2050 = [
        get_nucleated_ice_crystals(p_count, plot=show_plots, tech="Fossil", year=2050)
        for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2050
    ]
    ICE_PARTICLE_ESTIMATE_PER_KM_2050 = np.array(ICE_PARTICLE_ESTIMATE_PER_KM_2050)

    if tech == "SAF":
        future_soot_particles = SOOT_PARTICLE_ESTIMATE_PER_KM_2050 * (
            1 - SAF_SOOT_PARTICLE_REDUCTION
        )  # Markl 2024

        if HYDROTREATMENT["SAF"]:
            future_soot_particles_ht = (
                future_soot_particles / ht_emission_params["BC Grey"]
            )

        else:
            future_soot_particles_ht = future_soot_particles

    elif tech == "Fossil":
        future_soot_particles = SOOT_PARTICLE_ESTIMATE_PER_KM_2050

        if HYDROTREATMENT["Fossil"]:
            future_soot_particles_ht = (
                future_soot_particles * ht_emission_params["BC Grey"]
            )

        else:
            future_soot_particles_ht = future_soot_particles

    future_nucleated_ice_particles = [
        get_nucleated_ice_crystals(p_count, plot=show_plots, tech="SAF", year=2050)
        for p_count in future_soot_particles
    ]
    future_nucleated_ice_particles = np.array(future_nucleated_ice_particles)

    future_nucleated_ice_particles_ht = [
        get_nucleated_ice_crystals(p_count, plot=False, tech="SAF", year=2050)
        for p_count in future_soot_particles_ht
    ]

    future_nucleated_ice_particles_ht = np.array(future_nucleated_ice_particles_ht)

    normalised_nucleated_ice_particles = (
        future_nucleated_ice_particles / ICE_PARTICLE_ESTIMATE_PER_KM_2050
    )

    normalised_nucleated_ice_particles_ht = (
        future_nucleated_ice_particles_ht / ICE_PARTICLE_ESTIMATE_PER_KM_2050
    )

    vectorized_calculate_normalised_rf = np.vectorize(calculate_normalised_rf)
    rf_factors = vectorized_calculate_normalised_rf(normalised_nucleated_ice_particles)
    rf_factors_ht = vectorized_calculate_normalised_rf(
        normalised_nucleated_ice_particles_ht
    )
    rf_factors_ht_median = np.median(rf_factors_ht)
    rf_factors_ht_std = np.std(rf_factors_ht)
    rf_factors_ht = ufloat(rf_factors_ht_median, rf_factors_ht_std)

    if CONTRAIL_AVOIDANCE["SAF"] and tech == "SAF":
        rf_factors = rf_factors - CONTRAIL_REDUCTION

    if CONTRAIL_AVOIDANCE["Fossil"] and tech == "Fossil":
        rf_factors = rf_factors - CONTRAIL_REDUCTION

    nominal_rf_factor = np.median(rf_factors)
    std_rf_factor = np.std(rf_factors)
    new_contrail_factor = ufloat(nominal_rf_factor, std_rf_factor)

    return new_contrail_factor, rf_factors_ht


def calculate_investment_contrail_avoidance(
    demand_df,
    FLEET_SIZE_2025,
    HUMIDITY_SENSOR_COST,
    SENSOR_REQUIREMENT,
    INFRA_COST_MULTIPLIER,
    WACC,
    HUMIDITY_SENSOR_LIFE,
):
    """
    Function to calculate yearly CAPEX for contrail avoidance when a certain percentage of aircraft are equipped with humidity sensors.

    Params:
    - demand_df: DataFrame with projected aviation demand
    - FLEET_SIZE_2025: Fleet size in 2025
    - HUMIDITY_SENSOR_COST: Cost of humidity sensor in $
    - SENSOR_REQUIREMENT: Number of sensors required per aircraft
    - INFRA_COST_MULTIPLIER: Multiplier for infrastructure cost
    - WACC: Weighted average cost of capital
    - HUMIDITY_SENSOR_LIFE: Life of humidity sensor in years

    Returns:
    - Yearly CAPEX for contrail avoidance in 2050 in $

    """

    # Estimate fleet size in 2050.
    FLEET_SIZE_2050 = np.round(
        (demand_df.loc[2050, "DEMAND_M_KM"] / demand_df.loc[2025, "DEMAND_M_KM"])
        * FLEET_SIZE_2025,
        0,
    )

    # Amortize investment cost over the life of the humidity sensor to accurately reflect CAPEX per year.
    amortised_sensor_cost = (
        HUMIDITY_SENSOR_COST
        * (WACC * (1 + WACC) ** HUMIDITY_SENSOR_LIFE)
        / ((1 + WACC) ** HUMIDITY_SENSOR_LIFE - 1)
    )

    # Calculate contrail avoidance CAPEX per year
    contrail_avoidance_capex = (
        FLEET_SIZE_2050
        * amortised_sensor_cost
        * SENSOR_REQUIREMENT
        * INFRA_COST_MULTIPLIER
    )

    return contrail_avoidance_capex


def calculate_additional_fuel_cost(
    demand_df, REROUTING_FUEL_PENALTY, FUEL_PRICE_2050, MJ_PER_L
):
    """
    Function to calculate additional fuel cost due to rerouting for contrail management

    Params:
    - demand_df: DataFrame with projected aviation demand
    - REROUTING_FUEL_PENALTY: Additional fuel consumption (%) due to rerouting
    - FUEL_PRICE: Fuel price in $/L (2050)

    Returns:
    - Additional fuel cost due to rerouting in 2050 ($)
    """

    fuel_demand_2050 = demand_df.loc[2050, "DEMAND_EJ"]  # in EJ

    additional_fuel_consumption_2050_ej = (
        fuel_demand_2050 * REROUTING_FUEL_PENALTY
    )  # in EJ
    additional_fuel_consumption_2050_mj = (
        additional_fuel_consumption_2050_ej * 10**12
    )  # in MJ
    additional_fuel_consumption_2050_l = (
        additional_fuel_consumption_2050_mj / MJ_PER_L
    )  # in L

    additional_fuel_cost = additional_fuel_consumption_2050_l * FUEL_PRICE_2050  # in $

    return additional_fuel_cost


def calculate_additional_abatement_cost_contrail_avoidance(
    df_demand,
    gwp,
    gwp_baseline,
    contrail_avoidance_capex,
    REROUTING_FUEL_PENALTY,
    FUEL_PRICE_2050,
    MJ_PER_L,
):
    abated_emissions_contrail_avoidance = (
        gwp_baseline - gwp
    )  # Avoided emissions by using contrail avoidance

    fuel_cost_additional = calculate_additional_fuel_cost(
        df_demand, REROUTING_FUEL_PENALTY, FUEL_PRICE_2050, MJ_PER_L
    )

    additional_abatement_cost = contrail_avoidance_capex + fuel_cost_additional

    additional_abatement_cost_per_t = additional_abatement_cost / (
        abated_emissions_contrail_avoidance["Total"] * 10**6
    )

    additional_cost_breakdown = pd.DataFrame({
        "CAPEX": (contrail_avoidance_capex / additional_abatement_cost) * additional_abatement_cost_per_t,
        "Fuel Cost": (fuel_cost_additional / additional_abatement_cost) * additional_abatement_cost_per_t
    })

    return additional_abatement_cost_per_t, abated_emissions_contrail_avoidance, additional_cost_breakdown

def calculate_weighted_abatement_cost(emission_components: List[Tuple[float, float]]):

    total_abated_emissions = 0
    total_abatement_cost = 0
    numerator = 0

    for abatement_cost, abated_emissions in emission_components:
        total_abated_emissions += abated_emissions
        numerator += abated_emissions * abatement_cost
    
    total_abatement_cost = numerator / total_abated_emissions
         

    return total_abatement_cost
     


def initialize_hydrotreatment_cost_params():
    """Initialize parameters for hydrotreatment of jet fuel

    Params:
    - None

    Returns:
    - Dictionary with parameters for hydrotreatment of jet fuel

    """

    h2_requirement_green_h2 = 42.7  # m3/ton of fuel
    elec_requirement_green_h2 = 18.3  # kWh/ton of fuel, recalculated
    ng_price = 0.23  # €/m3 in 2050
    elec_price = 0.05  # €/kWh in 2050
    h2_price_kg = 3.2  # €/kg in 2050
    h2_price_m3 = 0.29  # €/m3 in 2050

    hydrotreatment_params = {
        "h2_requirement": h2_requirement_green_h2,
        "elec_requirement": elec_requirement_green_h2,
        "ng_price": ng_price,
        "elec_price": elec_price,
        "h2_price_kg": h2_price_kg,
        "h2_price_m3": h2_price_m3,
    }

    return hydrotreatment_params


def initialize_hydrotreatment_emission_params():
    # Baseline Emissions from Jet A-1
    baseline_so2 = 0.2432  # g/l of fuel
    baseline_co2_per_l = 2.59  # kg/l
    baseline_bc = 0.024  # g/l of fuel

    # Emissions from Hydrotreated Jet A-1 with grey hydrogen
    ht_so2_grey = 0.0111  # g/l of fuel
    ht_co2_per_l_grey = 2.55  # kg/l
    ht_bc_grey = 0.01656 #reduction by 31% in line with SAF

    # Emissions from Hydrotreated Jet A-1 with green hydrogen
    ht_so2_green = 0.0111
    ht_co2_per_l_green = 2.55
    ht_bc_green = 0.01656 #reduction by 31% in line with SAF

    additional_co2_emissions_ht_grey = 0.14
    additional_co2_emissions_ht_green = 0.01

    ht_co2_per_l_grey_net = ht_co2_per_l_grey + additional_co2_emissions_ht_grey
    ht_co2_per_l_green_net = ht_co2_per_l_green + additional_co2_emissions_ht_green

    # Relative emissions for grey and green hydrogen
    relative_so2_grey = ht_so2_grey / baseline_so2
    relative_co2_grey = ht_co2_per_l_grey_net / baseline_co2_per_l
    relative_bc_grey = ht_bc_grey / baseline_bc

    relative_so2_green = ht_so2_green / baseline_so2
    relative_co2_green = ht_co2_per_l_green_net / baseline_co2_per_l
    relative_bc_green = ht_bc_green / baseline_bc

    emissions_params = {
        "SO2 Grey": relative_so2_grey,
        "CO2 Grey": relative_co2_grey,
        "BC Grey": relative_bc_grey,
        "SO2 Green": relative_so2_green,
        "CO2 Green": relative_co2_green,
        "BC Green": relative_bc_green,
    }

    return emissions_params


def calculate_hydrotreatment_cost(
    demand_df,
    hydrotreatment_params,
    DENSITY_SAF,
    MJ_PER_L,
):
    green_h2_cost = (
        hydrotreatment_params["h2_price_m3"] * hydrotreatment_params["h2_requirement"]
    )  # €/ton of fuel

    elec_cost_green = (
        hydrotreatment_params["elec_price"] * hydrotreatment_params["elec_requirement"]
    )  # €/ton of fuel

    total_cost_green = green_h2_cost + elec_cost_green

    total_cost_grey = 10  # €/ton of fuel

    total_cost_per_l_green = total_cost_green / (1000 / DENSITY_SAF)

    total_cost_per_l_grey = total_cost_grey / (1000 / DENSITY_SAF)

    fuel_consumption_2050_l = (
        demand_df.loc[2050, "DEMAND_EJ"] * 10**12 / MJ_PER_L
    )  # in L

    total_cost_2050_green = (
        total_cost_per_l_green * fuel_consumption_2050_l
    )  # total cost in €

    total_cost_2050_grey = (
        total_cost_per_l_grey * fuel_consumption_2050_l
    )  # total cost in €

    total_cost_hydrotreatment = {
        "Green": total_cost_2050_green * EUR_USD,
        "Grey": total_cost_2050_grey * EUR_USD,
    }

    total_cost_hydrotreatment = total_cost_hydrotreatment

    return total_cost_hydrotreatment


def calculate_additional_abatement_hydrotreatment(
    demand_df,
    emission_params,
    rf_factor_ht_saf,
    rf_factor_ht_fossil,
    gwp,
    MJ_PER_L,
    ANNUAL_EFFICIENCY_CHANGE,
    N_YEARS,
    abate_so2=False,
    year=2050,
):
    GWP_metrics = {
        "GWP100": {
            "CO2": 1,
            "netNOx": 114,
            "Contrail Cirrus and C-C": 11,  # km basis
            "BC": 1166,
            "SO2": -226,
            "H2O": 0.06,
        },
        "GWP20": {
            "CO2": 1,
            "netNOx": 619,
            "Contrail Cirrus and C-C": 39,  # km basis
            "BC": 4288,
            "SO2": -832,
            "H2O": 0.22,
        },
    }

    abatement_df_gwp_grey = pd.DataFrame(0, index=gwp.index, columns=gwp.columns)
    abatement_df_gwp_green = pd.DataFrame(0, index=gwp.index, columns=gwp.columns)

    ht_abatement_dfs = {"Grey": abatement_df_gwp_grey, "Green": abatement_df_gwp_green}

    rf_factors = {"BAU": rf_factor_ht_fossil, "SAF": rf_factor_ht_saf}

    species = ["SO2", "CO2", "BC", "Contrail Cirrus and C-C"]

    # Loops over green and grey hydrogen scenarios

    for df_name, df in ht_abatement_dfs.items():
        # Loop over 100% fossil (BAU) and SAF scenarios
        for scenario in ["BAU", "SAF"]:
            # Loop over GWP100 and GWP20 metrics
            for metric in GWP_metrics.keys():
                # Loop over each component that is affected by hydrotreatment
                for component in species:
                    # Contrails are calculated separately based on soot reduction
                    if component != "Contrail Cirrus and C-C":
                        # Abated emissions are calculated by subtracting the emissions from hydrotreated fuel from baseline fuel (either 100% fossil or 100% SAF)
                        df.loc[f"{metric} {scenario}", component] = gwp.loc[
                            f"{metric} {scenario}", component
                        ] - (
                            gwp.loc[f"{metric} {scenario}", component]
                            * emission_params[f"{component} {df_name}"] 
                        )
                    elif component == "Contrail Cirrus and C-C":
                        df.loc[f"{metric} {scenario}", component] = np.array(
                            gwp.loc[f"{metric} {scenario}", component] * (1-rf_factors[scenario]))
    for df in ht_abatement_dfs.values():
        df.loc[:,"CO2"] = df.loc[:,"CO2"].replace(0, df.loc["GWP100 BAU","CO2"])
    
    if not abate_so2:
        for df in ht_abatement_dfs.values():
            df.loc["GWP100 BAU", "SO2"] = 0
            df.loc["GWP100 SAF", "SO2"] = 0
            df.loc["GWP20 BAU", "SO2"] = 0
            df.loc["GWP20 SAF", "SO2"] = 0

            df.loc[:, "Total"] = df.sum(axis=1)
    else:
        for df in ht_abatement_dfs.values():
            df.loc[:, "Total"] = df.sum(axis=1)

    return ht_abatement_dfs


def calculate_additional_abatement_cost_hydrotreatment(
    total_cost_hydrotreatment, ht_abatement_dfs
):
    abatement_cost_dfs = {}

    for df_name, df in ht_abatement_dfs.items():
        abatement_cost_dfs[df_name] = total_cost_hydrotreatment[df_name] / (
            df.loc[:, "Total"] * 10**6
        )

    return abatement_cost_dfs

def calculate_daccs_cost_remaining_emissions(gwp_baseline,gwp_star,abated_emissions_dict,abatement_curve_daccs):

    abated_emissions_saf = abated_emissions_dict["SAF"]
    abated_emissions_daccs = abated_emissions_dict["DACCS"]

    remaining_emissions_saf = {key:0 for key in abated_emissions_saf.keys()}
    remaining_emissions_daccs = {key:0 for key in abated_emissions_daccs.keys()}

    emissions = [(abated_emissions_saf,remaining_emissions_saf), (abated_emissions_daccs, remaining_emissions_daccs)]

    for abated_emissions, remaining_emissions in emissions:
        for metric in remaining_emissions.keys():
            if metric != "GWP_star":
                remaining_emissions[metric] = gwp_baseline.loc[f"{metric} BAU", "Total"] - abated_emissions[metric] # in Mt CO2eq
            else:
                remaining_emissions[metric] = gwp_star.loc["GWP* BAU", "Total"] - abated_emissions[metric] # in Mt CO2eq
    
    return remaining_emissions_saf, remaining_emissions_daccs