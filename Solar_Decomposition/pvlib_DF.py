import matplotlib.pyplot as plt
import pandas as pd
import pvlib as pv
import numpy as np
import pvlib.location as loc
import matplotlib
matplotlib.use('Qt5Agg')

df_1 = pd.read_excel('E_TMY_782 - HWASOON.xlsx',index_col =0 )
latitude, longitude=35.06, 126.98

tz = 'Asia/Seoul'
site = pv.location.Location(latitude, longitude, tz=tz)

datetime = pd.date_range(start='2016-01-01', end='2016-12-30 23:00:00', freq='1h', tz = 'Asia/Seoul')
df_1.index = datetime
solpos = pv .solarposition.get_solarposition(datetime, latitude, longitude)

ghi = df_1['GHI(W/m²)']
solar_zenith = solpos['zenith']
pressure = df_1['Pressure(hPa)']*100
temp_dew = df_1['Temp_dew(℃)']
clearsky = site.get_clearsky(datetime)

DHI_disc = pv.irradiance.disc(ghi, solar_zenith, datetime, pressure=pressure, min_cos_zenith=0.065, max_zenith=87, max_airmass=12)

DNI_dirint = pv.irradiance.dirint(ghi, solar_zenith, datetime, pressure=101325.0, use_delta_kt_prime=True,
                        temp_dew=temp_dew, min_cos_zenith=0.065, max_zenith=87)
DNI_dirindex = pv.irradiance.dirindex(ghi, clearsky['ghi'], clearsky['dni'], solar_zenith, datetime, pressure=pressure,
                          use_delta_kt_prime=True, temp_dew=temp_dew, min_cos_zenith=0.065, max_zenith=87)

dni = pv.irradiance.disc(ghi, solar_zenith, datetime)
dhi = ghi - dni['dni'] * np.cos(np.radians(solar_zenith))

df_r = pd.DataFrame(index=datetime)
df_r['ghi'] = np.linspace(0,0,len(df_r))
df_r.reset_index(inplace=True)

for i in range(len(df_1)):
    month = df_1['m'][i]
    day = df_1['d'][i]
    hour = df_1['h'][i]
    filt = (df_r['index'].dt.month == month) & (df_r['index'].dt.day == day) & (df_r['index'].dt.hour == hour)
    index = df_r[filt]['ghi'].index
    df_r.iloc[index,1]=df_1['ghi'][i]