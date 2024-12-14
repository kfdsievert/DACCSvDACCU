
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
        year_col = "Year of Assumption in Study"
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

    base_inputs = pd.read_excel(file_path, sheet_name='base_input_brazzola', index_col=0)

    # Select all rows but only the first two columns
    base_inputs = base_inputs.iloc[:, :2]

    return base_inputs

# Example Usage
abatement_cost_saf = load_input_abatement_cost("data/Master Standardisation_SAF.xlsx", tech='SAF')
abatement_cost_daccs = load_input_abatement_cost("data/Master Standardisation DACCS.xlsx", tech='DACCS')


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
    demand_growth_vector = (1 + DEMAND_GROWTH_RATE) ** np.arange(N_YEARS)
    efficiency_growth_vector = (1 - ANNUAL_EFFICIENCY_CHANGE) ** np.arange(N_YEARS)

    # Fuel demand is affected by both growth in demand and efficiency improvements
    demand_ej_vector = initial_demand_ej * demand_growth_vector * efficiency_growth_vector
    # Kilometre demand is only affected by growth in demand
    demand_km_vector = initial_demand_km * demand_growth_vector

    # Create output DataFrame
    df_output = pd.DataFrame({
        'DEMAND_EJ': demand_ej_vector,
        'DEMAND_M_KM': demand_km_vector
    }, index=range(2025, 2025+N_YEARS))

    return df_output









