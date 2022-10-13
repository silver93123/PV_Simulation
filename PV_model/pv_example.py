import pandas as pd
import matplotlib.pyplot as plt
import pvlib as pv
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as TMP
from pvlib import pvsystem, modelchain, location
import matplotlib
matplotlib.use('Qt5Agg')
#%%
#모듈 및 인버터 목록 불러오기
List_modules = pv.pvsystem.retrieve_sam('CECMod')
A_cec_List_modules_T = List_modules.T
List_inverters = pv.pvsystem.retrieve_sam('CECInverter')
A_cec_List_inverters_T = List_inverters.T

#%%
#위치 및 시간정보 입력
latitude, longitude = 36, 127                                                                 #위치정보: 위도, 경도
timezone = 'Asia/Seoul'                                                                       #타임존
times = pd.date_range('2019-01-01 06:00', '2019-01-04 18:00', freq='10min', tz=timezone)      #(시작시간, 종료시간, 시간간격)

#%%
# 기상조건 읽기
source_ir, region_ir = 'KSES', 'DAEJEON'
df_ir_all = pd.read_excel('df_ir_all.xlsx')
df_ir = df_ir_all[(df_ir_all['Source']==source_ir) & (df_ir_all['region']==region_ir) ].reset_index(drop=True)
df_weather = pd.read_excel('KSES_weather.xlsx', )
df_weather = pd.concat([df_ir, df_weather], axis=1)

times_s = pd.date_range('2019-01-01 01:00', '2020-01-01 00:00', freq='1H', tz=timezone)
df_weather.index = times_s

weather_KSES = df_weather[['ghi', 'dni', 'dhi', 'wind_speed','temp_air']]

#%%

#설치정보('Noene'은 기본값)
name = ['South-30 Array', 'South-90 Array','North-30 Array', 'North-90 Array',
        'East-90 Array', 'West-90 Array']  #어레이 명칭
surface_tilt = [30, 90, 30, 90, 90, 90]                                              #어레이 고도각(지면과 평행 = 0)
surface_azimuth = [180, 180, 0, 0, 90, 270]                                         #어레이 방위각(북쪽(0)으로부터 시계방향)
module_height = [1, 1, 1, 1, 1, 1]                                                #어레이 높이(m)
PVArea = [10, 10, 10, 10, 10, 10]                                                    #어레이 설치면적(㎡)
temperature_model_parameters = TMP['pvsyst']['insulated']                #후면조건[개방: 'freestanding',부착: 'insulated']
albedo = None                                                            #지면 반사율
surface_type = None                                                      #지면 종류

#모듈 정보 입력(현재 설정-효율:20.0%, STC_Power=400.32W)
module_type = 'glass_glass'                                              #모듈 타입
module_parameters = List_modules['LG_Electronics_Inc__LG400N2C_A5']
modules_per_string= [i//module_parameters['A_c'] for i in PVArea]        #스트링당 모듈개수
strings= [1, 1, 1, 1, 1, 1]                                                       #스트링 개수
#%%
#인버터 입력(입력된 모듈정보에 따라 자동선택됨)
inverter_capacity = [i*j*module_parameters['STC'] for i, j in zip(modules_per_string, strings)]
inverter_MpptV = [module_parameters['V_mp_ref']*i for i in modules_per_string]
filter_inverter = [((int(i) < List_inverters.loc['Paco']) & (List_inverters.loc['Mppt_low'] < int(j)) &
                (List_inverters.loc['Mppt_high'] > int(j)))
               for i, j in zip(inverter_capacity, inverter_MpptV)]
inverter_name = [i[i == True ].index[0] for i in filter_inverter]
inverter = List_inverters[inverter_name]      #만약 특정 인버터를 선택한다면 'inverter_name'에 인버터 모델명 입력

array_losses_parameters = None
#어레이 구성부
arrays = []
for n, t, a, h, s_m, s in zip(name, surface_tilt, surface_azimuth, module_height, modules_per_string, strings):
    array_kwargs = dict(
        name=n,
        modules_per_string=s_m,
        strings=s,
        albedo=albedo,
        surface_type=surface_type,
        module=module_parameters,
        module_type=module_type,
        module_parameters=module_parameters,
        temperature_model_parameters=temperature_model_parameters,
        array_losses_parameters=array_losses_parameters
    )
    arrays.append(pvsystem.Array(pvsystem.FixedMount(t, a, module_height =h), **array_kwargs))
#%%
#시스템 구성(일사량의 경우 ClearSky모델에 의해 청천공 기준으로 계산됩니다)
loc = location.Location(latitude, longitude)
weather = loc.get_clearsky(times)

df_result = pd.DataFrame()
result_pv_l = []
for j in range(len(inverter_name)):
    system = pvsystem.PVSystem(arrays=[arrays[j]], inverter_parameters=inverter.iloc[:, j])
    mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')
    result_pv = mc.run_model(weather_KSES)
    result_pv_l.append(result_pv)
    dict_result = {'name': [arrays[j].name], 'DC_sum': [result_pv.results.dc['p_mp'].sum()],
                   'Temp_Aver': [result_pv.results.cell_temperature.mean()]}
    df_result = pd.concat([df_result, pd.DataFrame(dict_result)])

result_pv_ac = pd.concat([result_pv_l[i].results.ac for i in range(len(inverter_name))],
                         axis=1, ignore_index=True).apply(pd.to_numeric)
result_pv_ac[result_pv_ac < 0] = 0
result_pv_ac_sum = result_pv_ac.sum(axis=1)


#%%

#결과 요약
result_pv_ac_sum_h = result_pv_ac_sum.resample('H').sum()
Area_pv = [i*module_parameters['A_c'] for i in modules_per_string]
df_result_sum = pd.DataFrame()
for j in range(len(inverter_name)):
    dc = result_pv_l[j].results.dc['p_mp'].resample('H').sum()
    ac = result_pv_ac[j].resample('H').sum()
    name = f'{arrays[j].name}'
    result_sum = {
        'Array' : [name],
        'Area[㎡]':[round(Area_pv[j],2)],
        'AC[kWh]': [round(ac.sum() / 1000,2)],
        'DC[kWh]': [round(dc.sum() / 1000,2)],
        'Module_Capacity[kW]': [round(inverter_capacity[j]/1000,2)],
        'StartTime': [round(inverter_capacity[j] / 1000, 2)],
    }
    df_result_sum = pd.concat([df_result_sum,pd.DataFrame(result_sum)])
#%%

#결과 확인
fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True)
for j in range(len(inverter_name)):
    ax1.plot(result_pv_l[j].results.dc['p_mp'], label=(f'{arrays[j].name}'+'_DC'), linestyle='--')
    ax1.plot(result_pv_ac[j], label=(f'{arrays[j].name}'+'_AC'), linestyle='-')
ax1.plot(result_pv_ac_sum, label='AC_TotalOutput')
ax1.set(ylabel='System Output[W]')
ax1.legend()
for j in range(len(inverter_name)):
    ax2.plot(result_pv_l[j].results.effective_irradiance, label=(f'{arrays[j].name}'))
ax2.plot(weather['ghi'], label='GHI')
ax2.set(ylabel='Irradiance[W/m²]')
ax2.legend()
for j in range(len(inverter_name)):
    ax3.plot(result_pv_l[j].results.cell_temperature, label=(f'{arrays[j].name}'))
ax3.set(ylabel='Temperature[℃]')
ax3.legend()
dd =pd.Timedelta('2019-01-01 06:00', '2019-01-04 18:00', unit='days')
#%%
# 1. 발전량
fig, ax = plt.subplots()
for j in range(len(inverter_name)):
    plt.plot(result_pv_l[j].results.dc['p_mp'], label=(f'{arrays[j].name}'+'_DC'), linestyle='--')
    plt.plot(result_pv_ac[j], label=(f'{arrays[j].name}'+'_AC'), linestyle='-')
plt.plot(result_pv_ac_sum, label='AC_TotalOutput')
plt.ylabel('System Output[W]')
# plt.legend()
#%%
# 2. 일사량
fig, ax = plt.subplots()
for j in range(len(inverter_name)):
    plt.plot(result_pv_l[j].results.effective_irradiance, label=(f'{arrays[j].name}'))
plt.plot(weather['ghi'], label='GHI')
plt.ylabel('Irradiance[W/m²]')
plt.legend()
#%%
# 3. 모듈 온도
fig, ax = plt.subplots()
for j in range(len(inverter_name)):
    plt.plot(result_pv_l[j].results.cell_temperature, label=(f'{arrays[j].name}'))
plt.ylabel('Temperature[℃]')
plt.legend()

#%% 결과 종합
name = ['South-30 Array', 'South-90 Array','North-30 Array', 'North-90 Array',
        'East-90 Array', 'West-90 Array']

df_dc = pd.DataFrame(columns=name)
df_ac = pd.DataFrame(columns=name)
df_temp = pd.DataFrame(columns=name)
df_ir_POA = pd.DataFrame(columns=name)

for i,n in enumerate(name):
    df_dc[n] = result_pv_l[i].results.dc['p_mp']
    df_ac[n] = result_pv_ac[i]
    df_temp[n] = result_pv_l[i].results.cell_temperature
    df_ir_POA[n] = result_pv_l[i].results.effective_irradiance