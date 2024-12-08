import pandas as pd
import numpy as np
import xlsxwriter


def load_input_abatement_cost(file_path, tech):
    """Loads data on abatement costs from master excel sheet and formulates into a dataframe with min, 25%, median, 75%, and max values for each technology."""

    # First row is headers and is skipped
    input_abatement_cost = pd.read_excel(file_path, sheet_name='Standardization Results', skiprows=1, index_col=0)

    # Final cost column varies by technology
    if tech not in ['DACCS', 'SAF']: 
        raise ValueError('Technology not recognized. Please enter either DACCS or SAF.')
    
    if tech == 'DACCS':
        col_name = "Fully Harmonized NET REMOVED COST (incl T&S"
    elif tech == 'SAF':
        col_name = "Fully Harmonized"

    # Create a df to store the min, 25%, median, 75%, and max values for each technology
    abatement_cost = input_abatement_cost[col_name].describe()

    return abatement_cost

# Example Usage
abatement_cost_daccs = load_input_abatement_cost("/Users/yash/Documents/GitHub/DACCSvDACCU/Master Standardisation DACCS.xlsx", tech='DACCS')
abatement_cost_saf = load_input_abatement_cost("/Users/yash/Documents/GitHub/DACCSvDACCU/Master Standardisation_SAF.xlsx", tech='SAF')





    