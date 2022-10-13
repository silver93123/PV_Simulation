import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib as pv
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as TMP
from pvlib.temperature import sapm_cell_from_module as TMP_sandia
from pvlib import pvsystem, modelchain, location

#%%

def find_PV(Power, ef, type_cell, PVArea): # type_cell = ['Mono-c-Si', 'Multi-c-Si', 'Thin Film', 'CdTe', 'CIGS']
    List_modules = pv.pvsystem.retrieve_sam('CECMod') # 모듈 및 인버터 목록 불러오기
    A_cec_List_modules_T = List_modules.T
    module_maching_list =  A_cec_List_modules_T[(A_cec_List_modules_T['STC'] > Power-Power*0.01) &
                               (A_cec_List_modules_T['STC'] < Power+Power*0.01) &
                               (A_cec_List_modules_T['Technology'] == type_cell)
                               ]
    ef_list =  module_maching_list['STC']/(module_maching_list['Length']*module_maching_list['Width'])/1000
    module_name = ef_list[(ef_list> ef-ef*0.03) & (ef_list< ef+ef*0.03)].iloc[[0]].index[0]
    module_parameters = List_modules[module_name]
    modules_per_string = PVArea // module_parameters['A_c']  # 스트링당 모듈개수
    return module_parameters, modules_per_string
def find_inverter(module_parameters, strings, modules_per_string):  # type_cell = ['Mono-c-Si', 'Multi-c-Si', 'Thin Film', 'CdTe', 'CIGS']
    List_inverters = pv.pvsystem.retrieve_sam('CECInverter')
    inverter_capacity = modules_per_string * strings * module_parameters['STC']
    inverter_MpptV = module_parameters['V_mp_ref'] * modules_per_string
    filter_inverter = ((int(inverter_capacity) < List_inverters.loc['Paco']) & (
                List_inverters.loc['Mppt_low'] < int(inverter_MpptV)) &
                       (List_inverters.loc['Mppt_high'] > int(inverter_MpptV)))
    inverter_name = filter_inverter[filter_inverter == True].index[0]
    inverter = List_inverters[inverter_name]  # 만약 특정 인버터를 선택한다면 'inverter_name'에 인버터 모델명 입력
    return inverter, inverter_capacity