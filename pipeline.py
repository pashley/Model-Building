#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *

# module load civet (for mincbet) !!!!!!!

# preprocess: image correction, normalization, maskig, lsq6 registrations to reference and resampling
mkdirp('NUC')            # stores corrected input images
mkdirp('NORM')           # stores normalized images
mkdirp('masks')          # stores masks of images
mkdirp('lin_tfiles')     # stores '.xfm' files
mkdirp('output_lsq6')    # stores resampled images

#for subject in glob.glob('inputs/*'):
  #thefile = basename(subject)
  #name = thefile[0:4]
 
  #mkdirp(name)
  #mkdirp(name + '/NUC')
  #mkdirp(name + '/NORM')
  #mkdirp(name + '/masks')
  #mkdirp(name + '/lin_tfiles')
  #mkdirp(name + '/output_lsq6')
  #mkdirp(name + '/pairwise_tfiles')
  #mkdirp(name + '/tfiles_avg') 
  
  

for subject in glob.glob('inputs/*'):
  thefile = basename(subject)
  execute('nu_correct -clob %s %s' %('inputs/' + thefile, 'NUC/' + thefile))
  themax = execute('mincstats -max NUC/' + thefile + ' | cut -c20-31') 	
  themin = execute('mincstats -min NUC/' + thefile + ' | cut -c20-31')
  execute ('minccalc -clob %s -expression "10000*(A[0]-0)/(%s-%s)" %s' %('NUC/' + thefile, themax, themin, 'NORM/' + thefile))
  name = thefile.replace(".mnc","")  #get just the name of the input
  execute ('mincbet %s %s -m' %('NORM/' + thefile, 'masks/' + name))
  mask = name + '_mask.mnc'
  execute('bestlinreg -clob -lsq6 -source_mask %s -target_mask ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc %s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s' %('masks/' + mask, 'NORM/' + thefile, 'lin_tfiles/' + name + '_lsq6.xfm')) 
  execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %('lin_tfiles/' + name + '_lsq6.xfm', 'NORM/' + thefile, 'output_lsq6/' + name + '_lsq6.mnc'))
 	  


# pairwise lsq12 registrations (linear)
mkdirp('pairwise_tfiles')   # stores '.xfm' files

for subject in glob.glob('output_lsq6/*'):
  thefile = basename(subject)
  name = thefile.replace("_lsq6.mnc","")
  for subject2 in glob.glob('output_lsq6/*'):
    target = basename(subject2)
    targetname = target.replace("_lsq6.mnc","")
    if name != targetname:
      execute('bestlinreg -lsq12 %s %s %s' %('output_lsq6/' + thefile, 'output_lsq6/' + target, 'pairwise_tfiles/' + name + '_' + targetname + '_lsq12.xfm'))




# average lsq12 xfms for each input
mkdirp('tfiles_avg')    # stores average '.xfm' files for each input

for subject in glob.glob('inputs/*'):
  thefile = basename(subject)
  name = thefile.replace(".mnc","")
  execute('xfmavg -clob %s %s' %('pairwise_tfiles/' + name + '*', 'tfiles_avg/' + name + '.xfm'))	
 	


#transform lsq6 images along lsq12 avg
mkdirp('timages')       # stores resampled images along lsq12 averages

for subject in glob.glob('output_lsq6/*'):
  thefile = basename(subject)
  name = thefile.replace("_lsq6.mnc","")
  execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %('tfiles_avg/' + name + '.xfm','output_lsq6/' + name + '_lsq6.mnc', 'timages/' + name + '_lsq12.mnc')) 




# mincaverage all lsq12 averages
mkdirp('avgimages')     # stores average lsq12 images 
execute('mincaverage timages/H* avgimages/linavg.mnc')



def nonlin_registration(sourcefolder,targetimage,number,iteration):
  for subject in glob.glob(sourcefolder + '*'):
    thefile = basename(subject)
    name = thefile[0:4]
    execute('mincANTS 3 -m PR[%s,%s,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s \
      -i %s' %(sourcefolder + thefile, 'avgimages/' + targetimage, 'tfiles_nonlin' + number + '/' + name + '_nonlin' + number + '.xfm', iteration))
  return



def nonlin_transformation(sourcefolder,number):
  for subject in glob.glob('inputs/*'):
    thefile = basename(subject)
    name  = thefile[0:4]
    execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %('tfiles_nonlin' + number + '/' + name + '_nonlin' + number + '.xfm', sourcefolder + name + '*','timages_nonlin' + number + '/' + name +'_nonlin' + number + '.mnc'))
  return 


def nonlin(sourcefolder,targetimage,number,iteration):
  mkdirp('tfiles_nonlin' + number)         # stores the '.xfm' transformation files
  mkdirp('timages_nonlin' + number)        # stores the resampled images
  
  nonlin_registration(sourcefolder,targetimage,number,iteration)
  nonlin_transformation(sourcefolder,number)
  execute('mincaverage timages_nonlin%s/H* avgimages/nonlin%savg.mnc'%(number,number))    # average image stored in avgimages folder
  return 

 # Four sets on nonlinear processing
nonlin('timages/', 'linavg.mnc', '1', '100x1x1x1')  
nonlin('timages_nonlin1/','nonlin1avg.mnc','2','100x20x1')
nonlin('timages_nonlin2/', 'nonlin2avg.mnc', '3', '100x5')
nonlin('timages_nonlin3/', 'nonlin3avg.mnc', '4', '5x20')



# join all xfms files

for subject in glob.glob('inputs/*'):
  thefile = basename(subject)
  name = thefile[0:4]
  execute('/projects/utilities/xfmjoin tfiles_nonlin1/%s_nonlin1.xfm tfiles_nonlin2/%s_nonlin2.xfm tfiles_nonlin3/%s_nonlin3.xfm tfiles_nonlin4/%s_nonlin4.xfm %s_merged.xfm' %(name, name, name, name, name))
  

# output grid
mkdirp('grids')  
for subject in glob.glob('timages/*'):
  thefile = basename(subject)
  name = thefile[0:4]
  execute('minc_displacement timages/%s %s_merged.xfm grids/%s_grid.mnc' %(thefile, name, name))                                                                           
                                                                           