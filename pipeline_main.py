#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys


# module load civet for mincbet


for subject in glob.glob('inputs/*'):
  name = subject[7:11]
  if not os.path.exists(name + '/'):
    mkdirp(name)                         # subfolder for each input 
    mkdirp(name + '/NUC')                # stores the corrected input image
    mkdirp(name + '/NORM')               # stores the normalized image  
    mkdirp(name + '/masks')              # stores the masks of the input
    mkdirp(name + '/lin_tfiles')         # stores lsq6 transformation file 
    mkdirp(name + '/output_lsq6')        # stores resampled images
    mkdirp(name + '/pairwise_tfiles')    # stores lsq12 pairwise transformation files  
    mkdirp(name + '/tfiles_avg')         # stores average lsq12 transformation file 
    mkdirp(name + '/timage_lsq12')       # stores resampled images along lsq12 averages  
    mkdirp('avgimages')                  # stores average image after each registration
    mkdirp(name + '/tfiles_nonlin')      # stores nonlinear transformation files
    mkdirp(name + '/timages_nonlin')     # stores nonlinear resampled images 
       

job_submitted = False

def pbs_submit(command): 
  execute("sge_batch " + command)
  global job_submitted
  job_submitted = True
  return

#def wait():
   #pipeline_main.py -depends on ###
   #return


# preprocess  
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname,inputname)):
    pbs_submit("./process.py preprocess %s" % subject)
    
if job_submitted:
  sys.exit(1)










#wait()

# wait for all _lsq6.mnc files
# ./pipeline_main.py -depends on ###    

#pairwise lsq12 registrations
for subject in glob.glob('inputs/H001.mnc*'):
  sourcename = subject[7:11]
  for subject2 in glob.glob('inputs/*'):
    targetname = subject2[7:11]
    if sourcename != targetname:
      if not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename,sourcename, targetname)):
        pbs_submit('./process.py pairwise_reg %s %s' %(sourcename, targetname))
        
              
if job_submitted:
  sys.exit(1)


# wait for all the pairwise registrations of a single input 
# xfm average & resample
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
    pbs_submit('./process.py avg_and_resample %s' % inputname)

if job_submitted:
  sys.exit(1)
  

  
# wait for all _lsq12.mnc files 

# average all _lsq12.mnc files
if not os.path.exists('avgimages/linavg.mnc'):
  pbs_submit('./process.py mnc_avg timage_lsq12 lsq12 linavg.mnc')

if job_submitted:
  sys.exit(1)


# wait for average files
# first nonlinear registration 
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timages_nonlin/%s_nonlin1.mnc' %(inputname,inputname)):
    pbs_submit('./process.py nonlin_reg %s %s/timage_lsq12/%s_lsq12.mnc linavg.mnc 1 100x1x1x1' %(inputname, inputname, inputname))
       
if job_submitted:
  sys.exit(1)


# wait for all _nonlin1.mnc files
# average all _nonlin1.mnc files
if not os.path.exists('avgimages/nonlin1avg.mnc'):
  pbs_submit('./process.py mnc_avg timages_nonlin nonlin1 nonlin1avg.mnc')
  
if job_submitted:
  sys.exit(1)


# wait for average
# second nonlinear registration
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timages_nonlin/%s_nonlin2.mnc' %(inputname, inputname)):
    pbs_submit('./process.py nonlin_reg %s %s/timages_nonlin/%s_nonlin1.mnc nonlin1avg.mnc 2 100x20x1' %(inputname, inputname, inputname))

if job_submitted:
  sys.exit(1)
  

# wait  
# average all _nonlin2.mnc
if not os.path.exists('avgimages/nonlin2avg.mnc'):
  pbs_submit('./process.py mnc_avg timages_nonlin nonlin2 nonlin2avg.mnc')
              
if job_submitted:
  sys.exit(1)


# wait for average
# third nonlinear registration
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timages_nonlin/%s_nonlin3.mnc' %(inputname, inputname)):
    pbs_submit('./process.py nonlin_reg %s %s/timages_nonlin/%s_nonlin2.mnc nonlin2avg.mnc 3 100x5' %(inputname, inputname, inputname))
             
if job_submitted:
  sys.exit(1)

  
# wait
# average all _nonlin3.mnc
if not os.path.exists('avgimages/nonlin3avg.mnc'):
  pbs_submit('./process.py mnc_avg timages_nonlin nonlin3 nonlin3avg.mnc')

if job_submitted:
  sys.exit(1)

# wait for average
# fourth nonlinear registration
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timages_nonlin/%s_nonlin4.mnc' %(inputname,inputname)):
    pbs_submit('./process.py nonlin_reg %s %s/timages_nonlin/%s_nonlin3.mnc nonlin3avg.mnc 4 5x20' %(inputname, inputname, inputname))

if job_submitted:
  sys.exit(1)

# wait
# average all _nonlin4.mnc
if not os.path.exists('avgimages/nonlin4avg.mnc'):
  pbs_submit('./process.py mnc_avg timages_nonlin nonlin4 nonlin4avg.mnc')

if job_submitted:
  sys.exit(1)
  
# wait for all nonlinear registrations of a single input to be complete
# deformation grid
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/%s_grid.mnc' %(inputname, inputname)):
    pbs_submit('./process.py deformation %s' % inputname)
               
if job_submitted:
  sys.exit(1)
  
# wait for deformation grid of a single input  
for subject in glob.glob('inputs/H001.mnc*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/%s_blur.mnc' %(inputname, inputname)):
    pbs_submit('./process.py det_and_blur %s' % inputname)
    
if job_submitted:
  sys.exit(1)
  