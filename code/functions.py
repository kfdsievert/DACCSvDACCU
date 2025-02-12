
import pandas as pd
import numpy as np
import xlsxwriter
from uncertainties import unumpy, ufloat
from fair.forward import fair_scm
from fair.inverse import inverse_fair_scm
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

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
        return_residual_emissions = True

    # First row is headers and is skipped
    input_abatement_cost = pd.read_excel(file_path, sheet_name='Standardization Results', skiprows=skiprows, index_col=0)
    
    if tech == 'SAF':
        input_abatement_cost_low = pd.read_excel(file_path, sheet_name='Low CO2', skiprows=skiprows, index_col=0)
        input_abatement_cost_high = pd.read_excel(file_path, sheet_name='High CO2', skiprows=skiprows, index_col=0)


    # Filter studies with both current (<=2025) and future (2050) costs. The lambda function is used with the filter here.
    input_abatement_cost = input_abatement_cost.groupby(input_abatement_cost.index).filter(
        lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050)
    )
    if tech == 'SAF':
        input_abatement_cost_low = input_abatement_cost_low.groupby(input_abatement_cost_low.index).filter(
            lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050)
        )
        input_abatement_cost_high = input_abatement_cost_high.groupby(input_abatement_cost_high.index).filter(
            lambda x: any(x[year_col] <= 2025) and any(x[year_col] == 2050)
        )
    
    # Filter data for short- and long-term costs
    input_abatement_cost_short = input_abatement_cost[input_abatement_cost[year_col] <= 2025]
    input_abatement_cost_long = input_abatement_cost[input_abatement_cost[year_col] == 2050]

    if tech == 'SAF':
        input_abatement_cost_short_low = input_abatement_cost_low[input_abatement_cost_low[year_col] <= 2025]
        input_abatement_cost_long_low = input_abatement_cost_low[input_abatement_cost_low[year_col] == 2050]
        input_abatement_cost_short_high = input_abatement_cost_high[input_abatement_cost_high[year_col] <= 2025]
        input_abatement_cost_long_high = input_abatement_cost_high[input_abatement_cost_high[year_col] == 2050]

    # Descriptive statistics
    input_abatement_cost_short = input_abatement_cost_short[cost_col].describe()
    input_abatement_cost_long = input_abatement_cost_long[cost_col].describe()

    # For SAF, descriptive statistics are taken from High (75th percentile) and Low(25th percentile) CO2 prices
    if tech == 'SAF':
        input_abatement_cost_short_low = input_abatement_cost_short_low[cost_col].describe()
        input_abatement_cost_long_low = input_abatement_cost_long_low[cost_col].describe()
        input_abatement_cost_short_high = input_abatement_cost_short_high[cost_col].describe()
        input_abatement_cost_long_high = input_abatement_cost_long_high[cost_col].describe()

    # Generate yearly abatement cost interpolations
    if tech == "DACCS":
        yearly_abatement_cost = pd.DataFrame()
        yearly_abatement_cost['50%'] = np.linspace(input_abatement_cost_short['50%'], input_abatement_cost_long['50%'], 25)
        yearly_abatement_cost['25%'] = np.linspace(input_abatement_cost_short['25%'], input_abatement_cost_long['25%'], 25)
        yearly_abatement_cost['75%'] = np.linspace(input_abatement_cost_short['75%'], input_abatement_cost_long['75%'], 25) 
    
    # For SAF, the minimum value is the 25th percentile of results for low CO2 prices and the maximum value is the 75th percentile of results for high CO2 prices.
    elif tech == "SAF":
        yearly_abatement_cost = pd.DataFrame()
        yearly_abatement_cost['50%'] = np.linspace(input_abatement_cost_short['50%'], input_abatement_cost_long['50%'], 25)
        yearly_abatement_cost['25%'] = np.linspace(input_abatement_cost_short_low['25%'], input_abatement_cost_long_low['25%'], 25)
        yearly_abatement_cost['75%'] = np.linspace(input_abatement_cost_short_high['75%'], input_abatement_cost_long_high['75%'], 25)

    yearly_abatement_cost.to_excel(f"outputs/abatement_cost_curve_{tech}.xlsx")

    # Only activated for SAF, residual emissions are abated using DACCS.
    if return_residual_emissions:
        residual_emissions = input_abatement_cost.loc[:,["Residual Emissions (gCO2eq/L fuel)", "Year of Cost"]]

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

def generate_aviation_demand(df_input, DEMAND_GROWTH_RATE, ANNUAL_EFFICIENCY_CHANGE, N_YEARS): 

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


def generate_equivalence_gwp(demand_df, base_inputs, year, SAF_FACTORS, ANNUAL_EFFICIENCY_CHANGE, N_YEARS,metric="GWP100"): 

    """
    Calculates Equivalent CO2 emissions from GWP metrics as in Lee et. al. 2021

    Params:
    - demand_df: DataFrame with projected aviation demand
    - base_inputs: DataFrame with base inputs for progression curve of SAF from Brazzola et. al. 2024
    - year: Year for which GWP values are to be calculated
    - SAF_FACTORS: Dictionary with multipliers for SAF emissions addopted from Brazzola et. al. 2024
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency improvement rate
    - N_YEARS: Number of years to project
    - metric: GWP metric to use. Default is GWP100

    Returns:
    - DataFrame with equivalent CO2 emissions for each GWP metric for net NOx, CO2, and Contrail Cirrus and C-C cloud formation in BAU and SAF scenarios.
    
    """

    # GWP metrics derived from Table 5 of Lee et. al. 2021: https://doi.org/10.1016/j.atmosenv.2020.117834
    GWP_metrics = {
        "GWP100": {
            "CO2": 1, 
            "netNOx": 114, 
            "Contrail Cirrus and C-C": 11 # km basis
        },
        "GWP20": {
            "CO2": 1,
            "netNOx": 619,
            "Contrail Cirrus and C-C": 39 # km basis
        }
    }

    # Values below are obtained from the Time Series sheet of the Supplmentary Material of Lee et. al. 2021

    # SAF deployment in selected year
    saf_deployed_current = base_inputs.loc[year, 'PROGRESSION_CURVE']
    fossil_share_current = 1 - saf_deployed_current

    dist_net_2018 = 61333 # Million kms in 2018 from Lee et. al. 2021
    co2_net_2018 = 1034 # Tg CO2 in 2018 from Lee et. al. 2021 (1Tg = 1Mt)
    nox_net_2018 = 1.43 # Tg N in 2018 from Lee et. al. 2021
    contrail_cc_dist_2018 = 6.13 * 10**10 # Contrail Cirrus and C-C cloud km in 2018 from Lee et. al. 2021

    dist_net_year = demand_df.loc[year, 'DEMAND_M_KM'] # Total distance covered in 2050 in million kms
    co2_net_year = co2_net_2018 * (dist_net_year / dist_net_2018) * (1-ANNUAL_EFFICIENCY_CHANGE)**(N_YEARS) # CO2 emissions in 2050 in Mt corrected for demand and efficiency changes
    nox_net_year = nox_net_2018 * (dist_net_year / dist_net_2018) * (1-ANNUAL_EFFICIENCY_CHANGE)**(N_YEARS) # NOx emissions in 2050 in Mt corrected for demand and efficiency changes
    contrail_cc_dist_year = contrail_cc_dist_2018 * (dist_net_year / dist_net_2018) * (1-ANNUAL_EFFICIENCY_CHANGE) ** (N_YEARS) # Contrail Cirrus and C-C distance in km in 2050 corrected for demand and efficiency changes

    # Formulae below are adopted from the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)
    
    # BAU scenario
    co2_equiv_bau = co2_net_year * GWP_metrics[metric]["CO2"]
    nox_equiv_bau = nox_net_year * GWP_metrics[metric]["netNOx"]
    contrail_cc_equiv_bau = (contrail_cc_dist_year / 10**9) * GWP_metrics[metric]["Contrail Cirrus and C-C"]

    # SAF scenario Fossil component
    co2_equiv_fossil = co2_equiv_bau * fossil_share_current
    nox_equiv_fossil = nox_equiv_bau * fossil_share_current
    contrail_cc_equiv_fossil = contrail_cc_equiv_bau * fossil_share_current

    # SAF scenario SAF component
    co2_equiv_saf = co2_equiv_bau * saf_deployed_current * SAF_FACTORS["CO2"]
    nox_equiv_saf = nox_equiv_bau * saf_deployed_current * SAF_FACTORS["netNOx"]
    contrail_cc_equiv_saf = contrail_cc_equiv_bau * saf_deployed_current * SAF_FACTORS["Contrail Cirrus and C-C"]

    # Total CO2 equivalent emissions SAF scenario
    co2_equiv_total = co2_equiv_fossil + co2_equiv_saf
    nox_equiv_total = nox_equiv_fossil + nox_equiv_saf
    contrail_cc_equiv_total = contrail_cc_equiv_fossil + contrail_cc_equiv_saf


    df_equivalents_saf = pd.DataFrame({
        "CO2": co2_equiv_total,
        "netNOx": nox_equiv_total,
        "Contrail Cirrus and C-C": contrail_cc_equiv_total
    }, index=[f"{metric} SAF"])

    df_equivalents_bau = pd.DataFrame({
        "CO2": co2_equiv_bau,
        "netNOx": nox_equiv_bau,
        "Contrail Cirrus and C-C": contrail_cc_equiv_bau
    }, index=[f"{metric} BAU"])

    df_equivalents = pd.concat([df_equivalents_bau, df_equivalents_saf], axis=0)

    return df_equivalents

def make_CO2aviation_hist():
    """
    Makes CO2 emissions from aviation from 1940-2018 from concentrations reported in Lee et al. 2021
    :return: historical aviation CO2 emissions and forcing due to CO2 emissions
    """
    CO2_C_1940_2018 = np.array([0.0042, 0.0078, 0.0113, 0.0149, 0.0187, 0.0227, 0.0269, 0.0314, 0.0362, 0.0413, 0.0468,
                          0.0527, 0.0590, 0.0658, 0.0731, 0.0810, 0.0894, 0.0986, 0.1085, 0.1192, 0.1308, 0.1437,
                          0.1579, 0.1724, 0.1870, 0.2024, 0.2193, 0.2409, 0.2657, 0.2907, 0.3143, 0.3386, 0.3647,
                          0.3916, 0.4162, 0.4404, 0.4643, 0.4908, 0.5185, 0.5475, 0.5762, 0.6038, 0.6319, 0.6598,
                          0.6898, 0.7213, 0.7558, 0.7924, 0.8315, 0.8725, 0.9130, 0.9507, 0.9872, 1.0216, 1.0596,
                          1.0997, 1.1434, 1.1892, 1.2361, 1.2853, 1.3382, 1.3869, 1.4357, 1.4843, 1.5381, 1.5956,
                          1.6530, 1.7123, 1.7704, 1.8227, 1.8803, 1.9401, 2.0004, 2.0633, 2.1291, 2.2002, 2.2737,
                          2.3496, 2.4281]) # CO2 concentrations in ppm above 278 ppm (pre-industrial average)
    CO2_C_1940_2018 += 278 # Add to get actual atmospheric effect
    E1, F1, T1 = inverse_fair_scm(C=CO2_C_1940_2018, rt=0)
    return E1, F1

def future_aviation_emissions(base_inputs, ANNUAL_EFFICIENCY_CHANGE, DEMAND_GROWTH_RATE, scenario, SAF_FACTORS):

    """
    Function to generate future CO2 emissions from aviation
    """

    co2_net_2018 = 1034 # Tg CO2 in 2018 from Lee et. al. 2021 (1Tg = 1Mt)
    nox_net_2018 = 1.43 # Tg NOx in 2018 from Lee et. al. 2021
    bc_net_2018 = 0.0093 # Tg BC in 2018 from Lee et. al. 2021
    so2_net_2018 = 0.3729 # Tg SO2 in 2018 from Lee et. al. 2021
    h2o_net_2018 = 382.6 # Tg H2O in 2018 from Lee et. al. 2021
    contrail_net_2018 = 6.13e10 # km in 2018 from Lee et. al. 2021
    n_years = 2050 - 2018

    demand_growth_vector = (1 + DEMAND_GROWTH_RATE) ** np.arange(n_years+1)
    efficiency_growth_vector = (1 - ANNUAL_EFFICIENCY_CHANGE) ** np.arange(n_years+1)

    co2_emissions = np.zeros(n_years)
    nox_emissions = np.zeros(n_years)
    bc_emissions = np.zeros(n_years)
    so2_emissions = np.zeros(n_years)
    h2o_emissions = np.zeros(n_years)
    contrail_emissions = np.zeros(n_years)

    saf_share = base_inputs['PROGRESSION_CURVE'].loc["2018":str(2018+n_years)]
    fossil_share = 1 - saf_share

    if scenario == "BAU":
        co2_emissions = co2_net_2018 * demand_growth_vector * efficiency_growth_vector
        nox_emissions = nox_net_2018 * demand_growth_vector * efficiency_growth_vector
        bc_emissions = bc_net_2018 * demand_growth_vector * efficiency_growth_vector
        so2_emissions = so2_net_2018 * demand_growth_vector * efficiency_growth_vector
        h2o_emissions = h2o_net_2018 * demand_growth_vector * efficiency_growth_vector
        contrail_emissions = contrail_net_2018 * demand_growth_vector * efficiency_growth_vector

    elif scenario == "SAF":
        co2_emissions = co2_net_2018 * demand_growth_vector * efficiency_growth_vector * (fossil_share + saf_share * SAF_FACTORS['CO2'])
        nox_emissions = nox_net_2018 * demand_growth_vector * efficiency_growth_vector * (fossil_share + saf_share * SAF_FACTORS['netNOx'])
        contrail_emissions = contrail_net_2018 * demand_growth_vector * efficiency_growth_vector * (fossil_share + saf_share * SAF_FACTORS['Contrail Cirrus and C-C'])
        bc_emissions = bc_net_2018 * demand_growth_vector * efficiency_growth_vector
        so2_emissions = so2_net_2018 * demand_growth_vector * efficiency_growth_vector
        h2o_emissions = h2o_net_2018 * demand_growth_vector * efficiency_growth_vector




    df_emissions = pd.DataFrame(index = np.arange(2018, 2051), columns = ['CO2', 'NOx', 'BC', 'SO2', 'H2O', 'Contrail'],
                                    data = np.array([co2_emissions, nox_emissions, bc_emissions, so2_emissions, h2o_emissions, contrail_emissions]).T)
    


    return df_emissions


def calc_ERF_CO2(E, start_year=1990):
    """
    Calculate the ERF of CO2
    :param E: dataframe with future emissions
    :param start_year: start date of future emissions
    :return: forcing of CO2 emissions from start date
    """
    E_CO2_hist = make_CO2aviation_hist()[0]
    E_GtC = E.loc[str(start_year):,"CO2"].values / (3.677*10**3)
    E_input = np.concatenate((E_CO2_hist[:start_year-1940], E_GtC), axis = 0)
    C_CO2, F_CO2, T_CO2= fair_scm(
        emissions = E_input,
        useMultigas= False
    )
    return F_CO2[start_year-1940:]*10**3 #in mW/m2


def calculate_ERF(df, e_factors):
    """
    Function to calculate ERF from sensitivity to emissions reported in Lee et al. 2021
    :param df: dataframe with emissions
    :param e_factors: sensitivity to emissions reported in Lee et al. 2021
    :return: ERF of each species in each year
    """
    # Index is datetime 2018 - 2050
    index = pd.date_range(start='2018', end='2051', freq='Y')
    columns = e_factors.keys()
    # sensitivity to emissions for other species + uncertainties (as in Lee et al. 2021)
    erf_data = np.array([ufloat(34.44, 9.90), ufloat(-18.60,6.90), ufloat(-9.35,3.40), ufloat(-2.80,1.00), ufloat(5.46,8.10),
                     ufloat(100.67, 165.50), ufloat(-19.91,16.00), ufloat(0.0052, 0.0026), ufloat(9.36*10**(-10),6.57*10**(-10))])
    erf_factors = pd.DataFrame(index = columns, columns = ['ERF factors'],
                                 data = erf_data)
    ERF_df = pd.DataFrame(index=index, columns=columns)
    ERF_df = ERF_df.fillna(0.)
    ERF_df['CO2'] = calc_ERF_CO2(df, start_year=index[0].year)
    ERF_df['O3 short'] = df['NOx'].values*erf_factors.loc['O3 short',:].values
    ERF_df['CH4'] = df['NOx'].values*erf_factors.loc['CH4',:].values
    ERF_df['O3 long'] = df['NOx'].values*erf_factors.loc['O3 long',:].values
    ERF_df['SWV'] = df['NOx'].values*erf_factors.loc['SWV',:].values
    ERF_df['netNOx'] = df['NOx'].values*erf_factors.loc['netNOx',:].values
    ERF_df['BC'] = df['BC'].values*erf_factors.loc['BC',:].values
    ERF_df['SO4'] = df['SO2'].values*erf_factors.loc['SO4',:].values
    ERF_df['H2O'] = df['H2O'].values*erf_factors.loc['H2O',:].values
    ERF_df['Contrail Cirrus and C-C'] = df['Contrail'].values*erf_factors.loc['Contrail Cirrus and C-C',:].values
    ERF_df['non-CO2'] = ERF_df.loc[:,['netNOx', 'BC', 'SO4', 'H2O', 'Contrail Cirrus and C-C']].sum(axis=1)
    ERF_df['Tot'] = ERF_df.loc[:,['netNOx', 'BC', 'SO4', 'H2O', 'Contrail Cirrus and C-C', 'CO2']].sum(axis=1)
    return ERF_df


def generate_equivalence_gwp_star(erf_df_fossil, erf_df_saf, base_inputs, year, SAF_FACTORS, dt):

    """
    Generate GWP100* values for NOx and C-C based on ERF values.

    Params:
    - erf_df: DataFrame with projected ERF values for NOx and C-C
    - base_inputs: DataFrame with base inputs for progression curve of SAF from Brazzola et. al. 2024
    - year: Year for which GWP* values are to be calculated
    - SAF_FACTORS: Dictionary with multipliers for SAF emissions addopted from Brazzola et. al. 2024
    - dt: Time span between emission pulses in GWP*. Default is 20 years.

    Returns:
    - DataFrame with GWP* values for NOx and C-C in Tg CO2 eq. for SAF and BAU scenarios.

    """

    H = 100 # 100 year time span. This is the default value for GWP100* in the code for Brazzola et. al. 2022 (https://doi.org/10.1038/s41558-022-01404-7)
    AGWP_CO2 = 0.088 # Absolute GWP of CO2 in mWm-2 yr Mt-1 from Lee et. al. 2021 Supplementary Material AGWP-CO2 sheet

    erf_df_fossil.index = erf_df_fossil.index.year
    erf_df_saf.index = erf_df_saf.index.year

    # ERF values for BAU scenario - Current year
    nox_erf_current_bau = erf_df_fossil.loc[year, 'netNOx']
    cc_erf_current_bau = erf_df_fossil.loc[year, 'Contrail Cirrus and C-C']

    # ERF values for BAU scenario - "DT" years ago.
    nox_erf_past_bau = erf_df_fossil.loc[year-dt, 'netNOx']
    cc_erf_past_bau = erf_df_fossil.loc[year-dt, 'Contrail Cirrus and C-C']

    # ERF values for SAF scenario - Current year
    nox_erf_current_saf = erf_df_saf.loc[year, 'netNOx'] * SAF_FACTORS['netNOx']
    cc_erf_current_saf = erf_df_saf.loc[year, 'Contrail Cirrus and C-C'] * SAF_FACTORS['Contrail Cirrus and C-C']

    # ERF values for SAF scenario - "DT" years ago.
    nox_erf_past_saf = erf_df_saf.loc[year-dt, 'netNOx'] * SAF_FACTORS['netNOx']
    cc_erf_past_saf = erf_df_saf.loc[year-dt, 'Contrail Cirrus and C-C'] * SAF_FACTORS['Contrail Cirrus and C-C']



    # Calulate GWP* values in Tg CO2 eq. for NOx and Contrail Cirrus and C-C - BAU scenario
    nox_gwp_star_bau = ((nox_erf_current_bau - nox_erf_past_bau)/dt) * (H / AGWP_CO2) # Formula for GWP* calculation adopted from Brazzola et. al. 2022 
    cc_gwp_star_bau = ((cc_erf_current_bau - cc_erf_past_bau)/dt) * (H / AGWP_CO2)

    # Calulate GWP* values in Tg CO2 eq. for NOx and Contrail Cirrus and C-C - SAF scenario
    nox_gwp_star_saf = ((nox_erf_current_saf - nox_erf_past_saf)/dt) * (H / AGWP_CO2) # Formula for GWP* calculation adopted from Brazzola et. al. 2022
    cc_gwp_star_saf = ((cc_erf_current_saf - cc_erf_past_saf)/dt) * (H / AGWP_CO2)


    gwp_star_saf_df = pd.DataFrame({
        "NOx": nox_gwp_star_saf,
        "Contrail Cirrus and C-C": cc_gwp_star_saf,
        "CO2" : 0
    }, index=["GWP* SAF"])

    gwp_star_bau_df = pd.DataFrame({
        "NOx": nox_gwp_star_bau,
        "Contrail Cirrus and C-C": cc_gwp_star_bau,
        "CO2" : 0
    }, index=["GWP* BAU"])

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
    total_co2 = gwp_df.loc["GWP100 BAU", 'CO2'] * 10**6 # In T of CO2
    
    # Abatement cost for SAF in 2050 (same for GWP and GWP*)
    abatement_cost = abatement_cost_saf.loc[year-SIMULATION_START-1] * total_co2

    return abatement_cost

def calculate_residual_abatement_saf(residual_emissions, df_demand, abatement_curve_daccs, year, MJ_PER_L, SIMULATION_START):

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

    residual_emissions_l = np.mean(residual_emissions.loc[residual_emissions["Year of Cost"] == year, "Residual Emissions (gCO2eq/L fuel)"]) # Residual emissions in gCO2/L of fuel
    residual_emissions_mj = residual_emissions_l  / MJ_PER_L # Residual emissions in gCO2/MJ of fuel
    residual_emissions_ej = residual_emissions_mj * 10**12 # Residual emissions in gCO2/EJ of fuel

    # Total Residual Emissions from SAF in 2050: 
    residual_emissions_total = residual_emissions_ej * df_demand.loc[year, 'DEMAND_EJ'] # in g of CO2
    residual_emissions_total = residual_emissions_total / 10**9 # in T of CO2

    # Calculate abatement cost for residual emissions using DACCS
    abatement_cost_residual = abatement_curve_daccs.loc[year-SIMULATION_START-1] * residual_emissions_total 

    return abatement_cost_residual

def calculate_total_abatement_cost_saf_non_co2 (total_abatement_cost_saf, gwp, gwp_star):

    """Function to calculate the abatement cost of SAF when non-CO2 effects are included

    Params:
    - total_abatement_cost_saf: Total abatement cost of SAF in 2050 in $ 
    - gwp: DataFrame with GWP20 and GWP100 values for CO2, NOx, and C-C in BAU and SAF scenarios
    - gwp_star: DataFrame with GWP* values for CO2, NOx, and C-C in BAU and SAF scenarios

    Returns:
    - Dictionary with abatement costs for GWP100, GWP20, and GWP* in $/ton of CO2 eq.
    """
    
    # Calculate abated emissions for each GWP metric. This is done by taking the difference between SAF and BAU scenarios for each GWP metric and multiplying by 10^6 to convert to T of CO2 eq.
    abated_emissions_gwp_100 = (gwp.loc["GWP100 BAU", "Total"] - gwp.loc["GWP100 SAF", "Total"]) * 10**6 # in T of CO2 eq.
    abated_emissions_gwp_20 = (gwp.loc["GWP20 BAU", "Total"] - gwp.loc["GWP20 SAF", "Total"]) * 10**6 
    abated_emissions_gwp_star = (gwp_star.loc["GWP* BAU", "Total"] - gwp_star.loc["GWP* SAF", "Total"]) * 10**6

    # Calculate abatement cost per ton of CO2 eq. for each GWP metric
    abatement_cost_saf_per_ton_gwp_100 = total_abatement_cost_saf / abated_emissions_gwp_100
    abatement_cost_saf_per_ton_gwp_20 = total_abatement_cost_saf / abated_emissions_gwp_20 
    abatement_cost_saf_per_ton_gwp_star = total_abatement_cost_saf / abated_emissions_gwp_star

    abatement_costs_saf = {
        "GWP100": abatement_cost_saf_per_ton_gwp_100,
        "GWP20": abatement_cost_saf_per_ton_gwp_20,
        "GWP_star": abatement_cost_saf_per_ton_gwp_star
    }

    return abatement_costs_saf

def calculate_total_abatemnet_cost_dac_non_co2 (abatement_curve_daccs, gwp,gwp_star):
    
    """Function to calculate the abatement cost of DACCS when non-CO2 effects are included

    Params:
    - abatement_curve_daccs: DataFrame with abatement cost data for DACCS
    - gwp: DataFrame with GWP20 and GWP100 values for CO2, NOx, and C-C in BAU and SAF scenarios
    - gwp_star: DataFrame with GWP* values for CO2, NOx, and C-C in BAU and SAF scenarios

    Returns:
    - Dictionary with abatement costs for GWP100, GWP20, and GWP* in $/ton of CO2 eq.
    """

    # Calculate total cost of abatement of CO2 emissions using DACCS in 2050 (same for all scenarios)
    total_abatement_daccs = gwp.loc["GWP100 BAU", "CO2"] # Same for all scenarios, in MT CO2

    non_co2_emissions_to_abate_gwp_100 = (gwp.loc["GWP100 BAU", "Total"] - gwp.loc["GWP100 SAF", "Total"] - total_abatement_daccs) * 10**6# in T of CO2 eq.
    ratio_gwp_100 = non_co2_emissions_to_abate_gwp_100 / (total_abatement_daccs * 10**6) # Ratio of non-CO2 emissions to CO2 emissions abated

    non_co2_emissions_to_abate_gwp_20 = (gwp.loc["GWP20 BAU", "Total"] - gwp.loc["GWP20 SAF", "Total"] - total_abatement_daccs) * 10**6
    ratio_gwp_20 = non_co2_emissions_to_abate_gwp_20 / (total_abatement_daccs * 10**6)

    non_co2_emissions_to_abate_gwp_star = (gwp_star.loc["GWP* BAU", "Total"] - gwp_star.loc["GWP* SAF", "Total"] - total_abatement_daccs) * 10**6
    ratio_gwp_star = non_co2_emissions_to_abate_gwp_star / (total_abatement_daccs * 10**6)

    abatement_cost_per_ton_co2_2050 = abatement_curve_daccs.iloc[-1] # in $/T CO2

    # Calculate abatement cost per ton of CO2 eq. for each GWP metric. This is done by multiplying the abatement cost of CO2 emissions in 2050 by the ratio of non-CO2 emissions to CO2 emissions abated.
    # Rationale: Extra deployment of DACCS is required to abate equivalent emissions from non-CO2 species.
    abatement_cost_daccs_per_ton_gwp_100 = abatement_cost_per_ton_co2_2050 * (1+ ratio_gwp_100)
    abatement_cost_daccs_per_ton_gwp_20 = abatement_cost_per_ton_co2_2050 * (1+ ratio_gwp_20)
    abatement_cost_daccs_per_ton_gwp_star = abatement_cost_per_ton_co2_2050 * (1+ ratio_gwp_star)

    abatement_costs_daccs = {
        "GWP100": abatement_cost_daccs_per_ton_gwp_100,
        "GWP20": abatement_cost_daccs_per_ton_gwp_20,
        "GWP_star": abatement_cost_daccs_per_ton_gwp_star
    }

    return abatement_costs_daccs

import numpy as np
from scipy.interpolate import interp1d

def get_nucleated_ice_crystals(emitted_soot_particles, curve='both', plot=False):

    """
    Calculate nucleated ice crystal number for a given emitted soot particle number.
    
    Parameters:
    emitted_soot_particles (float or array): Number of emitted soot particles per kg fuel
    curve (str): Which curve to calculate - 'upper', 'lower', or 'both' (default)
    plot (bool): Whether to generate a plot of the curves and interpolated points
    
    Returns:
    float or tuple: Nucleated ice crystal number(s) per kg fuel
    """
    # Construct x points for the curve
    x = np.logspace(12, 16, 1000)
    
    # Initialize arrays
    y1 = np.zeros_like(x, dtype=float)
    y2 = np.zeros_like(x, dtype=float)
    
    # Upper curve calculations
    mask1 = x < 7e13
    mask2 = (x >= 7e13) & (x <= 1e15)
    mask3 = x > 1e15
    
    # Linear decline in log space (initial segment)
    log_slope = (np.log10(1e14) - np.log10(1e15)) / (np.log10(7e13) - np.log10(1e12))
    y1[mask1] = 10**(np.log10(1e15) + log_slope * (np.log10(x[mask1]) - np.log10(1e12)))
    
    # Steeper upward trajectory to reach 1e15 at x=1e15
    start_y = 10**(np.log10(1e15) + log_slope * (np.log10(7e13) - np.log10(1e12)))
    exponent = np.log10(1e15/start_y) / np.log10(1e15/7e13)
    y1[mask2] = start_y * (x[mask2]/7e13)**exponent
    
    # Continue same slope after 1e15
    y1[mask3] = 1e15 * (x[mask3]/1e15)**exponent
    
    # Lower curve calculations with gradual rise
    mask_lower1 = x < 1e14
    mask_lower2 = (x >= 1e14) & (x <= 1e15)
    mask_lower3 = x > 1e15
    
    def smooth_rising_curve(x_val):
        # Transform to [0,1] range for x values between 1e12 and 1e14
        t = (np.log10(x_val) - 12) / (14 - 12)
        
        # Define start and end points in log space
        log_start = np.log10(6e12)
        log_end = np.log10(2e13)
        log_range = log_end - log_start
        
        # Create a more gradual exponential curve
        # Use power function with small exponent for gradual increase
        power = 2.5  # Controls the overall shape of the curve
        curve_factor = t**power
        
        # Add small offset to ensure initial flatness
        offset = 0.05
        adjusted_factor = (curve_factor + offset) / (1 + offset)
        
        # Calculate final value
        log_y = log_start + log_range * adjusted_factor
        
        return 10**log_y
    
    y2[mask_lower1] = smooth_rising_curve(x[mask_lower1])
    
    # NOTE: CHECK Reduced slope after 10^14 (80% of upper curve slope)
    lower_exponent = exponent * 0.9
    y2[mask_lower2] = 2e13 * (x[mask_lower2]/1e14)**lower_exponent
    
    # Continue same reduced slope after 1e15
    y2_at_1e15 = 2e13 * (1e15/1e14)**lower_exponent
    y2[mask_lower3] = y2_at_1e15 * (x[mask_lower3]/1e15)**lower_exponent
    
    # Create interpolation functions for both curves
    f1 = interp1d(x, y1, kind='linear', fill_value='extrapolate')
    f2 = interp1d(x, y2, kind='linear', fill_value='extrapolate')
    
    # Calculate interpolated values for the input x
    y1_interp = f1(emitted_soot_particles)
    y2_interp = f2(emitted_soot_particles)
    
    if plot:
        plt.figure(figsize=(10, 6))
        plt.loglog(x, y1, 'b-', label='Upper curve')
        plt.loglog(x, y2, 'g-', label='Lower curve')
        
        # Plot interpolated points
        plt.plot(emitted_soot_particles, y1_interp, 'bo', label='Upper interpolated')
        plt.plot(emitted_soot_particles, y2_interp, 'go', label='Lower interpolated')
        
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.xlabel('Emitted Soot Particles')
        plt.ylabel('Nucleated Ice Crystals')
        plt.title('Ice Crystal Nucleation Curves')
        plt.legend()
        plt.show()
    
    # Return results based on requested curve
    if curve.lower() == 'upper':
        return y1_interp
    elif curve.lower() == 'lower':
        return y2_interp
    else:  # both
        return np.array([y2_interp, y1_interp])


# Define polynomial function for fitting Fig 19 of DS Lee 2023 et. al.
def poly_func(x, a, b, c):
    return a*x**2 + b*x + c

def calculate_normalised_rf (normalized_ice_particle_number) :

    if normalized_ice_particle_number > 1.0:
        return 1.0 # Normalized RF is 1 for values greater than 1 as no data is available for values greater than 1

    x = np.array([0.1, 0.2, 0.5, 1.0]) # From Fig. 19 of DS Lee 2023 et. al. (https://pubs.rsc.org/en/content/articlehtml/2023/ea/d3ea00091e)
    y = np.array([0.3, 0.5, 0.8, 1.0]) # From Fig. 19 of DS Lee 2023 et. al.

    # Fit curve to 4 data points, using a 2nd degree polynomial
    popt, _ = curve_fit(poly_func, x, y)

    # Generate x values for smooth curve
    x_smooth = np.linspace(0.1, 1.0, 100)

    # Generate y values for smooth curve
    y_smooth = poly_func(x_smooth, *popt)
    

    # Perform interpolation with the normalized
    normalized_rf = np.interp(normalized_ice_particle_number, x_smooth, y_smooth)


    return normalized_rf

def update_emission_factors (N_YEARS, ANNUAL_EFFICIENCY_CHANGE, SOOT_PARTICLE_ESTIMATE_PER_KM_2025, SAF_SOOT_PARTICLE_REDUCTION, show_plots = False, tech="SAF"): 

    """

    Function to update emission factors for Contrail Cirrus and C-C based on soot particle emissions and associated ice particle formation per km of distance flown.

    The references used for this are: Karcher (2018) and Markl et. al. (2024) 

    Params:
    - SAF_FACTORS: Dictionary with multipliers for SAF emissions adopted from Brazzola et. al. 2024
    - FOSSIL_FACTORS: Dictionary with multipliers for fossil emissions, initially set to 1 as the baseline.
    - N_YEARS: Number of years for which the emissions are to be calculated
    - ANNUAL_EFFICIENCY_CHANGE: Annual efficiency change for aviation
    - SOOT_PARTICLE_ESTIMATE_PER_KM_2025: Estimate of soot particles emitted per km of distance flown in 2025
    - SAF_SOOT_PARTICLE_REDUCTION: Reduction in soot particles due to SAF
    - show_plots: Whether to show plots for new ice particles. Default is False.
    - tech: Technology for which the emissions are to be calculated. Default is SAF.

    Returns:
    - Updated SAF_FACTORS dictionary with new multipliers for Contrail Cirrus and C-C emissions
    - Updated FOSSIL_FACTORS dictionary with new multipliers for Contrail Cirrus and C-C emissions

    """

    efficiency_improvement_factor = ((1-ANNUAL_EFFICIENCY_CHANGE) ** N_YEARS) # Improvement in combustion efficiency reduces soot particle emissions

    SOOT_PARTICLE_ESTIMATE_PER_KM_2025 = np.array(SOOT_PARTICLE_ESTIMATE_PER_KM_2025)
    # Estimate Ice particles in 2025 based on soot particles emitted per km of distance flown and Karcher (2018) Fig 3
    ICE_PARTICLE_ESTIMATE_PER_KM_2025 = [get_nucleated_ice_crystals(p_count,plot=show_plots) for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2025]

    # New soot particle count for 2050 based on efficiency improvement in burn,
    SOOT_PARTICLE_ESTIMATE_PER_KM_2050 = SOOT_PARTICLE_ESTIMATE_PER_KM_2025 * efficiency_improvement_factor
    ICE_PARTICLE_ESTIMATE_PER_KM_2050 = [get_nucleated_ice_crystals(p_count,plot=show_plots) for p_count in SOOT_PARTICLE_ESTIMATE_PER_KM_2050]
    ICE_PARTICLE_ESTIMATE_PER_KM_2050 = np.array(ICE_PARTICLE_ESTIMATE_PER_KM_2050)

    if tech == "SAF":
        future_soot_particles = SOOT_PARTICLE_ESTIMATE_PER_KM_2050 * (1-SAF_SOOT_PARTICLE_REDUCTION) # Markl 2024

    elif tech == "Fossil":
        future_soot_particles = SOOT_PARTICLE_ESTIMATE_PER_KM_2050


    future_nucleated_ice_particles = [get_nucleated_ice_crystals(p_count,plot=show_plots) for p_count in future_soot_particles]
    future_nucleated_ice_particles = np.array(future_nucleated_ice_particles)


    normalised_nucleated_ice_particles = future_nucleated_ice_particles / ICE_PARTICLE_ESTIMATE_PER_KM_2050

    vectorized_calculate_normalised_rf = np.vectorize(calculate_normalised_rf)
    rf_factors = vectorized_calculate_normalised_rf(normalised_nucleated_ice_particles)
    nominal_rf_factor = np.median(rf_factors)
    std_rf_factor = np.std(rf_factors)
    new_contrail_factor = ufloat(nominal_rf_factor, std_rf_factor)

    return new_contrail_factor









        

