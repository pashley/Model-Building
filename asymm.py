#!/usr/bin/env python
import argparse
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys



# 1) correct each native MRI volume for intensity nonuniformities (due to MRI gradient inhomogeneities)
def create_dirs(inputname):
  if not os.path.exists(inputname):
    mkdirp(inputname)
    mkdirp(inputname + '/NUC')
  return 

def nuc(inputname):
  execute('nu_correct inputs/%s %s/NUC/%s' %(inputname, inputname))
  return 



# 2) linear 9-parameter transformation 

# 3) flip transformed volume along mid-sagittal plane (to create a mirror coronal image of it)

# 4) transform all volumes such that the mid-saggital plane is parallel to the Y-Z plane via linear 6-parameter transformation

# 5) nonlinearly register each MRI volume to its respective flippped coronal image volume

# 6) blur each nonlinear transformation with 8 mm Gaussian kernel in each dimension

# 7) Jacobian determinant of each transformation 

# 8) nonlinearly transform Jacobian determinants to MNI space using the nonlinear transformation that matches each flipped input volume to the ICBM 152 template ( 
    
    

if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess_asymm':
    preprocess_time2(sys.argv[2])
  if cmd == 'longitudinal':
    longitudinal(sys.argv[2])
