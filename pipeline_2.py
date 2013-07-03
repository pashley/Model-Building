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


# "module load civet" for mincbet
        
#count = 0
#for subject in glob.glob('inputs/*'):
  #count += 1



def submit_jobs(jobname, depends, command, job_list, batchsize, time, num, numjobs, name_file): 
  if batch_system == 'sge':
    execute('sge_batch -J %s -H "%s" %s' %(jobname, depends, command))
  elif batch_system == 'pbs':
    job_list.append(command)
    if num == numjobs:       # when all commands are added to the list, submit the list
      #cmdfileinfo = tempfile.mkstemp(dir='./')
      outputfile = open('%s' %name_file, 'w')
      outputfile.write("\n".join(job_list))
      outputfile.close()
      if jobname[0:2] == 's1':
        execute('qbatch -N %s %s %s %s ' %(jobname, name_file, batchsize, time))  # no dependency for first stage
      else:
        execute('qbatch -N %s --afterok_pattern %s %s %s %s ' %(jobname, depends, name_file, batchsize, time))
      #cmdfile = open(cmdfileinfo[1], 'w')
      #cmdfile.write("\n".join(job_list))
      #cmdfile.close()
      #execute('qbatch --afterok_pattern %s %s %s %s ' %(depends, basename(cmdfileinfo[1]), batchsize, time))
      #os.remove(cmdfile.name)
  elif batch_system == 'loc':  # run locally
    execute(command)
  return


def preprocessing():
  job_list = []
  num = 0
  for subject in listofinputs:
    inputname = subject[0:-4] 
    complete = len(glob.glob('*/output_lsq6/*_lsq6.mnc'))
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      num += 1
      submit_jobs('s1_%s' % inputname, "something", './process.py preprocess %s %s' %(subject, image_type), job_list, 8, "2:00:00", num, count-complete, 'preprocess') 
      # fix dependency
  return 

 
def nonpairwise():         # alternative to pairwise registrations (i.e. too many inputs)          
  # randomly select an input
  target = random.randint(1,count)
  target = listofinputs[target]
  targetname = target[0:-4]
  targetname = 'H005'
  
  # STAGE 2A: lsq12 transformation of each input to a randomly selected subject (not pairwise)
  job_list = []
  num = 0
  for subject in listofinputs:
    sourcename = subject[0:-4]     
    complete = len(glob.glob('*/lin_tfiles/*_*_lsq12.xfm'))
    if sourcename != targetname:
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        num += 1
        submit_jobs('sa_%s_%s' %(sourcename[2:4], targetname[2:4]), 's1_*', './process.py lsq12reg %s %s' %(sourcename, targetname),job_list, 8, "2:00:00", num, count-complete-1, 'stage2a')
  
  # STAGE 2B: average all lsq12 xfm files, invert this average, resample (apply inverted averaged xfm to randomly selected subject)
  # wait for all H*_H*_lsq12.xfm files
  job_list = []
  if not os.path.exists('avgsize.mnc'):
    submit_jobs('avgsize','sa_*', './process.py xfmavg_inv_resample %s' %targetname, job_list, 8, "2:00:00", 1, 1,'avgsize') 
   
  # STAGE 3: repeat lsq12 tranformation for every original input (ex. H001_lsq6.mnc) to the "average size", then resample (wait for avgsize.mnc)
  job_list = []
  num = 0
  for subject in listofinputs: 
    sourcename = subject[0:-4]
    complete = len(glob.glob('*/timage_lsq12/*_lsq12.mnc'))   
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename)):         
      num += 1
      submit_jobs('s3_%s' %sourcename, 'avgsize*', './process.py lsq12reg_and_resample %s' %sourcename, job_list, 8, "2:00:00", num, count-complete, 'stage3')
  return  
    
 
def pairwise():
  # STAGE 2: pairwise lsq12 registrations (wait for all H*_lsq6.mnc files)
  job_list = []
  num = 0
  for subject in listofinputs:
    sourcename = subject[0:-4]
    for subject2 in listofinputs:
      targetname = subject2[0:-4]
      complete = len(glob.glob('*/pairwise_tfiles/*_*_lsq12.xfm'))
      if sourcename != targetname and not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        num += 1
        submit_jobs('s2_%s_%s' %(sourcename[1:4], targetname[1:4]), 's1_*', './process.py pairwise_reg %s %s' %(sourcename, targetname), job_list, 8, "2:00:00", num, ((count-1)*count)-complete, 'plsq12')
          
  # STAGE 3: xfm average & resample (wait for all the pairwise registrations)
  job_list = []
  num = 0
  for subject in listofinputs:
    inputname = subject[0:-4]
    complete = len(glob.glob('*/timage_lsq12/*_lsq12.mnc'))
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      num += 1
      submit_jobs('s3_%s' %inputname, 's2_*', './process.py xfmavg_and_resample %s' %inputname, job_list, 8, "2:00:00", num, count-complete, 'p_res')
  return


def linavg():
  # STAGE 4: mincaverage linearly processed images (wait for all H*_lsq12.mnc files)
  job_list = []
  if not os.path.exists('avgimages/linavg.mnc'):
    submit_jobs('linavg', 's3_*', './process.py mnc_avg timage_lsq12 lsq12 linavg.mnc', job_list, 8, "1:00:00", 1, 1, 'linavg')
  return


  
def nonlinreg_and_avg(number, sourcefolder,inputregname, targetimage, iterations):
  # STAGE 5: nonlinear registrations & averaging (wait for previous average == targetimage)
  job_list = []
  num = 0
  for subject in listofinputs:
    inputname = subject[0:-4]  
    complete = len(glob.glob('*/timages_nonlin/*_nonlin%s.mnc' %number))
    if not os.path.exists('%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      num += 1
      submit_jobs('reg%s_%s' %(number, inputname[1:4]), '%s*' %targetimage[0:-4], './process.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations), job_list, 8, "2:00:00", num, count-complete, 'nlreg%s'%number)
  
  job_list = []
  # wait for all H*_nonlin#.mnc files    
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    submit_jobs('nonlin%savg' %number, 'reg%s_*' %number, './process.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number), job_list, 8, "2:00:00",1,1, 'nlavg%s'%number)
  return
 
  

def nonlinregs():
  # Check completion of (pairwise or non-pairwise) lsq12 registration 
  # if unsuccessful then stop, else continue
  job_list = []
  string = ""
  for subject in listofinputs:
    string += subject
    string += " "
  #submit_jobs('check_lsq12', 'linavg', './process.py check_lsq12 %s' %string, job_list, 8, '1:00:00', 1,1)
  nonlinreg_and_avg('1', 'timage_lsq12','lsq12','linavg.mnc', '100x1x1x1')
  nonlinreg_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
  nonlinreg_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
  nonlinreg_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')
  return


def final_stats():
  # STAGE 6: deformations, determinants (wait for all nonlinear registrations) 
  job_list = []
  num = 0
  for subject in listofinputs:
    inputname = subject[0:-4]
    complete = len(glob.glob('*/final_stats/*_blur.mnc'))
    if not os.path.exists('%s/final_stats/%s_blur.mnc' %(inputname, inputname)):
      num += 1
      submit_jobs('s6_%s' % inputname, 'nonlin4avg*', './process.py deformation %s' % inputname, job_list, 8, "2:00:00", num, count-complete,'fstats')
  # dependency ???
  return




if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  #parser.add_argument("-s",
                      #choices=['preprocess','lsq12', 'lsq12-p', 'lsq12-n',
                               #'linavg', 'nonlinreg', 'finalstats'],
                      #help="stage to execute")
  parser.add_argument("-face", action="store_true",
                      help="craniofacial structure (default brain)")
  parser.add_argument("-prefix", help= "selects a subset of inputs within the inputs directory")
  parser.add_argument("-rp", action="store_true",
                    help="run pipeline with pairwise lsq12 registrations")
  parser.add_argument("-rn", action= "store_true",
                      help="run pipeline with non-pairwise lsq12 registrations")                    
  parser.add_argument("-p", action="store_true", 
                      help="preprocessing: correct, normalize, mask, lsq6, resample")
  parser.add_argument("-lsq12",action="store_true",
                      help="lsq12 registrations (method based on number of inputs)")
  parser.add_argument("-lsq12p", action="store_true",
                       help="pairwise lsq12 registrations")
  parser.add_argument("-lsq12n", action="store_true",
                      help="non-pairwise lsq12 registrations")
  parser.add_argument("-a",action="store_true", 
                      help="average linearly processed images")
  parser.add_argument("-n", action="store_true", 
                      help="4 nonlinear registrations: (mincANTS, resample, average)x4")
  parser.add_argument("-f", action="store_true",
                      help="final stats: deformation fields, determinant")
  #parser.add_argument("-minctracc", action="store_true",
                      #help='minctracc')
  parser.add_argument("batch_system", choices=['sge', 'pbs', 'loc'],
                      help="batch system to process jobs")
    

  args = parser.parse_args()
  batch_system = args.batch_system
  if args.face:
    image_type = 'face'
  else:
    image_type = 'brain'
  #image_type = args.image
  prefix = args.prefix

  listofinputs = []
  inputdir = 'inputs/*%s*' % prefix
  if prefix == None:        # when no prefix is specified, process all inputs
    inputdir = 'inputs/*' 
  for subject in glob.glob(inputdir):
    listofinputs.append(basename(subject))
  inputfile = open('inputlist.xfm', 'w')
  inputfile.write("\n".join(listofinputs))

  
  count = len(listofinputs)

  for subject in listofinputs:
    name = subject[0:-4]   # always .mnc files???
    if not os.path.exists(name + '/'):
      mkdirp(name)                          
      mkdirp(name + '/NUC')                
      mkdirp(name + '/NORM')
      #mkdirp(name + '/sienax_output_tmp')
      mkdirp(name + '/masks')              
      mkdirp(name + '/lin_tfiles')          
      mkdirp(name + '/output_lsq6')        
      mkdirp(name + '/pairwise_tfiles')      
      mkdirp(name + '/timage_lsq12')         
      mkdirp('avgimages')                  
      mkdirp(name + '/tfiles_nonlin')      
      mkdirp(name + '/timages_nonlin')     
      mkdirp(name + '/final_stats')
    
    
  
  if args.p:
    preprocessing()
  elif args.lsq12:
    if count > 20:
      nonpairwise()
    elif count <= 20:
      pairwise()    
  elif args.lsq12p:
    pairwise()
  elif args.lsq12n:
    nonpairwise()
  elif args.a:
    linavg()
  elif args.n:
    nonlinregs()
  elif args.f:
    final_stats()
  elif args.rp:
    preprocessing()
    pairwise()
    linavg()
    nonlinregs()
    final_stats()
  elif args.rn:
    preprocessing()
    nonpairwise()
    linavg()
    nonlinregs()
    final_stats()
  else:                  # execute all stages when no particular stage is specified
    preprocessing()
    if count > 20:       # method of lsq12 registrations depends on # of inputs
      nonpairwise()
    elif count <= 20:
      pairwise()
    linavg()
    nonlinregs()
    final_stats()    
