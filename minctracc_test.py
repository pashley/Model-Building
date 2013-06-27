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



def blur_n_minctracc(fwhm,num,iterations, step, lttdiam, model):
  # blur model
  execute('mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4]))
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/%s_lsq12_%s_blur.mnc' %(inputname, inputname,fwhm)):
      execute('mincblur -clob -fwhm %s ../timages/%s_lsq12.mnc %s/%s_lsq12_%s' %(fwhm,inputname, inputname, inputname,fwhm))
    
    if num == 1:     # no -transformation option for first minctracc
      execute('minctracc -clob -iterations 30 -step 8 8 8 -sub_lattice 6 -lattice_diameter 24 24 24 -stiffness 1 -weight 1 -similarity 0.3 %s/%s_lsq12_%s_blur.mnc avgimages/linavg_blur.mnc %s/%s_out1.xfm' %(inputname, inputname, fwhm, inputname, inputname))
      execute('mincresample -transformation %s/%s_out%s.xfm ../timages/%s_lsq12.mnc %s/%s_nlin%s.mnc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(inputname, inputname, num, inputname, inputname, inputname, num))
    
    else:
      execute('minctracc -clob -iterations %s -step %s %s %s -sub_lattice 6 -lattice_diameter %s %s %s -stiffness 1 -weight 1 -similarity 0.3 -transformation %s/%s_out%s.xfm %s/%s_lsq12_%s_blur.mnc avgimages/%s_blur.mnc %s/%s_out%s.xfm' %(iterations, step,step, step, lttdiam, lttdiam, lttdiam, inputname, inputname, int(num)-1, inputname, inputname, fwhm, model[0:-4], inputname, inputname, num))
      execute('mincresample -clob -transformation %s/%s_out%s.xfm %s/%s_nlin%s.mnc %s/%s_nlin%s.mnc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(inputname, inputname, num, inputname, inputname, int(num)-1, inputname, inputname, num))
  execute('mincaverage -clob H*/*nlin%s.mnc avgimages/nonlin%savg.mnc' %(num, num))
  return

 
#blur_n_minctracc(16, 1, 30, 8, 24, 'linavg.mnc')
#blur_n_minctracc(8, 2, 30, 8, 24,'nonlin1avg.mnc')
#blur_n_minctracc(8, 3, 30, 4, 12,'nonlin2avg.mnc')
#blur_n_minctracc(4, 4, 30, 4, 12,'nonlin3avg.mnc')
blur_n_minctracc(4, 5, 10, 2, 6,'nonlin4avg.mnc')
#blur_n_minctracc(2, 6, 10, 2, 6,'nonlin5avg.mnc')