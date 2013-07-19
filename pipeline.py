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

"""   

ROUGHT DRAFT of this description:


processes MINC files.
-The following scripts must be in the directory in which pipeline.py is being executed:
    - process.py
    - utils.py
    - utils.pyc  ??
    - xfmjoin 
    - MAGetbrain ?? 
    - targetimage.mnc (if target image is provided)
    - targetmask.mnc (if target image is provided)
    
    
    
To run 

"""


def submit_jobs(jobname, depends, job_list):
  """ Submits a list of jobs to the batch system specified by the user """
  # proceed to submitting if there is at least one job in the list 
  if len(job_list) >= 1:     
    
    if batch_system == 'sge':
      for command in job_list:
        # Add the input's name to the name of input-specific jobs 
        if len(job_list) != 1:                      
          command_split = command.split()
          thejobname = jobname + "_" + command_split[2] # the input's name is the 2nd argument in the command 
        else:
          thejobname = jobname
        #print thejobname  + " " + command    
        execute('sge_batch -J %s -H "%s" %s' %(thejobname, depends, command))
    
    elif batch_system == 'pbs':
      # create a temporary file with the list of jobs to submit to qbatch
      cmdfileinfo = tempfile.mkstemp(dir='./') 
      cmdfile = open(cmdfileinfo[1], 'w')
      cmdfile.write("\n".join(job_list))
      cmdfile.close()
       
      if depends[-2] != '_':            # sometimes dependency names without the underscore aren't recognized on scinet
        depends = depends[0:-1] + "_*"  # so, add the underscore to dependency names that don't have one 
        print depends
      batchsize = 8
      if len(job_list) == 1:
        time = "1:00:00"  # default walltime for 1 batch of 1 tasks
      else:
        time = "2:00:00"  # default walltime for 1 batch of 8 tasks
      execute('./MAGeTbrain/bin/qbatch -N %s --afterok_pattern %s %s %s %s ' %(jobname, depends,  basename(cmdfileinfo[1]), batchsize, time))
      os.remove(cmdfile.name)
    
    elif batch_system == 'local':  # run locally
      for command in job_list:
        execute(command)
  return




def call_preprocess():
  """Calls the preprocess stage for every input and submits the jobs"""
 
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
  submit_jobs('s1_a', "something_*", job_list) # fix dependency?
  if target_type == 'random' or image_type == 'face':
    call_preprocess2()
  return 


def call_preprocess2():
  """ Calls the Part 2 of the preprocessing stage 
  Executed for craniofacial structure image processing or when the target image is a randomly selected subject"""
  job_list = ['./process.py autocrop %s %s' %(image_type,targetname)]
  submit_jobs('s1_b', 's1_a_*', job_list)
  
  job_list = []
  for sourcename in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py preprocess2 %s %s %s' %(sourcename, targetname, image_type))
  #submit_jobs('s1_b', 's1_a_*', job_list)
  submit_jobs('s1_c', 's1_b*', job_list)
  return

 
def nonpairwise():
  """ Sets up the non-pairwise 12-parameter registration stage.
  This is the alternative to pairwise 2-parameter registrations (when there are too many inputs,for instance)"""
  # PART 1: calls lsq12reg 
  job_list = []
  for sourcename in listofinputs:     
    if sourcename != targetname: 
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py lsq12reg %s %s' %(sourcename, targetname))
  submit_jobs('s2', 's1*', job_list)
        
  # PART 2: calls xfmavg_inv_resample
  job_list = ['./process.py xfmavg_inv_resample %s' %targetname]
  if not os.path.exists('avgsize.mnc'):
    submit_jobs('avgsize','s2_*', job_list) 
   
  # PART 3: calls lsq12reg_and_resample
  job_list = []
  for sourcename in listofinputs:    
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py lsq12reg_and_resample %s' %sourcename)
  submit_jobs('s3', 'avgsize*', job_list)
  return  
    
 
def pairwise():
  """ Sets up the pairwise 12-parameter registration stage"""
  # PART 1: calls pairwise_reg
  job_list = []
  for sourcename in listofinputs:
    for targetname in listofinputs:
      if sourcename != targetname and not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py pairwise_reg %s %s' %(sourcename, targetname))      
  submit_jobs('s2', 's1*', job_list)
          
  # PART 2: calls xfmavg_and_resample
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      job_list.append('./process.py xfmavg_and_resample %s' %inputname)
  submit_jobs('s3', 's2_*', job_list)
  return


def call_linavg():
  """Average linearly processed images & check for completion of the lsq12 stage """
  job_list = ['./process.py linavg_and_check timage_lsq12 lsq12 linavg.mnc']
  if not os.path.exists('avgimages/linavg.mnc'):
    submit_jobs('linavg', 's3_*', job_list)
  return

  
def ANTS_and_avg(number, sourcefolder,inputregname, targetimage, iterations):
  """ Sets up the nonlinear processing stage which uses mincANTS"""
  # PART 1: calls nonlin_reg 
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      job_list.append('./process.py nonlin_reg %s %s/%s/%s_%s.mnc %s %s %s' %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations))
  submit_jobs('reg%s' %number, '%s*' %targetimage[0:-4], job_list)
 
 # PART 2: calls mnc_avg
  job_list = ['./process.py mnc_avg timages_nonlin nonlin%s nonlin%savg.mnc' %(number, number)]
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    submit_jobs('nonlin%savg' %number, 'reg%s_*' %number, job_list)
  return
 
  
def call_ANTS(iteration):
  """Calls each iteration of mincANTS with the appropriate parameters"""
  if iteration == '1' or iteration == 'all':
    ANTS_and_avg('1', 'timage_lsq12', 'lsq12', 'linavg.mnc', '100x1x1x1')
  if iteration == '2' or iteration == 'all':
    ANTS_and_avg('2', 'timages_nonlin', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
  if iteration == '3' or iteration == 'all':
    ANTS_and_avg('3', 'timages_nonlin', 'nonlin2', 'nonlin2avg.mnc', '100x5')
  if iteration == '4' or iteration == 'all':
    ANTS_and_avg('4', 'timages_nonlin', 'nonlin3', 'nonlin3avg.mnc', '5x20')
  return


def tracc_resmp(stage, fwhm, iterations, step, model):
  """Sets up the nonlinear processing stage which uses minctracc"""
  # PART 1
  job_list = ['mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4])]
  if not os.path.exists('avgimages/nonlin%savg.mnc' %stage):
    submit_jobs('blurmod%s' %stage, "%s*" %model[0:-4], job_list)
    
    # PART 2
    job_list = []
    for inputname in listofinputs:
      job_list.append('./process.py tracc %s %s %s %s %s %s' %(inputname, stage, fwhm, iterations, step, model))
    submit_jobs('tr%s' %stage, 'blurmod%s*' %stage, job_list)
    
    # PART 3
    job_list = ['./process.py mnc_avg minctracc_out nlin%s nonlin%savg.mnc' %(stage, stage)]
    submit_jobs('nonlin%savg' %stage, 'tr%s_*' %stage, job_list)    
  return


def call_tracc():
  """Calls each iteration of mintracc with the appropriate parameters"""
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


def call_final_stats():
  """Calls the deformation fields stage""" 
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/final_stats/%s_blur.mnc' %(inputname, inputname)):
      job_list.append( './process.py deformation %s' %inputname)
  if batch_system == 'pbs':           #TODO: fix depends name
    submit_jobs('s6', 'nonlin*_*', job_list)
  else:
    submit_jobs('s6', 'nonlin*', job_list)
  # dependency ???
  return


def run_all(option):
  '''Run the entire pipeline with the option selected.
  rp = pairwise lsq12 
  rpt = pairwise lsq12 & minctracc
  rn = non-pairwise lsq12 (& mincANTS)
  rnt = non-pairwise lsq12 & minctracc
  rcl = landmarked-based facial feature analysis (default: mincANTS)
  '''
  call_preprocess()
  if option == 'rp' or option == 'rpt':
    pairwise()
  elif option == 'rn' or option == 'rnt':
    nonpairwise()
  else:               # when no option is specified the method of lsq12 registrations is dependent on the number of inputs
    if count <= 300:
      pairwise()
    elif count > 300:
      nonpairwise()
  call_linavg()
  if option == 'rpt' or option == 'rnt' or option == 'rt':
    call_tracc()
  else:
    call_ANTS('all')  # default nonlinear 
  call_final_stats()
  
  if option == 'rcl':
    landmark()
  return


def call_longitudinal():
  # run entire pipeline on time-1
  run_all('all')
  
  # nu_correct time-2
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/time2/%s_nuc.mnc' %(inputname, inputname)):
      job_list.append('./longitudinal.py preprocess_time2 %s' %inputname)
  submit_jobs('nuc_t2','s6_*',job_list) #TODO: fix dependency name
  
  
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/det3_blur.mnc'):
      job_list.append('./longitudinal.py longitudinal %s' %inputname)
  submit_jobs('lng', 'nuc_t2*', job_list)
  return





def landmark():
  job_list = ['./landmark_facial.py warp_landmarked_2_model']
  if not os.path.exists('landmarked_nonlin_model.mnc'):
    submit_jobs('lnmk_model','s6_*', job_list)
    
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/landmarked/%s_landmarked.mnc' %(inputname, inputname)):
      job_list.append('./landmark_facial.py warp_model_2_subject %s' %inputname)
  submit_jobs('lndmk', 's6_*', job_list)    
  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("-face", action="store_true",
                      help="craniofacial structure imaging (default brain imaging)")
  parser.add_argument("-prefix", action="append",    # possible to specify more than one prefix
                      help= "specify subset(s) of inputs within the inputs directory to process")
  parser.add_argument("-check_inputs", action="store_true",
                      help="generate a file with the list of inputs to be processed")
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
  parser.add_argument("-rcl", action="store_true", 
                      help="run pipeline with craniofacial structure imaging & landmark-based facial feature analysis")
  parser.add_argument("-p", action="store_true", 
                      help="preprocessing: correct, normalize, mask, lsq6, resample")
  parser.add_argument("-lsq12",action="store_true",
                      help="lsq12 registrations (method based on number of inputs)")
  parser.add_argument("-lsq12p", action="store_true",
                       help="pairwise lsq12 registrations")
  parser.add_argument("-lsq12n", action="store_true",
                      help="non-pairwise lsq12 registrations")
  parser.add_argument("-linavg",action="store_true", 
                      help="average linearly processed images")
  parser.add_argument("-tracc",action="store_true",
                      help="minctracc nonlinear transformations (6 iterations with preset parameters)")
  parser.add_argument("-ants", action="store_true", 
                      help="4 nonlinear registrations: (mincANTS, resample, average)x4")
  parser.add_argument("-ants_stage", choices=['1','2','3','4'], 
                      help="run a single interation of mincANTS")
  parser.add_argument("-f", action="store_true",
                      help="final stats: deformation fields, determinant")
  parser.add_argument("batch_system", choices=['sge', 'pbs', 'local'],
                      help="batch system to process jobs")
  parser.add_argument("-l", action="store_true",
                      help="testing longitudinal")
  parser.add_argument("-random_target", action="store_true",
                      help="randomly select one input to be target image")
  parser.add_argument("-landmark",action="store_true",
                      help="landmark-based facial feature analysis")
  
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
  
  if args.l:
    string 
    for subject in listofinputs:
      execute("./longitudinal.py nlreg %s" %subject)
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
      mkdirp(subject + '/pairwise_tfiles')    # don't need when nonpw  
      mkdirp(subject + '/timage_lsq12')                        
      mkdirp(subject + '/tfiles_nonlin')      # don't need when minctracc
      mkdirp(subject + '/timages_nonlin')     # don't need when minctracc
      mkdirp(subject + '/final_stats')
  
  if not os.path.exists('avgimages'):
    mkdirp('avgimages') 
    
    
  target = random.randint(0,count-1) 
  targetname = listofinputs[target]
  
    
  if args.p:
    call_preprocess()
  elif args.lsq12:
    if count > 300:
      nonpairwise()
    elif count <= 300:
      pairwise()    
  elif args.lsq12p:
    pairwise()
  elif args.lsq12n:
    nonpairwise()
  elif args.linavg:
    call_linavg()
  elif args.ants:
    call_ANTS('all')
  elif args.ants_stage: 
    call_ANTS(args.ants_stage)
  elif args.f:
    call_final_stats()
  elif args.landmark:
    landmark()
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
  elif args.rcl:
    image_type = 'face'
    run_all('rcl')
  elif args.tracc:
    call_tracc()
  elif args.l:
    call_longitudinal()
      
  else:               # execute all stages when no particular stage is specified
    run_all('all')
     
