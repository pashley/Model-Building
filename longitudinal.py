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


# I think ?!

def preprocess_time2(inputname_time2):
  execute('nu_correct inputs/%s.mnc %s/longitudinal/%s_nuc.mnc' %(inputname_time2, inputname_time2[0:-2], inputname_time2))
  return

def ants(from_image, to_image, outpath):
  execute('mincANTS 3 -m PR[%s,%s,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s \
      -i 100x100x100x20' %(from_image, to_image, outpath))
  return 

def longitudinal(inputname_time2):
  inputname = inputname_time2[0:-2]
  # rigid body 6-parameter transformation of time2_nuc to time1_lsq12 
  execute('bestlinreg -lsq6 -clob %s/longitudinal/%s_nuc.mnc %s/output_lsq12/%s_lsq12.mnc %s/longitudinal/time2to1.xfm'%(inputname, inputname_time2, inputname, inputname, inputname))  
  execute('mincresample -clob -transformation %s/longitudinal/time2to1.xfm %s/longitudinal/%s_nuc.mnc %s/longitudinal/time2_lsq6.mnc -like %s/output_lsq12/%s_lsq12.mnc' 
          %(inputname, inputname, inputname_time2, inputname, inputname, inputname))

  # nonlinear registration of time1_lsq12 to time2_rigid 
  ants('%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname), '%s/longitudinal/time2_lsq6.mnc' %inputname, '%s/longitudinal/time1to2_nlin.xfm' %inputname)
  # use grid from this ^ (= Displacement volume)
 
  
  # Jacobian determinant of the deformation field (to detect volumetric changes)
  execute('mincblob -clob -determinant %s/longitudinal/time1to2_nlin_grid_0.mnc %s/longitudinal/det.mnc' %(inputname, inputname))


  # warp back to the nonlinear from time1 ??? model space
  ants('%s/longitudinal/det.mnc' %inputname, 'avgimages/nonlin4avg.mnc', '%s/longitudinal/det2model_nlin.xfm' %inputname)
  execute('mincresample -clob -transformation %s/longitudinal/det2model_nlin.xfm %s/longitudinal/det.mnc %s/longitudinal/det2model.mnc -like avgimages/nonlin4avg.mnc' %(inputname, inputname, inputname))

  # blur
  execute('mincblur -clob -fwhm 4 %s/longitudinal/det2model.mnc %s/longitudinal/det1' %(inputname, inputname))
  execute('mincblur -clob -fwhm 6 %s/longitudinal/det1_blur.mnc %s/longitudinal/det2' %(inputname, inputname))
  execute('mincblur -clob -fwhm 8 %s/longitudinal/det2_blur.mnc %s/longitudinal/det3' %(inputname, inputname))
  return



if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess_time2':
    preprocess_time2(sys.argv[2])
  if cmd == 'longitudinal':
    longitudinal(sys.argv[2])
