#!/usr/bin/env python
import argparse
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import random
import tempfile

def set_up_dirs(subject, folder):
  mkdirp(subject + folder +  '/NUC')                
  return 
  
def nlreg(subject):
  if not os.path.exists(subject + '/'):
    mkdirp(subject)
    mkdirp(subject + '/time1')
    mkdirp(subject + '/time2')
    mkdirp(subject + '/longitudinal')
    set_up_dirs(subject, '/time1') 
    set_up_dirs(subject, '/time2') 
  return 


def preprocess_time2(inputname):
  execute('nu_correct %s/time2/%s.mnc %s/time2/%s_nuc.mnc' %(inputname, inputname, inputname, inputname))
  return


def longitudinal(inputname):
  # rigid body 6-parameter transformation of time2_nuc to time1_lsq12 
  execute('bestlinreg -lsq6 -clob %s/time2/%s_nuc.mnc %s/time1/%s_lsq12.mnc time2to1.xfm'%(inputname, inputname, inputname, inputname, inputname))  
  execute('mincresample -transformation time2to1.xfm time2_nuc.mnc time2_rigid.mnc -like time1_lsq12.mnc')


  # nonlinear registration of time1_lsq12 to time2_rigid 
  execute('mincANTS 3 -m PR[time1_lsq12.mnc,time2_rigid.mnc,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s/longitudinal/time1to2_nlin.xfm \
      -i 100x100x100x20'%(inputname)) # use the grid from this (=Displacement volume)
  

  # Jacobian determinant of the deformation field (to detect volumetric changes)
  execute('mincblob -determinant long/time1to2_nlin_grid_0.mnc long/det.mnc')

  # warp back to the nonlinear from time1 ??? model space
  execute('mincANTS 3 -m PR[det.mnc,nonlin4avg.mnc,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o long/det2model_nlin.xfm \
      -i 100x100x100x20')
  execute('mincresample -transformation det2model.xfm det.mnc det2model.mnc -like model.mnc')
  
  # blur
  execute('mincblur -fwhm 4 det2model.mnc det1')
  execute('mincblur -fwhm 6 det1_blur.mnc det2')
  execute('mincblur -fwhm 8 det2_blur.mnc det3')
  return



"""
Symmetrical analysis

-papers??

"""




if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess_time2':
    preprocess_time2(sys.argv[2])
  if cmd == 'longitudinal':
    longitudinal(sys.argv[2])
