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

    input_abatement_cost_short = input_abatement_cost[input_abatement_cost[year_col] < 2031]
    input_abatement_cost_long = input_abatement_cost[input_abatement_cost[year_col] == 2050] 

    input_abatement_cost_short = input_abatement_cost_short[cost_col].describe()
    input_abatement_cost_long = input_abatement_cost_long[cost_col].describe()

    yearly_abatement_cost = {}
    yearly_abatement_cost['25%'] = np.linspace(input_abatement_cost_short['25%'], input_abatement_cost_long['25%'], 25)
    yearly_abatement_cost['75%'] = np.linspace(input_abatement_cost_short['75%'], input_abatement_cost_long['75%'], 25) 

    return yearly_abatement_cost

# Example Usage
abatement_cost_saf = load_input_abatement_cost("data/Master Standardisation_SAF.xlsx", tech='SAF')
abatement_cost_daccs = load_input_abatement_cost("data/Master Standardisation DACCS.xlsx", tech='DACCS')



 


    