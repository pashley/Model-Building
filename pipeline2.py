#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *

# module load civet (for mincbet) !


#for subject in glob.glob('inputs/*'):
  #thefile = basename(subject)
  #name = thefile[0:4]
 
  #mkdirp(name)                         # subfolder for each input 
  #mkdirp(name + '/NUC')                # stores the corrected input image
  #mkdirp(name + '/NORM')               # stores the normalized image  
  #mkdirp(name + '/masks')              # stores the masks of the input
  #mkdirp(name + '/lin_tfiles')         # stores lsq6 transformation file 
  #mkdirp(name + '/output_lsq6')        # stores resampled images
  #mkdirp(name + '/pairwise_tfiles')    # stores lsq12 pairwise transformation files  
  #mkdirp(name + '/tfiles_avg')         # stores average lsq12 transformation file 
  #mkdirp(name + '/timage_lsq12')       # stores resampled images along lsq12 averages  
  #mkdirp('avgimages')                  # stores average image after each registration
  #mkdirp(name + '/tfiles_nonlin')      # stores nonlinear transformation files
  #mkdirp(name + '/timages_nonlin')     # stores nonlinear resampled images 
  
  
## preprocess: image correction, normalization, masking, lsq6 registrations to reference and resampling      
for subject in glob.glob('inputs/H001.mnc*'):
  thefile = basename(subject)
  name = thefile[0:4]
  execute('nu_correct -clob %s %s' %('inputs/' + thefile, name + '/NUC/' + thefile))
  themax = execute('mincstats -max ' + name + '/NUC/' + thefile + ' | cut -c20-31') 	
  themin = execute('mincstats -min ' + name + '/NUC/' + thefile + ' | cut -c20-31')
  execute ('minccalc -clob %s -expression "10000*(A[0]-0)/(%s-%s)" %s' %(name + '/NUC/' + thefile, themax, themin, name + '/NORM/' + thefile))
  execute ('mincbet %s %s -m' %(name + '/NORM/' + thefile, name + '/masks/' + name))
  mask = name + '_mask.mnc'
  execute('bestlinreg -clob -lsq6 -source_mask %s -target_mask ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc %s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s' %(name + '/masks/' + mask, name + '/NORM/' + thefile, name + '/lin_tfiles/' + name + '_lsq6.xfm')) 
  execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(name + '/lin_tfiles/' + name + '_lsq6.xfm', name + '/NORM/' + thefile, name + '/output_lsq6/' + name + '_lsq6.mnc'))
 	  
 	  
## pairwise lsq12 registrations
#for subject in glob.glob('inputs/H001.mnc*'):
  #thefile = basename(subject)
  #name = thefile[0:4]
  
  #for subject2 in glob.glob('inputs/*'):
    #target = basename(subject2)
    #targetname = target[0:4]
    #if name != targetname:
      #execute('bestlinreg -lsq12 %s %s %s' %(name + '/output_lsq6/' + name + '_lsq6.mnc', targetname + '/output_lsq6/' + targetname + '_lsq6.mnc', name + '/pairwise_tfiles/' + name + '_' + targetname + '_lsq12.xfm'))


## average lsq12 xfms for each input
#for subject in glob.glob('inputs/H001.mnc*'):
  #thefile = basename(subject)
  #name = thefile[0:4]
  #execute('xfmavg -clob %s %s' %(name + '/pairwise_tfiles/*', name + '/tfiles_avg/' + name + '.xfm'))	
 	


## transform lsq6 images along lsq12 avg
#for subject in glob.glob('inputs/H001.mnc*'):
  #thefile = basename(subject)
  #name = thefile[0:4]
  #execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(name + '/tfiles_avg/' + name + '.xfm', name + '/output_lsq6/' + name + '_lsq6.mnc', name + '/timage_lsq12/' + name + '_lsq12.mnc')) 


## mincaverage all lsq12 averages
#execute('mincaverage H0*/timage_lsq12/H* avgimages/linavg.mnc')



#def nonlin_registration(sourcefolder,sourcefile,targetimage,number,iteration):
  #for subject in glob.glob('inputs/H001.mnc*'):
    #thefile = basename(subject)
    #name = thefile[0:4]
    #execute('mincANTS 3 -m PR[%s,%s,1,4] \
      #--number-of-affine-iterations 10000x10000x10000x10000x10000 \
      #--MI-option 32x16000 \
      #--affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      #--use-Histogram-Matching \
      #-r Gauss[3,0] \
      #-t SyN[0.5] \
      #-o %s \
      #-i %s' %(name + sourcefolder + name + sourcefile , 'avgimages/' + targetimage, name + '/tfiles_nonlin/' + name + '_nonlin' + number + '.xfm', iteration))
  #return


#def nonlin_transformation(sourcefolder,sourcefile,number):
  #for subject in glob.glob('inputs/H001.mnc*'):
    #thefile = basename(subject)
    #name  = thefile[0:4]
    #execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(name + '/tfiles_nonlin/' + name + '_nonlin' + number + '.xfm', name + sourcefolder + name + sourcefile, name + '/timages_nonlin/' + name +'_nonlin' + number + '.mnc'))
  #return 


#def nonlin(sourcefolder,sourcefile,targetimage,number,iteration):
  #nonlin_registration(sourcefolder,sourcefile,targetimage,number,iteration)
  #nonlin_transformation(sourcefolder,sourcefile,number)
  #execute('mincaverage H0*/timages_nonlin/H0*_nonlin%s.mnc avgimages/nonlin%savg.mnc'%(number,number))    # average image stored in 'avgimages' folder
  #return 


## Four sets on nonlinear registrations
#nonlin('/timage_lsq12/', '_lsq12.mnc', 'linavg.mnc', '1', '100x1x1x1')  
#nonlin('/timages_nonlin/','_nonlin1.mnc','nonlin1avg.mnc','2', '100x20x1')
#nonlin('/timages_nonlin/','_nonlin2.mnc', 'nonlin2avg.mnc', '3', '100x5')
#nonlin('/timages_nonlin/','_nonlin3.mnc', 'nonlin3avg.mnc', '4', '5x20')


# join all nonlinear transfomation ('.xfm') files
for subject in glob.glob('inputs/H001.mnc*'):
  thefile = basename(subject)
  name = thefile[0:4]
 # execute('/projects/utilities/xfmjoin %s/tfiles_nonlin/%s_nonlin1.xfm %s/tfiles_nonlin/%s_nonlin2.xfm %s/tfiles_nonlin/%s_nonlin3.xfm %s/tfiles_nonlin/%s_nonlin4.xfm %s_merged.xfm' %(name, name, name, name, name, name, name, name, name))

  

# deformations 
for subject in glob.glob('inputs/H001.mnc*'):
  thefile = basename(subject)
  name = thefile[0:4]
  execute("sed -i 's,= H001/, ,g' %s_merged.xfm" %(name))
  #execute('minc_displacement %s/timage_lsq12/%s_lsq12.mnc %s_merged.xfm %s/%s_grid.mnc' %(name, name, name, name, name))                                                                          
                                                                           
