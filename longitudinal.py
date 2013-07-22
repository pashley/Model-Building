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
  execute('nu_correct inputs/%s.mnc %s/NUC_time2/%s.mnc' %(inputname, inputname[0:-2], inputname))
  return


def longitudinal(inputname):
  # rigid body 6-parameter transformation of time2_nuc to time1_lsq12 
  execute('bestlinreg -lsq6 -clob %s/NUC_time2/%s.mnc %s/output_lsq12/%s_lsq12.mnc %s/lin_tfiles/time2to1.xfm'%(inputname[0:-2], inputname, inputname[0:-2], inputname[0:-2], inputname[0:-2]))  
  execute('mincresample -transformation %s/lin_tfiles/time2to1.xfm %s/NUC_time2/%s.mnc %s/output_lsq6/time2_lsq6.mnc -like %s/output_lsq12/%s_lsq2.mnc' 
          %(inputname[0:-2], inputname[0:-2], inputname, inputname[0:-2], inputname[0:-2], inputname[0:-2]))


  # nonlinear registration of time1_lsq12 to time2_rigid 
  execute('mincANTS 3 -m PR[%s/output_lsq12/%s_lsq12.mnc, %s/output_lsq6/time2_lsq6.mnc,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s/time1to2_nlin.xfm \
      -i 100x100x100x20'%(inputname[0:-2], inputname[0:-2], inputname[0:-2], inputname[0:-2])) # use the grid from this (=Displacement volume)
  

  # Jacobian determinant of the deformation field (to detect volumetric changes)
  execute('mincblob -determinant %s/time1to2_nlin_grid_0.mnc %s/det.mnc' %(inputname[0:-2], inputname[0:-2]))

  # warp back to the nonlinear from time1 ??? model space
  execute('mincANTS 3 -m PR[%s/det.mnc,avgimages/nonlin4avg.mnc,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s/det2model_nlin.xfm \
      -i 100x100x100x20' %(inputname[0:-2], inputname[0:-2]))
  execute('mincresample -transformation %s/det2model_nlin.xfm %s/det.mnc %s/det2model.mnc -like avgimages/nonlin4avg.mnc' %(inputname[0:-2], inputname[0:-2], inputname[0:-2]))
  
  # blur
  #execute('mincblur -fwhm 4 det2model.mnc det1')
  #execute('mincblur -fwhm 6 det1_blur.mnc det2')
  #execute('mincblur -fwhm 8 det2_blur.mnc det3')
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
