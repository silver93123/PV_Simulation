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
def PolarGraph(df_result,col_l,range_tilt,range_az,n_interval,  ):
    ti, ri= np.meshgrid(np.linspace(0,2 * np.pi,len(range_az)), np.linspace(0,90,len(range_tilt)))
    c_max = [df_result[i].max() for i in col_l]
    c_min = [df_result[i].min() for i in col_l]
    for i, col in zip(range(len(col_l)), col_l):
        ir = df_result[col].to_numpy()
        zi, z0 = np.reshape(ir, (len(range_az), len(range_tilt))).T, np.zeros((len(range_tilt), len(range_az)))
        ax = plt.subplot(1, len(col_l), i + 1, polar=True)
        cax_color_2 = ax.contourf(ti, ri, z0, cmap='Spectral_r', levels=np.linspace(c_min[i], c_max[i], n_interval))
        cax_line = ax.contour(ti, ri, zi, levels=np.linspace(c_min[i], c_max[i], n_interval), linewidths=0.5,
                              colors='k')
        cax_color = ax.contourf(ti, ri, zi, cmap='Spectral_r', levels=np.linspace(c_min[i], c_max[i], n_interval))
        cb = plt.colorbar(cax_color_2, orientation='vertical', shrink=0.5)
        cb.set_label(col, labelpad=10, y=0.5, rotation=90)
        ax.set_title(label=(col))
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)

        ax.set_rticks([0, 30, 60, 90])
        ax.set_rlabel_position(270)
        ax.annotate("Altitude[°]", xy=[np.pi / 180 * 262, 60], rotation=0)
        ax.set_yticks(np.linspace(0, 90, 4))
        ax.set_xticks(np.linspace(0, np.pi * 2 / 12 * 11, 12))
        ax.yaxis.grid(b=True, linestyle='--', color='k', linewidth=0.5)
        ax.xaxis.grid(b=True, linestyle='--', color='k', linewidth=0.5)
        plt.show()
