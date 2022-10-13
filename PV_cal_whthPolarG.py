import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib as pv
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as TMP
from pvlib.temperature import sapm_cell_from_module as TMP_sandia
from pvlib import pvsystem, modelchain, location
import PV_model.Model_Sandia as model
import matplotlib
matplotlib.use('Qt5Agg')

#%% 위치 및 시간정보 입력
latitude, longitude = 36, 127
timezone = 'Asia/Seoul'
times = pd.date_range('2019-01-01 06:00', '2019-01-04 18:00', freq='10min', tz=timezone)

#%% 기상조건 읽기
source_ir, region_ir = 'KSES', 'DAEJEON'
df_ir_all = pd.read_excel('df_ir_all.xlsx')
df_ir = df_ir_all[(df_ir_all['Source']==source_ir) & (df_ir_all['region']==region_ir) ].reset_index(drop=True)
df_weather = pd.concat([df_ir, pd.read_excel('KSES_weather.xlsx')], axis=1)

times_s = pd.date_range('2019-01-01 01:00', '2020-01-01 00:00', freq='1H', tz=timezone)
df_weather.index = times_s
weather_KSES = df_weather[['ghi', 'dni', 'dhi', 'wind_speed','temp_air']]

#%% PV 시뮬레이션 조건 ('Noene'은 기본값)
range_az =  np.linspace(0,360,19)
range_tilt = np.linspace(0,90,10)
module_height, PVArea = 1, 10
temperature_model_parameters = TMP['sapm']['open_rack_glass_polymer']          #후면조건[개방: 'freestanding',부착: 'insulated']
module_type = 'glass_glass'
strings= 1

PV_info = model.find_PV(200, 0.16, 'Mono-c-Si', PVArea)
PV_selected, modules_per_string = PV_info
inverter_selected, inverter_capacity = model.find_inverter(PV_selected, strings, modules_per_string)
albedo, surface_type, array_losses_parameters = None, None, None

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

#%% Run(일사량의 경우 ClearSky모델에 의해 청천공 기준으로 계산됩니다)
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

#%% 결과 정리

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