import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib as pv
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as TMP
from pvlib import pvsystem, modelchain, location
import matplotlib
matplotlib.use('Qt5Agg')

# SAPM: Sandia PV Array Performance Model
#%%
def find_PV(Power, ef,type_cell): # type_cell = ['Mono-c-Si', 'Multi-c-Si', 'Thin Film', 'CdTe', 'CIGS']
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

#%% 위치 및 기상조건 입력
latitude, longitude = 36, 127                                                                 #위치정보: 위도, 경도
timezone = 'Asia/Seoul'                                                                       #타임존
times = pd.date_range('2019-01-01 06:00', '2019-01-04 18:00', freq='10min', tz=timezone)      #(시작시간, 종료시간, 시간간격)
source_ir, region_ir = 'KSES', 'DAEJEON'
df_ir_all = pd.read_excel('df_ir_all.xlsx')
df_ir = df_ir_all[(df_ir_all['Source']==source_ir) & (df_ir_all['region']==region_ir) ].reset_index(drop=True)
df_weather = pd.concat([df_ir, pd.read_excel('KSES_weather.xlsx')], axis=1)

times_s = pd.date_range('2019-01-01 01:00', '2020-01-01 00:00', freq='1H', tz=timezone)
df_weather.index = times_s
weather_KSES = df_weather[['ghi', 'dni', 'dhi', 'wind_speed','temp_air']]

#%% PV 시뮬레이션 조건
#설치정보('Noene'은 기본값)
range_az =  np.linspace(0,360,13)
range_tilt = np.linspace(0,90,4)
module_height, PVArea = 1, 10                                    #어레이 높이(m), 어레이 설치면적(㎡)
# temperature_model_parameters = TMP['pvsyst']['freestanding']                #후면조건[개방: 'freestanding',부착: 'insulated']
temperature_model_parameters = TMP['sapm']['open_rack_glass_polymer']          #후면조건[개방: 'freestanding',부착: 'insulated']
#모듈 정보 입력(현재 설정-효율:20.0%, STC_Power=400.32W)
module_type = 'glass_glass'                                              #모듈 타입
strings= 1

PV_info = find_PV(200, 0.16, 'Mono-c-Si')
PV_selected, modules_per_string = PV_info
inverter_selected, inverter_capacity = find_inverter(PV_selected, strings, modules_per_string)
albedo = None                                                            #지면 반사율
surface_type = None                                                      #지면 종류
array_losses_parameters = None
#%% 어레이 구성부

arrays = []
for a in range_az:
    for t in range_tilt:
        array_kwargs = dict(
            name='az:'+str(a)+'_tilt:'+str(t),
            modules_per_string=modules_per_string,
            strings=strings,
            albedo=albedo,
            surface_type=surface_type,
            module=PV_selected,
            module_type=module_type,
            module_parameters=PV_selected,
            temperature_model_parameters=temperature_model_parameters,
            array_losses_parameters=array_losses_parameters
        )
        arrays.append(pvsystem.Array(pvsystem.FixedMount(t, a, module_height =module_height), **array_kwargs))
#%%
#시스템 구성(일사량의 경우 ClearSky모델에 의해 청천공 기준으로 계산됩니다)
loc = location.Location(latitude, longitude)
weather = loc.get_clearsky(times)

df_result = pd.DataFrame()
result_pv_l = []
for j in range(len(arrays)):
    system = pvsystem.PVSystem(arrays=[arrays[j]], inverter_parameters=inverter_selected)
    mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')
    result_pv = mc.run_model(weather_KSES)
    result_pv_l.append(result_pv)
    dict_result = {'name': [arrays[j].name], 'DC_sum': [result_pv.results.dc['p_mp'].sum()],
                   'Temp_Aver': [result_pv.results.cell_temperature.mean()]}
    df_result = pd.concat([df_result, pd.DataFrame(dict_result)])
    print(round(j/len(arrays),2))
result_pv_ac = pd.concat([result_pv_l[i].results.ac for i in range(len(arrays))],
                         axis=1, ignore_index=True).apply(pd.to_numeric)
result_pv_dc = pd.concat([result_pv_l[i].results.dc for i in range(len(arrays))],
                         axis=1, ignore_index=True).apply(pd.to_numeric)
result_pv_ac[result_pv_ac < 0] = 0
result_pv_ac_sum = result_pv_ac.sum(axis=1)

#%% #결과 요약

result_pv_ac_sum_h = result_pv_ac_sum.resample('H').sum()
Area_pv = modules_per_string*PV_selected['A_c']
df_result_sum = pd.DataFrame()
for j in range(len(arrays)):
    dc = result_pv_l[j].results.dc['p_mp'].resample('H').sum()
    ac = result_pv_ac[j].resample('H').sum()
    name = f'{arrays[j].name}'
    result_sum = {
        'Array' : [name],
        'Tilt': [arrays[j].mount.surface_tilt],
        'Az': [arrays[j].mount.surface_azimuth],
        'Area[㎡]':[round(Area_pv,2)],
        'AC[kWh]': [round(ac.sum() / 1000,2)],
        'DC[kWh]': [round(dc.sum() / 1000,2)],
        'Module_Capacity[kW]': [round(inverter_capacity/1000,2)],
        'Cell_Temperature': [round(result_pv_l[j].results.cell_temperature.mean(), 2)],
        'StartTime': [round(inverter_capacity / 1000, 2)],
    }
    df_result_sum = pd.concat([df_result_sum,pd.DataFrame(result_sum)])
#%% 그래프
col_l = ['AC[kWh]','Cell_Temperature']
n_interval = 10
PolarGraph(df_result_sum, col_l,range_tilt, range_az, n_interval)

# #%%
# df_close = pd.read_csv('./result/df_result_close_sandia.csv', index_col=0)
# df_open = pd.read_csv('./result/df_result_open_sandia.csv', index_col=0)
# df_delta = df_close[['AC[kWh]', 'Tilt', 'Az']]
# df_delta['AC[kWh]'] = df_open['AC[kWh]'] - df_close['AC[kWh]']
# df_delta['Cell_Temperature'] = df_close['Cell_Temperature'] - df_open['Cell_Temperature']
# #%% 그래프
# df_des = pd.DataFrame()
# for j in ['AC[kWh]','Cell_Temperature']:
#     for i,n in zip([df_open, df_close],['Open','Close']):
#         df_des[n+':'+j]=i[j].describe()

