#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import random



# "module load civet" for mincbet


job_submitted = False

def sge_submit(command): 
  execute("sge_batch " + command)
  global job_submitted
  job_submitted = True
  return


def pbs_add_job(command,job_list):        
  # add command to the end of a list to be submitted later
  job_list.append(command)
  return


def pbs_submit_jobs(job_list, depends, batchsize, time): 
  # call qbatch on jobs.list.txt with -J depends batchsize time
  # execute('./qbatch %s %s %s' %(job_list, batchsize, time))
  return


def batch(jobname, depends, command, job_list):
  if batch_system == 'sge':
    sge_submit('-J %s -H "%s" %s' %(jobname, depends, command))
  elif batch_system == 'pbs':
    pbs_add_job(command, job_list)
  elif batch_system == 'loc':
    execute(command)
  return


count = 0
for subject in glob.glob('inputs/*'):
  count += 1
  
def preprocessing():
  job_list = []
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    if not os.path.exists(inputname + '/'):
      mkdirp(inputname)                         # subfolder for each input 
      mkdirp(inputname + '/NUC')                # stores the corrected image
      mkdirp(inputname + '/NORM')               # stores the normalized image  
      mkdirp(inputname + '/masks')              # stores the mask of the input
      mkdirp(inputname + '/lin_tfiles')         # stores lsq6,lsq12 transformation files 
      mkdirp(inputname + '/output_lsq6')        # stores resampled images from lsq6 registration    

    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      batch('s1_%s' % inputname, "", './faceprocess.py preprocess %s %s' % (subject, image_type), job_list) 
      #if batch_system == 'sge': 
        #sge_submit("-J s1_%s ./process.py preprocess %s" % (inputname,subject))    
      #elif batch_system == 'pbs':
        #pbs_add_job('./process.py preprocess %s' %(inputname), job_list) 
        
   
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list, "", 4, "10:00:00")
    #pbs_submit_jobs('s1_<subject>', batchsize, time)
  return 


 
def nonpairwise():
  # STAGE 2A: alternative to pairwise registrations (i.e. too many inputs)
        
  # select a random input
  targetname = random.randint(1,count)
  if targetname < 10:
    targetname = "H00%s" % targetname
  else:
    targetname = "H0%s" % targetname
  #targetname = "H016"  
  
  # STAGE 2a: lsq12 transformation of each input to a randomly selected subject (not pairwise)
  # wait for all H###_lsq6.mnc files
  job_list = []
  for subject in glob.glob('inputs/*'):
    sourcename = subject[7:11]     
    sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(sourcename, sourcename)
    targetpath = "%s/output_lsq6/%s_lsq6.mnc" %(targetname, targetname)
    outputpath = "%s/lin_tfiles/%s_%s_lsq12.xfm" %(sourcename,sourcename,targetname)    
    if sourcename != targetname:
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        batch('sa_%s_%s' %(sourcename[2:4], targetname[2:4]), 's1_*', './faceprocess.py lsq12reg %s %s %s' %(sourcepath, targetpath, outputpath),job_list)       #pbs_submit('-J sa_%s_%s -H "s1_*" ./process.py lsq12reg %s %s %s' %(sourcename[2:4], targetname[2:4], sourcepath, targetpath, outputpath))
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list,"s1_*", 4,10)
        

  # STAGE 2b: average all lsq12 xfm files and invert this average
  # wait for all H###_H###_lsq12.xfm files
  job_list = []
  if not os.path.exists('lsq12avg_inverse.xfm'):
    batch('xfmavg_inv','sa_*', './faceprocess.py xfmavg_and_inv', job_list) 
    #pbs_submit('-J xfmavg_inv -H "sa_*" ./process.py xfmavg_and_inv')
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list,"sa_*",1, 10)
  
  
  # STAGE 2c: resample (apply inverted averaged xfm to randomly selected subject)
  # wait for lsq12avg_inverse.xfm
  job_list = []
  if not os.path.exists('avgsize.mnc'):
    batch('avgsize', 'xfmavg_inv', './faceprocess.py resample %s %s/output_lsq6/%s_lsq6.mnc avgsize.mnc' %('lsq12avg_inverse.xfm', targetname, targetname), job_list)  
    #pbs_submit('-J avgsize -H "xfmavg_inv" ./process.py resample %s %s/output_lsq6/%s_lsq6.mnc avgsize.mnc' %('lsq12avg_inverse.xfm', targetname, targe1tname))
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list,"xfmavg_inv",1, 10)
    
   
  # STAGE 2d: repeat lsq12 tranformation for every original input (ex. H001_lsq6.mnc) to the "average"
  # wait for H###_avglsq12.mnc of a single output
  job_list = []
  for subject in glob.glob('inputs/*'): 
    sourcename = subject[7:11]
    sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(sourcename, sourcename)
    targetpath = 'avgsize.mnc'
    outputpath = '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename) 
    if not os.path.exists('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename)):
      batch('sd_%s' %sourcename, 'avgsize', './faceprocess.py lsq12reg %s %s %s' %(sourcepath, targetpath, outputpath), job_list)
      #pbs_submit('-J sd_%s -H "avgsize" ./process.py lsq12reg %s %s %s' %(sourcename, sourcepath, targetpath, outputpath))
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list, "", 4, 10)
      
  # STAGE 3: resample   
  # wait for H###_lsq12.xfm of a single output
  job_list = []
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    xfm = '%s/lin_tfiles/%s_lsq12.xfm' %(inputname, inputname)
    sourcepath = "%s/output_lsq6/%s_lsq6.mnc" %(inputname, inputname)
    outputpath = '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)
    if not os.path.exists(inputname + '/timage_lsq12'):
      mkdirp(inputname + '/timage_lsq12')       # stores resampled images from lsq12 averages    
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)):
      batch('s3_%s' %inputname, 'sd_%s' %inputname, './faceprocess.py resample %s %s %s' %(xfm, sourcepath, outputpath), job_list)  
      #pbs_submit('-J s3_%s -H "sd_%s" ./process.py resample %s %s %s' %(inputname, inputname, xfm, sourcepath, outputpath))
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list, "", 4, 10)
  return  
    
    
def check2(path,targetnum):
  num = 0
  #for subject in glob.glob(path):
    #if execute('minccomplete %s' %subject):
      #print "status = clear for %s" %subject
      #num += 1
  #print "num of complete files== %s" %num
  #if num != int(targetnum):
    #print "file(s) not complete"
    #sys.exit(1)
  print "path == %s" %path
  print "type == %s" %type(targetnum)
  targetnum = int(targetnum)
  print "type now == %s" %type(targetnum)
  if len(glob.glob(path)) != targetnum:
    print "MISSING"
    sys.exit(1)
  return        


def pairwise():
  # STAGE 2: pairwise lsq12 registrations
  # wait for all H###_lsq6.mnc files
  job_list = []
  #execute('./process.py check H*/output_lsq6/H*_lsq6.mnc %s' %count)
  #check2('H*/output_lsq6/H*_lsq6.mnc', count)
  print count
  batch('check_lsq6', 's1_*','./faceprocess.py check H*/output_lsq6/H*_lsq6.mnc %s' % count, job_list)
  for subject in glob.glob('inputs/H002.mnc*'):
    sourcename = subject[7:11]
    if not os.path.exists(sourcename + '/pairwise_tfiles'):
      mkdirp(sourcename + '/pairwise_tfiles')
    for subject2 in glob.glob('inputs/*'):
      targetname = subject2[7:11]
      if sourcename != targetname:
        if not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
          batch('s2_%s_%s' %(sourcename[1:4], targetname[1:4]), 's1_*","check_lsq6', './faceprocess.py pairwise_reg %s %s' %(sourcename, targetname), job_list)
          #pbs_submit("-J s2_%s_%s -H 's1_*' ./process.py pairwise_reg %s %s" %(sourcename[1:4], targetname[1:4], sourcename, targetname))
 
  # STAGE 3: xfm average & resample
  # wait for all the pairwise registrations of a single input  
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      batch('s3_%s' %inputname, 's2_%s_*' %inputname[1:4], './faceprocess.py avg_and_resample %s' %inputname, job_list)
      #pbs_submit('-J s3_%s -H "s2_%s_*" ./process.py avg_and_resample %s' % (inputname, inputname[1:4], inputname))
  if batch_system == 'pbs':
    pbs_submit_jobs(job_list, "", 4, 10)
  return



def linavg():
  # STAGE 4: mincaverage   
  # wait for all H###_lsq12.mnc files
  job_list = []
  if not os.path.exists('avgimages/'):
    mkdirp('avgimages')              # stores average image after each registration
  if not os.path.exists('avgimages/linavg.mnc'):
    #execute('./process.py mnc_avg timage_lsq12 lsq12 linavg.mnc')
    batch('linavg', 's3_*', './faceprocess.py mnc_avg timage_lsq12 lsq12 linavg.mnc', job_list)
    #pbs_submit('-J linavg -H "s3_*" ./process.py mnc_avg timage_lsq12 lsq12 linavg.mnc')
  if batch_system == 'pbs':
    pbs_submit_job(job_list, "", 1, 10)
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
    if not os.path.exists(inputname + '/tfiles_nonlin'):
      mkdirp(inputname + '/tfiles_nonlin')      # stores transformation files from nonlinear registrations
      mkdirp(inputname + '/timages_nonlin')     # stores resampled images from nonlinear registrations      
    if not os.path.exists('%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      #batch('reg%s_%s' %(number, inputname[1:4]), '%s","check_%s' %(targetimage[0:-4], checkfor), './process.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations), job_list)
      sge_submit('-J reg%s_%s -H "%s","check_%s" ./faceprocess.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(number, inputname[1:4], targetimage[0:-4], checkfor, inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations)) 
      
  # wait for all H###_nonlin#.mnc files    
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    batch('nonlin%savg' %number,'reg%s_*","check_lsq12' %number, './faceprocess.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number), job_list)
    #pbs_submit('-J nonlin%savg -H "reg%s_*","check_lsq12" ./process.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number, number, number))
  if batch_system == 'pbs':
    pbs_submit_job(job_list, "", 4, 10)
  return
 
 
 
def nonlinregs():
  # Check for successful completion of (pairwise or non-pairwise) lsq12 registration 
  # if unsuccessful then stop program, else continue
  #pbs_submit('-J check_lsq12 -H "linavg" ./process.py check_lsq12 %s' % count)
  job_list = []
  batch('check_lsq12', 'linavg', './faceprocess.py check_lsq12 %s' % count, job_list)
  
  for subject in glob.glob('inputs/H002.mnc*'):
    inputname = subject[7:11]
    if not os.path.exists(inputname + '/tfiles_nonlin'):
      mkdirp(inputname + '/tfiles_nonlin')      # stores transformation files from nonlinear registrations
      mkdirp(inputname + '/timages_nonlin')     # stores resampled images from nonlinear registrations  
    nonlinreg_and_avg('1', 'timage_lsq12','lsq12','linavg.mnc', '100x1x1x1')
    batch('check_reg1', 'nonlin1avg', './faceprocess.py check_reg timages_nonlin nonlin1 nonlin1avg.mnc', job_list)
    #pbs_submit('-J check_reg1 -H "nonlin1avg" ./process.py check_reg timages_nonlin nonlin1 nonlin1avg.mnc')
    
    nonlinreg_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
    batch('check_reg2', 'nonlin2avg', './faceprocess.py check_reg timages_nonlin nonlin2 nonlin2avg.mnc', job_list)
    #pbs_submit('-J check_reg2 -H "nonlin2avg" ./process.py check_reg timages_nonlin nonlin2 nonlin2avg.mnc')
    
    nonlinreg_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
    batch('check_reg3', 'nonlin3avg', './faceprocess.py check_reg timages_nonlin nonlin3 nonlin3avg.mnc', job_list)
    #pbs_submit('-J check_reg3 -H "nonlin3avg" ./process.py check_reg timages_nonlin nonlin3 nonlin3avg.mnc')
    
    nonlinreg_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')
    batch('check_reg4', 'nonlin4avg', './faceprocess.py check_reg timages_nonlin nonlin4 nonlin4avg.mnc', job_list)
    #pbs_submit('-J check_reg4 -H "nonlin4avg" ./process.py check_reg timages_nonlin nonlin4 nonlin4avg.mnc')
  return



def final_stats():
  # wait for all nonlinear registrations of a single input to be complete  
  for subject in glob.glob('inputs/H001.mnc*'):
    inputname = subject[7:11]
    
    if not os.path.exists(inputname + '/final_stats'):
      mkdirp(inputname + '/final_stats')        # stores 
    if not os.path.exists('%s/final_stats/%s_grid.mnc' %(inputname, inputname)):
      #execute('./process.py deformation %s' % inputname)
      pbs_submit('-J s6_%s -H "reg*_%s","check_lsq12" ./faceprocess.py deformation %s' % (inputname, inputname[1:4], inputname))          
  
   # wait for deformation grid of a single input  
  for subject in glob.glob('inputs/H001.mnc*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/final_stats/%s_blur.mnc' %(inputname, inputname)):
      pbs_submit('-J s7_%s -H "s6_%s","check_lsq12" ./faceprocess.py det_and_blur %s' % (inputname, inputname, inputname)) 
  return







if __name__ == '__main__':
  cmd = sys.argv[1]           # first command line argument: stage to execute (preprocess, lsq12_p, lsq12_n, lsq12, linavg, nonlinreg, finalstats, all)           
  batch_system = sys.argv[2]  # second command line argument: batch system to run pipeline (sge, pbs, loc)
  image_type = sys.argv[3]    # third commmand line argument: brain (b) or craniofacial (f)
 
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