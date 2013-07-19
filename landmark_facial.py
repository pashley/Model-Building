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


""" Landmark-Based Facial Feature Analysis

- happens after everything  
- warp 56 landmarked model(already done) to the model generated
- then warp that back to each individual 

1. Define 56 landmarks on a surface- & voxel-representation of the average nonlinear model
2. warp landmarks to each individuals face using the inverse of the transformation file that maps the individual's craniofacial structure to the avg                   
"""


def warp_landmarked_2_model():
  """Warps the given landmarked model to the linear (12-parameter) model"""
  
  # generate transformation file that maps the generated model to the landmarked model 
  execute('mincANTS 3 -m PR[nonlin_model.mnc, landmarked_model.mnc,1,4] \
    --number-of-affine-iterations 10000x10000x10000x10000x10000 \
    --MI-option 32x16000 \
    --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
    --use-Histogram-Matching \
    -r Gauss[3,0] \
    -t SyN[0.5] \
    -o model2landmarked.xfm \
    -i 100x100x100x20')
  # resample using the inverted transformation file (bring the landmarks to the model space)
  execute('mincresample -invert_transformation model2landmarked.xfm landmarked_model.mnc landmarked_nonlin_model.mnc -like nonlin_model.mnc')
  return


def warp_model_2_subject(inputname):
  """Warps the landmarked linear (12-parameter) model to the lsq12 subject"""
  # warp the landmarked lsq12model to each individual (via inverting the xfm the maps the craniofacial features to this landmarked model)
  
  # generate transformation file that maps the craniofacial features to this landmarked model  
  execute('mincANTS 3 -m PR[subject.mnc,landmarked_nonlin_model.mnc,1,4] \
    --number-of-affine-iterations 10000x10000x10000x10000x10000 \
    --MI-option 32x16000 \
    --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
    --use-Histogram-Matching \
    -r Gauss[3,0] \
    -t SyN[0.5] \
    -o %s/landmarked/%s_landmarked.xfm \
    -i 100x100x100x20' %(inputname, inputname))

  # resample using the inverted transformation file (brings the landmarks to the subject space) 
  execute('mincresample -invert_transformation landmarked_subject.xfm subject_lsq12.xfm %s/landmarked/%s_landmarked.mnc -like subject.mnc' %(inputname,inputname)
  return




if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'warp_landmarked_2_model':
    warp_landmarked_2_model()
  if cmd == 'warp_model_2_subject':
    warp_model_2_subject(sys.argv[2])
