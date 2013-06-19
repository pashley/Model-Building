#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import random



# "module load civet" for mincbet

for subject in glob.glob('inputs/*'):
  name = subject[7:11]
  if not os.path.exists(name + '/'):
    mkdirp(name)                          
    mkdirp(name + '/NUC')                
    mkdirp(name + '/NORM')                 
    mkdirp(name + '/masks')              
    mkdirp(name + '/lin_tfiles')          
    mkdirp(name + '/output_lsq6')        
    mkdirp(name + '/pairwise_tfiles')      
    mkdirp(name + '/timage_lsq12')         
    mkdirp('avgimages')                  
    mkdirp(name + '/tfiles_nonlin')      
    mkdirp(name + '/timages_nonlin')     
    mkdirp(name + '/final_stats')        
               

count = 0
for subject in glob.glob('inputs/*'):
  count += 1
  



def submit_jobs(jobname, depends, command, job_list, batchsize, time, num, numjobs): 
  if batch_system == 'sge':
    execute('sge_batch -J %s -H "%s" %s' %(jobname, depends, command))
  elif batch_system == 'pbs':
    job_list.append(command)
    if num == numjobs:       # when all commands are added to the list, submit the list
      print 'num == %s' %num
      print 'numjobs %s' %numjobs
      for i in job_list:
        print i
      #execute('./qbatch %s %s %s -H %s' %(job_list, batchsize, time, depends))  
  return



def preprocessing():
  job_list = []
  num = 0
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    complete = len(glob.glob('H*/output_lsq6/*_lsq6.mnc'))
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      num += 1
      submit_jobs('s1_%s' % inputname, "", './process.py preprocess %s' % subject, job_list, 4, "10:00:00", num, count-complete)         
  return 


 
def nonpairwise():         # alternative to pairwise registrations (i.e. too many inputs)          
  # select a random input
  targetname = random.randint(1,count)
  if targetname < 10:
    targetname = "H00%s" % targetname
  elif targetname >= 10 and targetname < 100:
    targetname = "H0%s" % targetname
  else:
    targetname = "H%s" % targetname
  targetname = "H016"  
  
  # STAGE 2a: lsq12 transformation of each input to a randomly selected subject (not pairwise)
  job_list = []
  num = 0
  for subject in glob.glob('inputs/*'):
    sourcename = subject[7:11]     
    sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(sourcename, sourcename)
    targetpath = "%s/output_lsq6/%s_lsq6.mnc" %(targetname, targetname)
    outputpath = "%s/lin_tfiles/%s_%s_lsq12.xfm" %(sourcename,sourcename,targetname)
    complete = len(glob.glob('H*/lin_tfiles/H*_H*_lsq12.xfm'))
    if sourcename != targetname:
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        num += 1
        submit_jobs('sa_%s_%s' %(sourcename[2:4], targetname[2:4]), 's1_*', './process.py lsq12reg %s %s %s' %(sourcepath, targetpath, outputpath),job_list, 4, "10:00:00", num, count-complete-1)
        

  # STAGE 2b: average all lsq12 xfm files, invert this average, resample (apply inverted averaged xfm to randomly selected subject)
  # wait for all H*_H*_lsq12.xfm files
  job_list = []
  if not os.path.exists('avgsize.mnc'):
    submit_jobs('avgsize','sa_*', './process.py xfmavg_inv_resample %s' %targetname, job_list, 1, "1:00:00", 1, 1) 
  
   
  # STAGE 2c: repeat lsq12 tranformation for every original input (ex. H001_lsq6.mnc) to the "average size", then resample (wait for avgsize.mnc)
  job_list = []
  num = 0
  for subject in glob.glob('inputs/*'): 
    sourcename = subject[7:11]
    sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(sourcename, sourcename)
    targetpath = 'avgsize.mnc'
    outputpath = '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename) 
    complete = len(glob.glob('H*/timage_lsq12/H*_lsq12.mnc'))   
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename)):         
      num += 1
      submit_jobs('s3_%s' %sourcename, 'avgsize', './process.py lsq12reg_and_resample %s' %sourcename, job_list, 4, "10:00:00", num, count-complete)
  return  
    
    
      

def pairwise():
  # STAGE 2: pairwise lsq12 registrations (wait for all H*_lsq6.mnc files)
  job_list = []
  num = 0
  for subject in glob.glob('inputs/*'):
    sourcename = subject[7:11]
    for subject2 in glob.glob('inputs/*'):
      targetname = subject2[7:11]
      complete = len(glob.glob('H*/pairwise_tfiles/*_*_lsq12.xfm'))
      if sourcename != targetname and not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
          num += 1
          submit_jobs('s2_%s_%s' %(sourcename[1:4], targetname[1:4]), 's1_*","check_lsq6', './process.py pairwise_reg %s %s' %(sourcename, targetname), job_list, 4, "10:00:00", num, ((count-1)*count)-complete)
          
  # STAGE 3: xfm average & resample (wait for all the pairwise registrations of a single input)
  job_list = []
  num = 0
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    complete = len(glob.glob('*/timage_lsq12/*_lsq12.mnc'))
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      num += 1
      submit_jobs('s3_%s' %inputname, 's2_*', './process.py avg_and_resample %s' %inputname, job_list, 4, "10:00:00", num, count-complete)
  return



def linavg():
  # STAGE 4: mincaverage (wait for all H*_lsq12.mnc files)
  job_list = []
  if not os.path.exists('avgimages/linavg.mnc'):
    submit_jobs('linavg', 's3_*', './process.py mnc_avg timage_lsq12 lsq12 linavg.mnc', job_list, 1, "1:00:00", 1, 1 )
  return


  
def nonlinreg_and_avg(number, sourcefolder,inputregname, targetimage, iterations):
  # STAGE 5: nonlinear registrations & averaging
  # wait for previous average ( == targetimage)
  if number == '1':
    checkfor = 'lsq12'
  if int(number) > 1:
    checkfor = 'reg' + str(int(number) - 1)
  job_list = []
  for subject in glob.glob('inputs/H002.mnc*'):
    inputname = subject[7:11]  
    if not os.path.exists('%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      batch('reg%s_%s' %(number, inputname[1:4]), '%s","check_%s' %(targetimage[0:-4], checkfor), './process.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations), job_list)
       
  # wait for all H###_nonlin#.mnc files    
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    batch('nonlin%savg' %number,'reg%s_*","check_lsq12' %number, './process.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number), job_list)
  if batch_system == 'pbs':
    pbs_submit_job(job_list, "", 4, "10:00:00")
  return
 
 
 
def nonlinregs():
  # Check for successful completion of (pairwise or non-pairwise) lsq12 registration 
  # if unsuccessful then stop program, else continue
  job_list = []
  batch('check_lsq12', 'linavg', './process.py check_lsq12 %s' % count, job_list)
  
  for subject in glob.glob('inputs/H002.mnc*'):
    inputname = subject[7:11]
        
    nonlinreg_and_avg('1', 'timage_lsq12','lsq12','linavg.mnc', '100x1x1x1')
    batch('check_reg1', 'nonlin1avg', './process.py check_reg 1', job_list)
    
    nonlinreg_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
    batch('check_reg2', 'nonlin2avg', './process.py check_reg 2', job_list)
    
    nonlinreg_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
    batch('check_reg3', 'nonlin3avg', './process.py check_reg 3', job_list)
    
    nonlinreg_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')
    batch('check_reg4', 'nonlin4avg', './process.py check_reg 4', job_list)
  return



def final_stats():
  # wait for all nonlinear registrations of a single input to be complete 
  job_list = []
  for subject in glob.glob('inputs/H001.mnc*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/final_stats/%s_grid.mnc' %(inputname, inputname)):
      batch('s6_%s' % inputname, 'reg*_%s","check_lsq12' %inputname[1:4], './process.py deformation %s' % inputname, job_list)
      
   # wait for deformation grid of a single input  
  for subject in glob.glob('inputs/H001.mnc*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/final_stats/%s_blur.mnc' %(inputname, inputname)):
      batch('s7_%s' %inputname, 's6_%s","check_lsq12' %inputname, './process.py det_and_blur %s' % inputname)  
  return







if __name__ == '__main__':
  cmd = sys.argv[1]           # first command line argument: stage to execute (options: preprocess, lsq12_p, lsq12_n, lsq12, linavg, nonlinreg, finalstats, all)           
  batch_system = sys.argv[2]  # second command line argument: batch system to run pipeline (options: sge or pbs)
                            
  if cmd == 'preprocess':
    preprocessing()
    sys.exit(1)
  
  elif cmd[0:5] == 'lsq12':
    # "lsq12_p" or "lsq12_n"      
    if len(cmd) > 5:            
      if cmd[6] == 'p':         # pairwise
        pairwise()
      elif cmd[6] == 'n':       # non-pairwise
        nonpairwise()
    # "lsq12"
    elif len(cmd) == 5:         # when 'pairwise' or 'non-pairwise' is not specified, perform lsq12 registration method according to the number of inputs  
      if count < 20:
        pairwise()
      else:
        nonpairwise()
    sys.exit(1)

  elif cmd == 'linavg':
    linavg()
    sys.exit(1)
  
  elif cmd == 'nonlinreg':
    nonlinregs()
    sys.exit(1)
         
  elif cmd == 'finalstats':
    final_stats()
    sys.exit(1)
      
  elif cmd == "all":
    #preprocessing()
    if count > 20:   
      nonpairwise()
    elif count < 20:
      pairwise()
    linavg()
    nonlinregs() 
    #final_stats()
    sys.exit(1)
    
    
    #def check2(path,targetnum):
      #targetnum = int(targetnum)  
      #num = 0
      #for subject in glob.glob('inputs/*'):
        #inputname = subject[7:11]
        #try:
          #execute('minccomplete %s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname))
          #num += 1
        #except subprocess.CalledProcessError as e:
          #print "Uh oh missing/incomplete file!"
          #print e.output
      #if num != targetnum:
        #print "missing files"
        #sys.exit(1)   
      #return        