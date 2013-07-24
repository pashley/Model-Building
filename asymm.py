#!/usr/bin/env python
import argparse
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys


def create_dirs(inputname):
  if not os.path.exists(inputname):
    mkdirp(inputname)
    mkdirp(inputname + '/NUC')
    mkdirp(inputname + '/lin_tfiles')
    mkdirp(inputname + '/output_lsq9')
    mkdirp(inpurname + '/output_lsq6')
    mkdirp(inputname + '/nlin_tfiles')
    mkdipr(inputname + '/stats')
  return 




def asymmetric_analysis(inputname):
  # 1) correct each native MRI volume for intensity nonuniformities (due to MRI gradient inhomogeneities)
  if not os.path.exists('%s/NUC/%s.mnc' %(inputname, inputname)):
    execute('nu_correct inputs/%s.mnc %s/NUC/%s.mnc' %(inputname, inputname, inputname))
  
  # 2) linear 9-parameter transformation
  if not os.path.exists('%s/output_lsq9/%s_lsq9.mnc' %(inputname, inputname)):
    execute('bestlinreg -lsq9 -clob %s/NUC/%s.mnc targetimage.mnc %s/lin_tfiles/%s_lsq9.xfm' %(inputname, inputname, inputname, inputname))
    execute('mincresample -transformation %s/lin_tfiles/%s_lsq9.xfm %s/NUC/%s.mnc %s/output_lsq9/%s_lsq9.mnc -like targetimage.mnc' %(inputname, inputname, inputname, inputname, inputname, inputname))
  
  # 3) flip transformed volume along mid-sagittal plane (to create a mirror coronal image of it)
  if not os.path.exists('%s/output_lsq9/%s_flipped_lsq9.mnc' %(inputname, inputname)):
    execute('volflip -x -clob %s/output_lsq9/%s_lsq9.mnc %s/output_lsq9/%s_flipped_lsq9.mnc' %(inputname, inputname, inputname, inputname))
  
  # 4) transform all volumes such that the mid-saggital plane is parallel to the Y-Z plane via linear 6-parameter transformation 
  if not os.path.exists('%s/output_lsq6/%s_flipped_lsq6.mnc' %(inputname, inputname)):
    execute('bestlinreg -lsq6 -clob %s/output_lsq9/%s_flipped_lsq9.mnc targetimage.mnc %s/lin_tfiles/%s_flipped_lsq6.xfm' %(inputname, inputname, inputname, inputname))
    execute('mincresample -transformation %s/lin_tfiles/%s_flipped_lsq6.xfm %s/output_lsq9/%s_flipped_lsq9.mnc %s/output_lsq6/%s_flipped_lsq6.mnc -like targetimage.mnc' %(inputname, inputname, inputname, inputname, inputname, inputname))
  
  if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
    execute('bestlinreg -lsq6 -clob %s/output_lsq9/%s_lsq9.mnc targetimage.mnc %s/lin_tfiles/%s_lsq6.xfm' %(inputname, inputname, inputname, inputname))
    execute('mincresample -transformation %s/lin_tfiles/%s_lsq6.xfm %s/output_lsq9/%s_lsq9.mnc %s/output_lsq6/%s_lsq6.mnc -like targetimage.mnc' %(inputname, inputname, inputname, inputname, inputname, inputname))
  
  # 5) nonlinearly register each MRI volume to its respective flippped coronal image volume
  if not os.path.exists('%s/nlin_tfiles/%s_nlin_grid_0.mnc' %(inputname, inputname)):
    execute('mincANTS 3 -m PR[%s/output_lsq6/%s_lsq6.mnc,%s/output_lsq6/%s_flipped_lsq6.mnc,1,4] \
                        --number-of-affine-iterations 10000x10000x10000x10000x10000 \
                        --MI-option 32x16000 \
                        --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
                        --use-Histogram-Matching \
                        -r Gauss[3,0] \
                        -t SyN[0.5] \
                        -o %s/nlin_tfiles/%s_nlin.xfm \
                        -i 100x100x100x20' %(inputname, inputname, inputname, inputname, inputname, inputname))
  
  # 6) blur each nonlinear transformation with 8 mm Gaussian kernel in each dimension
  if not os.path.exists('%s/nlin_tfiles/%s_nlin_grid_0_blur.mnc' %(inputname, inputname)):
    execute('mincblur -fwhm 8 %s/nlin_tfiles/%s_nlin_grid_0.mnc %s/nlin_tfiles/%s_nlin_grid_0' %(inputname, inputname, inputname, inputname))
  
  # 7) Get Jacobian determinant of each transformation 
  if not os.path.exists('%s/stats/%s_det.mnc' %(inputname, inputname)):
    execute('mincblob -determinant %s/nlin_tfiles/%s_nlin_grid_0_blur.mnc %s/stats/%s_det.mnc' %(inputname, inputname, inputname,inputname))

  # 8) nonlinearly transform Jacobian determinatns to MNI space using the nonlinear transfomation that matches each flipped input volume to the ICBM 152 template
  if not os.path.exists('%s/nlin_tfiles/f2model_nlin.xfm' %inputname):
    execute('mincANTS 3 -m PR[%s/output_lsq6/%s_flipped_lsq6.mnc,targetimage.mnc,1,4] \
                        --number-of-affine-iterations 10000x10000x10000x10000x10000 \
                        --MI-option 32x16000 \
                        --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
                        --use-Histogram-Matching \
                        -r Gauss[3,0] \
                        -t SyN[0.5] \
                        -o %s/nlin_tfiles/f2model_nlin.xfm \
                        -i 100x100x100x20' %(inputname, inputname, inputname))
    execute('mincresample -transformation %s/nlin_tfiles/f2model_nlin.xfm %s/stats/%s_det.mnc %s/stats/%s_det_in_model_space.mnc -like targetimage.mnc' %(inputname, inputname, inputname, inputname, inputname))
  return 


if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'create_dirs':
    create_dirs(sys.argv[2])
  elif cmd == 'asymmetric_analysis':
    asymmetric_analysis(sys.argv[2])
