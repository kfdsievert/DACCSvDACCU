import xlwings as xw
import time
import os


input_path_daccs = r"Sensitivity\Harmonization_DACCS"

master_path_daccs = os.path.join("Master Standardisation DACCS.xlsx")

sheets_to_update_daccs = [r"\Young2023\Young2023_Harmonization_done_ambientw_2050.xlsx", 
                          r"\Young2023\Young2023_Harmonization_done_electrochemLS_2050.xlsx",
                          r"\Young2023\Young2023_Harmonization_done_liquisolvent_2050.xlsx",
                          r"\Young2023\Young2023_Harmonization_done_solid sorbent_2050.xlsx",
                          "Fasihi2019_Harmonization_done.xlsx","Pett-Ridge_204_Liquid_Solvent_Harmonization_done.xlsx",
                          "Pett-Ridge2024_Solid_Harmonization_done.xlsx","Keith2018_Harmonization_done.xlsx"]