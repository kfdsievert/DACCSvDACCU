import xlwings as xw
import time
import os

sensitivity_scenarios = {
    "Default": { 
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282}, 
                 "2050" : {"low": 147, "median" : 260, "high" : 495}},
        "electricity_price" : 39, #$/MWh
        "fuel_price" : 0.8 #$/l

    },

    "HF" : { 
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 147, "median" : 260, "high" : 495}},
        "electricity_price" : 39, #$/MWh
        "fuel_price" : 1.7 #$/l
    },

    "HF_LE" : {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 131, "median" : 260, "high" : 480}},
        "electricity_price" : 11, #$/MWh
        "fuel_price" : 1.7 #$/l
    },

    "HF_LE_CA": {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 131, "median" : 260, "high" : 480}},
        "electricity_price" : 11, #$/MWh
        "fuel_price" : 1.7 #$/l
    }, 

    "HF_CA": {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 147, "median" : 260, "high" : 495}},
        "electricity_price" : 39, #$/MWh
        "fuel_price" : 1.7 #$/l
    },

    "LE_CA": {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 131, "median" : 260, "high" : 480}},
        "electricity_price" : 11, #$/MWh
        "fuel_price" : 0.8 #$/l

    },

    "LE": {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 131, "median" : 260, "high" : 480}},
        "electricity_price" : 11, #$/MWh
        "fuel_price" : 0.8 #$/l

    },

    "CA": {
        "lcor" :{"2024" : {"low": 295, "median" : 440, "high" : 1282},
                    "2050" : {"low": 147, "median" : 260, "high" : 495}},
        "electricity_price" : 39, #$/MWh
        "fuel_price" : 0.8 #$/l

    }

}


input_path_saf = r"Sensitivity\Harmonization_SAF\Harmonization Sheets"

master_path_saf = os.path.join(input_path_saf,"Master Standardisation_SAF.xlsx")


sheets_to_update_saf = [
    "Brazzola_2024_Harmonization.xlsx", "Gray_2024_Harmonization.xlsx", "Marchese_2021_Harmonization.xlsx", "Martin_2023_Harmonization.xlsx",
    "Moretti_2023_Harmonization.xlsx", "Peacock_2024_Harmonization.xlsx", "Schmidt_Concawe_2024_Harmonization.xlsx", "Seymour_2024_Harmonization.xlsx",  "Sherwin_2022_Harmonization.xlsx"
]
result_sheets = {"low":"Low CO2", "median":"Median CO2", "high":"High CO2"}

for scenario in sensitivity_scenarios:
    for lcor_level in result_sheets.keys():

        wb = xw.Book(str(master_path_saf))
        ws = wb.sheets['Inputs']

        ws.range("C10").value = sensitivity_scenarios[scenario]["electricity_price"]
        ws.range("C19").value = sensitivity_scenarios[scenario]["fuel_price"]

        ws.range("C33").value = sensitivity_scenarios[scenario]["lcor"]["2024"][lcor_level]
        ws.range("C34").value = sensitivity_scenarios[scenario]["lcor"]["2050"][lcor_level]

        wb.save()
        wb.close()


        for path in sheets_to_update_saf: 
            wb = xw.Book(os.path.join(input_path_saf, path))

            time.sleep(3)

            wb.save()
            wb.close()

        wb = xw.Book(str(master_path_saf))
        results_ws = wb.sheets["Standardization Results"]
        result_sheet = result_sheets[lcor_level]

        time.sleep(3) 
        
        # Copy results to corresponding result sheet

        source_range = results_ws.range("A1:T50")
        result_values = source_range.value


        # Paste into the correct result sheet (value only)
        target_ws = wb.sheets[result_sheet]
        target_ws.range("A1").options(transpose=False).value = result_values

        wb.save()
        wb.close()

        print("Update complete for scenario: ", scenario, " and lcor level: ", lcor_level)
    print()
    print("Ensure that you close all open Excel windows before proceeding.")

    # Pause for user input 
    user_input = input("Type Y to continue or N to stop: ").strip().upper()
    if user_input == "y":
        continue
    elif user_input == "n":
        break
        

