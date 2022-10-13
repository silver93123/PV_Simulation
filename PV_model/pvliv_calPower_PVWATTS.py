import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pvlib as pv
from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS as TMP
from pvlib import pvsystem, modelchain, location
import matplotlib
matplotlib.use('Qt5Agg')
#%%

a_poa = np.linspace(500,500,100)
ir_ref =1000
temp_cell = np.linspace(30,50,100)
pdc0 = 200
gm_pdc = -0.005
temp_ref = 25

power_cal = pd.Series(pv.pvsystem.pvwatts_dc(g_poa_effective=a_poa, temp_cell=temp_cell, pdc0=pdc0, gamma_pdc=gm_pdc))
print(power_cal)
