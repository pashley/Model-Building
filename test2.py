#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
from optparse import OptionParser
import random



job_submitted = False


def test(x):
  print "num == %s" % x
  global job_submitted
  if x > 5:
    job_submitted = True
  return

print job_submitted
test(random.randint(1,9))
print job_submitted
test(4)
print job_submitted

'''count = 0



for subject in glob.glob('inputs/*'):
  count += 1
  
print "count = %s" % count

if count > 16:
  print "here"
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    if inputname != "H002":
      if not os.path.exists('%s/%s_H002_lsq12.xfm' %(inputname, inputname)):
        pbs_submit('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s %s/%s_H002_lsq12.xfm' %(inputname, inputname,'H002/output_lsq6/H002_lsq6.mnc', inputname, inputname))
   


if not os.path.exists('xfmavg.xfm'):
  execute('xfmavg -clob H0*/H0*_H002_lsq12.xfm xfmavg.xfm')  

for subject in glob.glob('inputs/*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/%savg_lsq12.mnc' %(inputname, inputname)):
    pbs_submit('mincresample -clob -transformation %s %s/output_lsq6/%s_lsq6.mnc %s/%savg_lsq12.mnc -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %('xfmavg.xfm', inputname, inputname, inputname, inputname))
 
  
for subject in glob.glob('inputs/*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/%s_lsq12.xfm' %(inputname, inputname)):
    pbs_submit('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/%savg_lsq12.mnc %s/%s_lsq12.xfm' %(inputname, inputname, inputname, inputname, inputname, inputname))
  
   
for subject in glob.glob('inputs/*'):
  inputname = subject[7:11]
  if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)):
    pbs_submit('mincresample -clob -transformation %s/%s_lsq12.xfm %s/output_lsq6/%s_lsq6.mnc %s/timage_lsq12/%s_lsq12.mnc -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(inputname, inputname , inputname, inputname, inputname, inputname))

execute('mincaverage H0*/%s/H0*_%s.mnc avgimages/%s' %('timage_lsq12','lsq12','linavgtest.mnc'))'''


  # We can take a randomly selected subset of the inputs and do pairwise registration with those. 
  
  # We can also take a random subject and estimate the 12-parameter mapping each subject to it (not pairwise).  If we then take those transformations, average them, and then apply them, then this subject represents the "average" head size of the group.  We then repeat the 12-parameter mapping to this transformed individual and continue as normal.
  
  
  
  
  #import random
  
  #random.randint(1,18)
  
  
  
  
  '''
  # wait for all _lsq6.mnc files
  # ./pipeline_main.py -depends on ###  
  
  count = 0
  for subject in glob.glob('inputs/*'):
    count += 1
  
  
  
  # alternative to pairwise registrations (when many inputs)
  if count > 16:
    
    #targetname = random.randint(1,count)
    targetname = 2
    print "targetname == %s" % targetname
      
    if targetname < 10:
      targetname = "H00%s" % targetname
    else:
      targetname = "H0%s" % targetname
  
    for subject in glob.glob('H*/output_lsq6/*'):
      sourcename = subject[0:4]
      targetpath = "%s/output_lsq6/%s_lsq6.mnc" %(targetname, targetname)
      outputpath = "%s/lin_tfiles/%s_%s_lsq12.xfm" %(sourcename,sourcename,targetname)    
      if sourcename != targetname:
        if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
          pbs_submit('./process.py lsq12reg %s %s %s' %(subject, targetpath, outputpath))   
    if job_submitted:
      sys.exit(1)
      
    # wait for all H*_targetname_lsq12.xfm files     
    if not os.path.exists('xfmavg.xfm'):
      pbs_submit('./process.py xfmavg')
    if job_submitted:
      sys.exit(1)    
    
    # wait for average
    for subject in glob.glob('H*/output_lsq6/*'):
      inputname = subject[0:4]
      xfm = 'xfmavg.xfm'
      outputpath = '%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)
      if not os.path.exists('%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)):
        pbs_submit('./process.py resample %s %s %s' %(xfm, subject, outputpath))
    if job_submitted:
      sys.exit(1)  
  
    # wait for H*_avglsq12.mnc of a single output
    for subject in glob.glob('H*/output_lsq6/*'):
      sourcename = subject[0:4]
      targetpath = '%s/timage_lsq12/%s_avglsq12.mnc' %(sourcename, sourcename)
      outputpath = '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename) 
      if not os.path.exists('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename)):
        pbs_submit('./process.py lsq12reg %s %s %s' %(subject,targetpath,outputpath))
    if job_submitted:
      sys.exit(1)
  
    # wait for H*_lsq12.xfm of a single output  
    for subject in glob.glob('H*/output_lsq6/*'):
      inputname = subject[0:4]
      xfm = '%s/lin_tfiles/%s_lsq12.xfm' %(inputname, inputname)
      outputpath = '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)
      if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)):
        pbs_submit('./process.py resample %s %s %s' %(xfm, subject, outputpath))
    if job_submitted:
      sys.exit(1)  
  '''  
  """ # wait for average files
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
  """
  
  #for subject in glob.glob('inputs/*'):
      #inputname = subject[7:11]
      #xfm = 'lsq12avg_inverse.xfm'
      #sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(inputname, inputname)
      #outputpath = '%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)
      #if not os.path.exists('%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)):
        #pbs_submit('-J sc_%s -H "xfmavg_inv" ./process.py resample %s %s %s' %(inputname, xfm, sourcepath, outputpath))  
        
#for subject in glob.glob('inputs/*'):
  #name = subject[7:11]
  #if not os.path.exists(name + '/'):
    #mkdirp(name)                         # subfolder for each input 
    #mkdirp(name + '/NUC')                # stores the corrected image
    #mkdirp(name + '/NORM')               # stores the normalized image  
    #mkdirp(name + '/masks')              # stores the mask of the input
    #mkdirp(name + '/lin_tfiles')         # stores lsq6,lsq12 transformation files 
    #mkdirp(name + '/output_lsq6')        # stores resampled images from lsq6 registration
    #mkdirp(name + '/pairwise_tfiles')    # stores lsq12 pairwise transformation files  
    #mkdirp(name + '/timage_lsq12')       # stores resampled images from lsq12 averages  
    #mkdirp('avgimages')                  # stores average image after each registration
    #mkdirp(name + '/tfiles_nonlin')      # stores transformation files from nonlinear registrations
    #mkdirp(name + '/timages_nonlin')     # stores resampled images from nonlinear registrations
    #mkdirp(name + '/final_stats')        # stores 
               

    elif cmd[0:9] == 'nonlinreg':
       if len(cmd) == 10:
         num = int(cmd[9])
         if num == 1 and len(glob.glob('H*/timage_lsq12/*')) == count and os.path.exists('avgimages/linavg.mnc'):
           pbs_submit('-J check_lsq12 -H "linavg" ./process.py check_lsq12 %s' % count)
           nonlinreg_and_avg('1', 'timage_lsq12','lsq12','linavg.mnc', '100x1x1x1')   
         if num == 2 and len(glob.glob('H*/timages_nonlin/*_nonlin1.mnc*')) == count and os.path.exists('avgimages/nonlin1avg.mnc'):
           nonlinreg_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
         if num == 3 and len(glob.glob('H*/timages_nonlin/*_nonlin2.mnc*')) == count and os.path.exists('avgimages/nonlin2avg.mnc'):
           nonlinreg_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
         if num == 4 and len(glob.glob('H*/timages_nonlin/*_nonlin3.mnc*')) == count and os.path.exists('avgimages/nonlin3avg.mnc'):
           nonlinreg_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')       
       else:
         if len(glob.glob('H*/timage_lsq12/*')) == count and os.path.exists('avgimages/linavg.mnc'):
           nonlinregs()
       sys.exit(1)
    