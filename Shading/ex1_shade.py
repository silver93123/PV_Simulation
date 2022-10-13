import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import os
import scipy.stats as stats
import matplotlib
matplotlib.use('Qt5Agg')

#%% 회전변환
def matrix_rotation_xz(angle_x, angle_z):
    rotation_x = np.array([[1, 0, 0],
                           [0, np.cos(angle_x), -1*np.sin(angle_x)],
                           [0, np.sin(angle_x), np.cos(angle_x)]])
    # rotation_y = np.array([[np.cos(angle_z), 0, np.sin(angle_z)],
    #                        [0, 1, 0],
    #                        [-1*np.sin(angle_z), 0, np.cos(angle_z)]])
    rotation_z = np.array([[np.cos(angle_z), -np.sin(angle_z), 0],
                           [np.sin(angle_z), np.cos(angle_z), 0],
                           [0, 0, 1]])
    rotation = rotation_x.dot(rotation_z)
    return rotation

class PV_surface:
    def __init__(self,point_0, size_h, size_d, tilt_sur,azi_sur ,v_norm):
        self.point_0 = point_0
        rotation_xz = matrix_rotation_xz(tilt_sur+np.pi, azi_sur+np.pi/2)
        self.point_1 = np.array([0,0,0]).dot(rotation_xz)
        self.point_2 = np.array([size_d,0,0]).dot(rotation_xz)
        self.point_3 = np.array([0,size_h,0]).dot(rotation_xz)
        self.point_4 = np.array([size_d,size_h,0]).dot(rotation_xz)
        self.v_norm = v_norm
        self.v1 = self.point_2 - self.point_1
        self.v2 = self.point_3 - self.point_1
        self.v_n = np.cross(self.v1, self.v2)*self.v_norm
        self.size = (size_h, size_d)
        self.Area_surface = self.size[0]*self.size[1]

        self.X = np.linspace(-size_h, size_h, 10)
        self.Y = np.linspace(-size_h, size_h, 10)
        self.Z = self.v_n[0] * (self.X - self.point_1[0]) + self.v_n[1] * (self.X - self.point_1[1]) - self.v_n[2] * \
            self.point_1[2]

        self.Xm, self.Ym = np.meshgrid(self.X, self.Y)

    def plan_ep(self):
        Z = self.v_n[0] * (self.Xm - self.point_1[0]) + self.v_n[1] * (self.Ym - self.point_1[1]) - self.v_n[2] * self.point_1[2]
        return Z
x0, y0, z0 = np.meshgrid(np.linspace(0, 0, 3),np.linspace(0, 0, 3),np.linspace(0, 0, 3)) # 방위화살표
u0, v0, w0 = 1,0,0
#%%
p1 = np.array([0,0,0])
p2 = np.array([-2,2,0])
p3 = np.array([1,1,0])
p1_  = np.linspace(0,10,11)
p2_  = np.linspace(0,10,11)
px,py = np.meshgrid(p1_, p2_)
#%% (x, y, z)
height, size_h, size_d = 5, 2, 1
angle_tilt, angle_azi = np.pi/3, 0
point_1 = np.array([1,1,2])
surface_1 = PV_surface(point_1, size_h, size_d, angle_tilt, angle_azi, v_norm=1)

#%% 그래프
# fig = plt.figure()
# ax = fig.add_subplot(projection='3d')
# surf = ax.plot_surface(surface_1.Xm, surface_1.Ym, surface_1.plan_ep(), alpha=0.6,
#                        linewidth=0, antialiased=False)
# ax.quiver(x0, y0, z0, u0, v0, w0, length=size_h, normalize=False, color='k')
# ax.set(xlim=(-size_h,size_h), ylim=(-size_h,size_h), zlim=(-size_h,size_h), xlabel='x', ylabel='y', zlabel='z')
#%% 그래프
fig = plt.figure()
ax = fig.add_subplot(projection='3d')
surf1 = ax.scatter(surface_1.point_1[0], surface_1.point_1[1], surface_1.point_1[2], alpha=1,
                       linewidth=0, antialiased=False)
surf2 = ax.scatter(surface_1.point_2[0], surface_1.point_2[1], surface_1.point_2[2], alpha=1,
                       linewidth=0, antialiased=False)
surf3 = ax.scatter(surface_1.point_3[0], surface_1.point_3[1], surface_1.point_3[2], alpha=1,
                       linewidth=0, antialiased=False)
surf4 = ax.scatter(surface_1.point_4[0], surface_1.point_4[1], surface_1.point_4[2], alpha=1,
                       linewidth=0, antialiased=False)
ax.set(xlim=(-size_h,size_h), ylim=(-size_h,size_h), zlim=(-size_h,size_h), xlabel='x', ylabel='y', zlabel='z')

ax.quiver(x0, y0, z0, u0, v0, w0, length=size_h, normalize=False, color='k')


