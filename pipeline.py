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


def submit_jobs(jobname, depends, job_list, batchsize, time, name_file): 
  if batch_system == 'sge':
    for command in job_list:
      jobname2 = jobname
      if len(job_list) != 1:                          # just to get nicer job names
        command_split = command.split()
        jobname2 = jobname + "_" + command_split[2]
      #print jobname2  + " " + command
      execute('sge_batch -J %s -H "%s" %s' %(jobname2, depends, command))
  
  elif batch_system == 'pbs':
    outputfile = open('%s' %name_file, 'w')
    outputfile.write("\n".join(job_list))
    outputfile.close()
    execute('./MAGeTbrain/bin/qbatch -N %s --afterok_pattern %s %s %s %s ' %(jobname, depends, name_file, batchsize, time))
      #cmdfileinfo = tempfile.mkstemp(dir='./')
      #cmdfile = open(cmdfileinfo[1], 'w')
      #cmdfile.write("\n".join(job_list))
      #cmdfile.close()
      #execute('qbatch --afterok_pattern %s %s %s %s ' %(depends, basename(cmdfileinfo[1]), batchsize, time))
      #os.remove(cmdfile.name)
  elif batch_system == 'loc':  # run locally
    for command in job_list:
      execute(command)
  return


def preprocessing():
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
  submit_jobs('s1a', "something", job_list, 8, "2:00:00", 'preprocess_a') # fix dependency?
  if target_type == 'random' or image_type == 'face':
    preprocessing_2()
  

  
  #job_list = []
  #if target_type == 'given' and not image_type == 'face': 
    #for inputname in listofinputs: 
      #if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
        #job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
    #submit_jobs('s1' , "something", job_list, 8, "2:00:00", 'preprocess')             # fix dependency
  
  #elif target_type == 'random' or image_type == 'face':
    #for inputname in listofinputs:    
      #if not os.path.exists('%s/masks/mask.mnc' %inputname):
        #job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
    #submit_jobs('s1a', "something", job_list, 8, "2:00:00", 'preprocess_a') # fix dependency?
    #preprocessing_2()
    
     #what about given target image and face?
  return 


def preprocessing_2():
  job_list =['./process.py autocrop %s %s' %(image_type, targetname)]
  submit_jobs('s1b_%s' %targetname, 's1a_*', job_list, 8, "1:00:00", 'autocrop')
  
  job_list = []
  for sourcename in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py lsq6reg_and_resample %s %s %s' %(sourcename, targetname, image_type))
  submit_jobs('s1c', 's1b_*', job_list, 8, "2:00:00", 'preprocess_c')
  return

 
def nonpairwise():         # alternative to pairwise registrations (i.e. too many inputs)          
  # STAGE 2A: lsq12 transformation of each input to a randomly selected subject (not pairwise)
  job_list = []
  for sourcename in listofinputs:     
    if sourcename != targetname:
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py lsq12reg %s %s' %(sourcename, targetname))
  submit_jobs('s2', 's1*', job_list, 8, "2:00:00",'stage2a')
        
  # STAGE 2B: average all lsq12 xfm files, invert this average, resample (apply inverted averaged xfm to randomly selected subject)
  # wait for all H*_H*_lsq12.xfm files
  job_list = ['./process.py xfmavg_inv_resample %s' %targetname]
  if not os.path.exists('avgsize.mnc'):
    submit_jobs('avgsize','s2_*', job_list, 8, "2:00:00", 'avgsize') 
   
  # STAGE 3: repeat lsq12 tranformation for every original input (ex. H001_lsq6.mnc) to the "average size", then resample (wait for avgsize.mnc)
  job_list = []
  for sourcename in listofinputs:    
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py lsq12reg_and_resample %s' %sourcename)
  submit_jobs('s3', 'avgsize*', job_list, 8, "2:00:00", 'stage3')
  return  
    
 
def pairwise():
  # STAGE 2: pairwise lsq12 registrations (wait for all H*_lsq6.mnc files)
  job_list = []
  for sourcename in listofinputs:
    for targetname in listofinputs:
      if sourcename != targetname and not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py pairwise_reg %s %s' %(sourcename, targetname))      
  submit_jobs('s2', 's1*', job_list, 8, "2:00:00", 'plsq12')
          
  # STAGE 3: xfm average & resample (wait for all the pairwise registrations)
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      job_list.append('./process.py xfmavg_and_resample %s' %inputname)
  submit_jobs('s3', 's2_*', job_list, 8, "2:00:00", 'p_res')
  return


def linavg():
  # STAGE 4: mincaverage linearly processed images (wait for all H*_lsq12.mnc files) and check for successful completion of lsq12 registration stage
  job_list = ['./process.py linavg_and_check timage_lsq12 lsq12 linavg.mnc']
  if not os.path.exists('avgimages/linavg.mnc'):
    #submit_jobs('linavg', 's3_*', './process.py mnc_avg timage_lsq12 lsq12 linavg.mnc', job_list, 8, "1:00:00", 1, 1, 'linavg')
    submit_jobs('linavg', 's3_*', job_list, 8, "1:00:00", 'linavg')

  #submit_jobs('check_lsq12', 'linavg', './process.py check_lsq12 %s' %string, job_list, 8, '1:00:00', 1,1)
  return


  
def nonlinreg_and_avg(number, sourcefolder,inputregname, targetimage, iterations):
  # STAGE 5: nonlinear registrations & averaging (wait for previous average == targetimage)
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      job_list.append('./process.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations))
  if targetimage == 'linavg.mnc' and batch_system == 'pbs':  # WHY?
    print "linear average"
    submit_jobs('reg%s' %number, 'linavg_*', job_list, 8, "2:00:00", 'nlreg%s'%number)
  else:
    submit_jobs('reg%s' %number, '%s*' %targetimage[0:-4], job_list, 8, "2:00:00", 'nlreg%s'%number)
  
 
  # wait for all H*_nonlin#.mnc files
  job_list = ['./process.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number)]
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    submit_jobs('nonlin%savg' %number, 'reg%s_*' %number, job_list, 8, "2:00:00", 'nlavg%s'%number)
  return
 
  
def call_ANTS():
  nonlinreg_and_avg('1', 'timage_lsq12', 'lsq12', 'linavg.mnc', '100x1x1x1')
  nonlinreg_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
  nonlinreg_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
  nonlinreg_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')
  return


def tracc_resmp(stage, fwhm, iterations, step, model):
  # CHECK num, num_jobs, complete...
  job_list = ['mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4])]
  if not os.path.exists('avgimages/nonlin%savg.mnc' %stage):
    submit_jobs('blurmod%s' %stage, "%s*" %model[0:-4], job_list, 8, "1:00:00", "blurmod%s"%stage)
    
    job_list = []
    for inputname in listofinputs:
      job_list.append('./process.py tracc %s %s %s %s %s %s' %(inputname, stage, fwhm, iterations, step, model))
    submit_jobs('tr%s' %stage, 'blurmod%s*' %stage, job_list, 8, "2:00:00", 'minctracc_%s' %stage)
    
    job_list = ['./process.py mnc_avg minctracc_out nlin%s nonlin%savg.mnc' %(stage, stage)]
    submit_jobs('nonlin%savg' %stage, 'tr%s_*' %stage, job_list, 8, "1:00:00", 'nlavg%s'%stage)    
  return


def call_tracc():
  for inputname in listofinputs:
    if not os.path.exists(inputname + '/minctracc_out'):
      mkdirp(inputname + '/minctracc_out')   
  #tracc_resmp(stage, Gaussian blur, iterations, step size, model name) 
  tracc_resmp(1, 16, 30, 8, 'linavg.mnc')
  tracc_resmp(2, 8, 30, 8, 'nonlin1avg.mnc')
  tracc_resmp(3, 8, 30, 4, 'nonlin2avg.mnc') 
  tracc_resmp(4, 4, 30, 4, 'nonlin3avg.mnc')
  tracc_resmp(5, 4, 10, 2, 'nonlin4avg.mnc')
  tracc_resmp(6, 2, 10, 2, 'nonlin5avg.mnc')  
  return

def final_stats():
  # STAGE 6: deformations, determinants (wait for all nonlinear registrations) 
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/final_stats/%s_blur.mnc' %(inputname, inputname)):
      job_list.append( './process.py deformation %s' %inputname)
  submit_jobs('s6', 'nonlin*', job_list, 8, "2:00:00", 'fstats')
  # dependency ???
  return

def run_all(option):
  '''Run the entire pipeline with the option selected.
  rp = pairwise lsq12 
  rpt = pairwise lsq12 & minctracc
  rn = non-pairwise lsq12 (& mincANTS)
  rnt = non-pairwise lsq12 & minctracc
  '''
  preprocessing()
  if option == 'rp' or option == 'rpt':
    pairwise()
  elif option == 'rn' or option == 'rnt':
    nonpairwise()
  else:               # when no option is specified the method of lsq12 registrations is dependent on the number of inputs
    if count <= 20:
      pairwise()
    elif count > 20:
      nonpairwise()
  linavg()
  if option == 'rpt' or option == 'rnt' or option == 'rt':
    call_tracc()
  else:
    call_ANTS()  # default nonlinear 
  final_stats()
  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("-face", action="store_true",
                      help="craniofacial structure (default brain)")
  parser.add_argument("-prefix", action="append",    # possible to specify more than one prefix
                      help= "selects subsets of inputs within the inputs directory")
  parser.add_argument("-check_inputs", action="store_true",
                      help="generate list of inputs to be processed")
  parser.add_argument("-rp", action="store_true",
                    help="run pipeline with pairwise lsq12 registrations")
  parser.add_argument("-rn", action= "store_true",
                      help="run pipeline with non-pairwise lsq12 registrations")
  parser.add_argument("-rt", action="store_true",
                      help="run pipeline with minctracc")
  parser.add_argument("-rpt", action="store_true",
                      help="run pipeline with pairwise lsq12 registrations and minctracc")
  parser.add_argument("-rnt", action="store_true", 
                      help="run pipeline with non-pairwise lsq12 registrations and minctracc")
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
  parser.add_argument("-tracc",action="store_true",
                      help="minctracc nonlinear transformations (6 iterations with preset parameters)")
  parser.add_argument("-n", action="store_true", 
                      help="4 nonlinear registrations: (mincANTS, resample, average)x4")
  
  parser.add_argument("-f", action="store_true",
                      help="final stats: deformation fields, determinant")
  parser.add_argument("batch_system", choices=['sge', 'pbs', 'loc'],
                      help="batch system to process jobs")
  parser.add_argument("-random_target", action="store_true",
                      help="randomly select one input to be target image")
  
  args = parser.parse_args()
  batch_system = args.batch_system
  prefix_list = args.prefix
 
  if args.face:
    image_type = 'face'
  else:
    image_type = 'brain' # default
  
  if args.random_target:
    target_type = 'random'
  else:
    target_type = 'given' # default  
  

  listofinputs = []
  if prefix_list == None:        # when no prefix is specified, process all inputs
    for subject in glob.glob('inputs/*'):
      thefile = basename(subject)
      listofinputs.append(thefile[0:-4])    # always a minc file??
  else:
    for prefix in prefix_list:
      inputdir = 'inputs/*%s*' % prefix
      for subject in glob.glob(inputdir):
        thefile = basename(subject)
        listofinputs.append(thefile[0:-4])
  inputfile = open('inputlist.xfm', 'w')    
  inputfile.write("\n".join(listofinputs))
  inputfile.close

  if args.check_inputs:
    sys.exit(1)
    
  count = len(listofinputs)  # number of inputs to process

  for subject in listofinputs:
    if not os.path.exists(subject + '/'):
      mkdirp(subject)                          
      mkdirp(subject + '/NUC')                
      mkdirp(subject + '/NORM')
      mkdirp(subject + '/masks')              
      mkdirp(subject + '/lin_tfiles')          
      mkdirp(subject + '/output_lsq6')        
      mkdirp(subject + '/pairwise_tfiles')      
      mkdirp(subject + '/timage_lsq12')                        
      mkdirp(subject + '/tfiles_nonlin')      # don't need when minctracc
      mkdirp(subject + '/timages_nonlin')     # don't need when minctracc
      mkdirp(subject + '/final_stats')
  
  if not os.path.exists('avgimages'):
    mkdirp('avgimages') 
    
    
  target = random.randint(0,count-1) 
  targetname = listofinputs[target]
  print "targetname == %s" %targetname
    
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
    call_ANTS()
  elif args.f:
    final_stats()
  elif args.rp:       # run pipeline with pairwise & mincANTS
    run_all('rp')
  elif args.rn:       # run pipeline with nonpairwise & mincANTS
    run_all('rn')
  elif args.rt:
    run_all('rt')
  elif args.rpt:      # run pipeline with pairwise & minctracc
    run_all('rpt')
  elif args.rnt:      # run pipeline with nonpairwise & minctracc   
    run_all('rnt') 
  elif args.tracc:
    call_tracc()
  else:               # execute all stages when no particular stage is specified
    run_all('all')
     
