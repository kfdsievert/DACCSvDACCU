
import pandas as pd
import numpy as np
import xlsxwriter

def load_input_abatement_cost(file_path, tech):
    """Loads data on abatement costs from master excel sheet and formulates into a dataframe with min, 25%, median, 75%, and max values for each technology."""

    # Final cost column varies by technology
    if tech not in ['DACCS', 'SAF']: 
        raise ValueError('Technology not recognized. Please enter either DACCS or SAF.')
    
    if tech == 'DACCS':
        cost_col = "Fully Harmonized NET REMOVED COST (incl T&S"
        skiprows = 1
        year_col = "Year of Assumptions in Study"
    elif tech == 'SAF':
        cost_col = "Fully Harmonized"
        skiprows = 0
        year_col = "Year of Cost"

    # First row is headers and is skipped
    input_abatement_cost = pd.read_excel(file_path, sheet_name='Standardization Results', skiprows=skiprows, index_col=0)

    # Filter studies with both current (<=2025) and future (2050) costs. The lambda function is used with the filter here.
    input_abatement_cost = input_abatement_cost.groupby(input_abatement_cost.index).filter(
        lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050)
    )
    
    # Filter data for short- and long-term costs
    input_abatement_cost_short = input_abatement_cost[input_abatement_cost[year_col] <= 2025]
    input_abatement_cost_long = input_abatement_cost[input_abatement_cost[year_col] == 2050]

    # Describe statistics
    input_abatement_cost_short = input_abatement_cost_short[cost_col].describe()
    input_abatement_cost_long = input_abatement_cost_long[cost_col].describe()

    # Generate yearly abatement cost interpolations
    yearly_abatement_cost = {}
    yearly_abatement_cost['25%'] = np.linspace(input_abatement_cost_short['25%'], input_abatement_cost_long['25%'], 25)
    yearly_abatement_cost['75%'] = np.linspace(input_abatement_cost_short['75%'], input_abatement_cost_long['75%'], 25) 

    return yearly_abatement_cost

def load_base_inputs(file_path):
    """Loads base inputs from an excel file and returns a dataframe."""

    base_inputs = pd.read_csv(file_path, index_col=0)

    # Select all rows but only the first two columns
    base_inputs = base_inputs.iloc[:, :2]

    return base_inputs

def load_lee(file_path):
    """Loads data from Lee et al. 2021 for aviation emissions and abatement costs."""

    lee = pd.read_csv(file_path, index_col=0)

    return lee

def generate_aviation_demand(
    df_input,  
    DEMAND_GROWTH_RATE, 
    ANNUAL_EFFICIENCY_CHANGE, 
    N_YEARS
): 
    """
    Generate future aviation demand based on historical data and future projections.
    
    Params:
    - df_input: Input DataFrame with base demand values
    - DEMAND_GROWTH_RATE: Annual demand growth rate
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - N_YEARS: Number of years to project
    
    Returns:
    - DataFrame with projected aviation demand
    """

    # Validate input
    if 2025 not in df_input.index:
        raise ValueError("Input DataFrame must contain data for the year 2025")

    # Initial demand for fuel in exajoules
    initial_demand_ej = df_input.loc[2025, 'DEMAND_EJ_BASE']
    # Initial aviation demand in million kilometres
    initial_demand_km = df_input.loc[2025, 'DEMAND_M_KM_BASE']

    # Vectors for demand growth and efficiency improvement
    demand_growth_vector = (1 + DEMAND_GROWTH_RATE) ** np.arange(N_YEARS+1)
    efficiency_growth_vector = (1 - ANNUAL_EFFICIENCY_CHANGE) ** np.arange(N_YEARS+1)

    # Fuel demand is affected by both growth in demand and efficiency improvements
    demand_ej_vector = initial_demand_ej * demand_growth_vector * efficiency_growth_vector
    # Kilometre demand is only affected by growth in demand
    demand_km_vector = initial_demand_km * demand_growth_vector

    # Create output DataFrame
    df_output = pd.DataFrame({
        'DEMAND_EJ': demand_ej_vector,
        'DEMAND_M_KM': demand_km_vector
    }, index=range(2025, 2025+N_YEARS+1))

    return df_output


def generate_equivalence_gwp(demand_df, ANNUAL_EFFICIENCY_CHANGE, N_YEARS,metric="GWP100"): 

    """
    Calculates Equivalent CO2 emissions from GWP metrics as in Lee et. al. 2021

    Params:
    - demand_df: DataFrame with projected aviation demand
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - N_YEARS: Number of years to project
    - metric: GWP metric to use. Default is GWP100

    Returns:
    - DataFrame with equivalent CO2 emissions for each GWP metric for net NOx, CO2, and contrail cirrus cloud formation.
    
    """

    # GWP metrics derived from Table 5 of Lee et. al. 2021: https://doi.org/10.1016/j.atmosenv.2020.117834
    GWP_metrics = {
        "GWP100": {
            "CO2": 1, 
            "Net NOx": 114, 
            "Contrail cirrus": 11 # km basis
        },
        "GWP20": {
            "CO2": 1,
            "Net NOx": 619,
            "Contrail cirrus": 39 # km basis
        }
    }

    # Values below are obtained from the Time Series sheet of the Supplmentary Material of Lee et. al. 2021

    dist_net_2018 = 61333 # Million kms in 2018 from Lee et. al. 2021
    co2_net_2018 = 1034 # Tg CO2 in 2018 from Lee et. al. 2021 (1Tg = 1Mt)
    nox_net_2018 = 1.43 # Tg N in 2018 from Lee et. al. 2021
    contrail_cc_dist_2018 = 6.13 * 10**10 # contrail cirrus cloud km in 2018 from Lee et. al. 2021

    dist_net_2050 = demand_df.loc[2050, 'DEMAND_M_KM'] # Total distance covered in 2050 in million kms
    co2_net_2050 = co2_net_2018 * (dist_net_2050 / dist_net_2018) * (1-ANNUAL_EFFICIENCY_CHANGE)**(N_YEARS) # CO2 emissions in 2050 in Mt corrected for demand and efficiency changes
    nox_net_2050 = nox_net_2018 * (dist_net_2050 / dist_net_2018) * (1-ANNUAL_EFFICIENCY_CHANGE)**(N_YEARS) # NOx emissions in 2050 in Mt corrected for demand and efficiency changes
    contrail_cc_dist_2050 = contrail_cc_dist_2018 * (dist_net_2050 / dist_net_2018) # Contrail cirrus cloud km in 2050 corrected for demand. Efficiency changes do not affect contrail cirrus cloud formation.

    # Formulae below are adopted from the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)
    if metric == "GWP100":
        co2_equiv = co2_net_2050 * GWP_metrics["GWP100"]["CO2"]
        nox_equiv = nox_net_2050 * GWP_metrics["GWP100"]["Net NOx"]
        contrail_cc_equiv = (contrail_cc_dist_2050 / 10**9) * GWP_metrics["GWP100"]["Contrail cirrus"]

    elif metric == "GWP20":
        co2_equiv = co2_net_2050 * GWP_metrics["GWP20"]["CO2"]
        nox_equiv = nox_net_2050 * GWP_metrics["GWP20"]["Net NOx"]
        contrail_cc_equiv = (contrail_cc_dist_2050 / 10**9) * GWP_metrics["GWP20"]["Contrail cirrus"]

    df_equivalents = pd.DataFrame({
        "CO2": co2_equiv,
        "Net NOx": nox_equiv,
        "Contrail cirrus": contrail_cc_equiv
    }, index=[2050])

    return df_equivalents

def project_erf(lee_df, ANNUAL_EFFICIENCY_CHANGE, ANNUAL_DEMAND_GROWTH, SIMULATION_START, SIMULATION_END):
    """
    Project ERF from Lee et. al. 2021 for NOx and CO2 emissions.

    Params:
    - lee_df: DataFrame with Lee et. al. 2021 data for ERFs in a time series.
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - ANNUAL_DEMAND_GROWTH: Annual demand growth rate
    - N_YEARS: Number of years from start of smulation

    Returns:
    - DataFrame with projected ERF for NOx and CO2 emissions.
    """

    erf_df = lee_df.copy()

    initial_nox_erf = erf_df.loc[2018, 'NOx']
    initial_cc_erf = erf_df.loc[2018, 'C-C']

    # Calculate ERF for each year till simulation end
    for year in range(SIMULATION_START, SIMULATION_END+1):
        erf_df.loc[year, 'NOx'] = initial_nox_erf * (1 - ANNUAL_EFFICIENCY_CHANGE)**(year-2018) * (1 + ANNUAL_DEMAND_GROWTH)**(year-2018)
        erf_df.loc[year, 'C-C'] = initial_cc_erf * (1 + ANNUAL_DEMAND_GROWTH)**(year-2018)
    
    return erf_df

def generate_equivalence_gwp_star(erf_df, year, DT):
    """
    Generate GWP100* values for NOx and C-C based on ERF values.

    Params:
    - erf_df: DataFrame with projected ERF values for NOx and C-C
    - year: Year for which GWP* values are to be calculated

    Returns:
    - DataFrame with GWP* values for NOx and C-C in Tg CO2 eq.

    """

    H = 100 # 100 year time span. This is the default value for GWP100* in the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)
    AGWP_CO2 = 0.088 # Absolute GWP of CO2 in mWm-2 yr Mt-1 from Lee et. al. 2021 Supplementary Material AGWP-CO2 sheet
    dt = DT # Time span between emission pulses in GWP*. This is the default from Brazzola et. al. 2022

    # ERF values for the year in which equivalence is being measured
    nox_erf_current = erf_df.loc[year, 'NOx']
    cc_erf_current = erf_df.loc[year, 'C-C']

    # ERF value for "DT" years ago. Default value is 20 years.
    nox_erf_past = erf_df.loc[year-dt, 'NOx'] 
    cc_erf_past = erf_df.loc[year-dt, 'C-C']

    # Calulate GWP* values in Tg CO2 eq. for NOx and Contrail cirrus
    nox_gwp_star = ((nox_erf_current - nox_erf_past)/dt) * (H / AGWP_CO2) # Formula for GWP* calculation adopted from Brazzola et. al. 2022 
    cc_gwp_star = ((cc_erf_current - cc_erf_past)/dt) * (H / AGWP_CO2)

    gwp_star_df = pd.DataFrame({
        "NOx": nox_gwp_star,
        "Contrail cirrus": cc_gwp_star
    }, index=[year])

    return gwp_star_df

