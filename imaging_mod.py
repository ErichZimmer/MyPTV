#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 18:02:07 2018

@author: ron


Imaging Module:
    
containts the camera and imaging system classes that handle 
the transformation from camera space coordinates to lab coordinates.

"""

import sys, os
from numpy import zeros, array, cos, sin, dot
from numpy.linalg import inv
from utils import *
from cal_image_coords import Cal_image_coord



class img_system(object):
    '''
    an object that holds a number of cameras.
    '''
    
    def __init__(self, camera_list):
        self.cameras = camera_list
    
    
    def stereo_match(self, coords, d_max):
        '''
        given n particle images [(eta, zeta) coords in camera space], this will
        determine whereather there is a good candidate point for the intersection
        of epipolar lines, and if so returns it. Here it is assumed that
        all images correspond to the same "real world" particle.
        This point is estimated as the average of the crossing point of the
        epipolar lines, that cross at distances smaller than a maximum value.
        
        input - 
        coords (dic) - keys are camera number, values are the image space 
                       coordinates of each point. Must have at least 2 entries
        d_max (float) - maximum allowable distance separating two lines
        
        
        output - either -
        X (numpy array, 3) - lab space coordinates of the sought point 
        cams (list) - list of camera indexes for which the point was found
        dist - average distance to crossing points
        
        or - (if all epipolar lines )
        None
        '''
        N = len(coords)
        x = []
        cams = []
        d = []
        keys = list(coords.keys())
        for i in range(N):
            for j in range(i+1,N):
                ki = keys[i]
                O1 = self.cameras[ki].O
                r1 = self.cameras[ki].get_r(coords[ki][0], coords[ki][1])
                
                kj = keys[j]
                O2 = self.cameras[kj].O
                r2 = self.cameras[kj].get_r(coords[kj][0], coords[kj][1])
                
                D, x_ij = line_dist(O1, r1, O2, r2)
                
                if D <= d_max:
                    x.append(x_ij)
                    cams.append(ki)
                    cams.append(kj)
                    d.append(D)

        if len(x)>=1:
            return sum(x)/1.0/len(x), set(cams), sum(d)/1.0/len(x)
        else:
            return None





class camera(object):
    '''
    an object that holds the calibration information for
    each camera. It can be used to:
    1) obtain image coordinates from given lab coordinates. 
    2) vice versa if used together with other cameras at 
       other locations (img_system.stereo_match).
      
    input:
    name - string name for the camera
    resolution - tuple (2) two integers for the camera pixels
    cal_points_fname - path to a file with calibration coordinates for the cam
    '''
    
    def __init__(self, name, resolution, cal_points_fname = None):    
        self.O = zeros(3) + 1.     # camera location
        self.theta = zeros(3) + 1. # rotation angles
        self.f = 1.0               # focal depth
        self.calc_R()
        self.resolution = resolution
        self.give_name(name)
        
        if cal_points_fname is not None:
            cic = Cal_image_coord(cal_points_fname)
            self.image_points = cic.image_coords
            self.lab_points = cic.lab_coords
    
        
    def __repr__(self):
        
        ret = (self.name +
               '\n O: ' + str(self.O) +
               '\n theta:' + str(self.theta) +
               '\n f:' + str(self.f))
        return ret
    
    
    
    def give_name(self, name):
        '''
        adds a name for the camera
        '''
        if type(name) == str:
            self.name = name
        else:
            raise TypeError('name must be string')    
    
    
    def calc_R(self):
        '''
        calculates the rotation matrix for the camera's angles
        '''
        tx,ty,tz = self.theta
        Rx = array([[1,0,0],
                    [0,cos(tx),-sin(tx)],
                    [0,sin(tx),cos(tx)]])
        Ry = array([[cos(ty),0,sin(ty)],
                     [0,1,0],
                     [-sin(ty),0,cos(ty)]])
        Rz = array([[cos(tz),-sin(tz),0],
                    [sin(tz),cos(tz),0],
                    [0,0,1]])
        self.R = dot(dot(Rx,Ry), Rz)
    
    
    def get_r(self, eta, zeta):
        '''
        input - pixel coordinates (eta, zeta) seen by the camera
        output - direction vector in real space
        '''
        self.calc_R()
        eta_ = eta - self.resolution[0]/2.0
        zeta_ = zeta - self.resolution[1]/2.0
        r = dot(array([-eta_, -zeta_, -self.f]), self.R)
        return r
    
    
    def projection(self,x):
        '''
        will return the image coordinate (eta, zeta) of a real point x.
        
        input - x (array,3) - real world coordinates
        output - (eta, zeta) (array,2) - camera coordinates of the projection 
                                         of x
        '''
        v = dot(x - self.O, inv(self.R))
        a = -1.0 * v[2] / self.f
        eta = (-1.0 * v[0]) / a  + self.resolution[0]/2
        zeta = (-1.0 * v[1]) / a  + self.resolution[1]/2
        return array([eta, zeta])
    
    
    def save(self, dir_path = ''):
        '''
        will save the camera on the hard drive
        '''
        full_path = os.path.join(dir_path, self.name)
        
        f = open(full_path, 'w')
        f.write(self.name+'\n')
        
        S = ''
        for s in self.O:
            S+= str(s)+' '
        f.write(S+'\n')
        
        S = ''
        for s in self.theta:
            S+= str(s)+' '
        f.write(S+'\n')
        
        f.write(str(self.f))
        f.close()
        
    def load(self, dir_path):
        '''
        will load camera data from the hard disk
        '''
        full_path = os.path.join(dir_path, self.name)
        
        f = open(full_path, 'r')
        name = f.readline()
        
        S = f.readline()[:-2]
        self.O = array([float(s) for s in S.split()])
        
        S = f.readline()[:-2]
        self.theta = array([float(s) for s in S.split()])
        
        self.f = float(f.readline()[:-2])
        f.close()
        
        self.calc_R()
        
    
    def plot_3D_epipolar_line(self, eta, zeta, zlims, ax=None, color=None):
        '''Will plot a 3D epipolar line for the image point (eta,zeta) in 
        between two given z values.
        
        This requires matplotlib.'''
        
        z0, z1 = zlims
        r = self.get_r(eta, zeta)
        a0 = (z0 - self.O[2])/r[2]
        a1 = (z1 - self.O[2])/r[2]
        x0, x1 = self.O[0]+a0*r[0], self.O[0]+a1*r[0]
        y0, y1 = self.O[1]+a0*r[1], self.O[1]+a1*r[1]
        
        if ax is None:
            from mpl_toolkits import mplot3d
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = plt.axes(projection='3d')
            if color is None:
                ax.plot3D([x0,x1], [z0,z1], [y0,y1])
            else:
                ax.plot3D([x0,x1], [z0,z1], [y0,y1], c=color)
        
            return fig, ax
       
        else:
            if color is None:
                ax.plot3D([x0,x1], [z0,z1], [y0,y1])
            else:
                ax.plot3D([x0,x1], [z0,z1], [y0,y1], c=color)
            
    
    
    
    
    
'''
if __name__ == '__main__':
    from numpy import pi 
    c1 = camera('1', (10,10))
    c2 = camera('2', (10,10))
    c3 = camera('3', (10,10))
    
    c1.O = array([10.0 ,0,0])
    c2.O = array([0,10.0 ,0])
    c3.O = array([10.0,10.0 ,0])
    
    c2.theta[0] = -pi / 2.0
    c1.theta[1] = pi / 2.0
    
    c1.calc_R()
    c2.calc_R()
    c3.calc_R()
    
    x = array([0.0,0.1,0.1])        
    
    imgsys = img_system()
    imgsys.cameras.append(c1)
    imgsys.cameras.append(c2)
    imgsys.cameras.append(c3)
    
    coords = {0: c1.projection(x),
              1: c2.projection(x)*1.01,
              2: c3.projection(x)*0.99}
        
    print(imgsys.stereo_match(coords, 0.5))

'''   
        
        
        
        
        
        
        
