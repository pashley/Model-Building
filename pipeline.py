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
Model-building pipeline

This pipeline takes in a set of images and processes them both linearly and 
nonlinearly to produce an average population model of either the brain or cranifacial structure.
.....

To run the pipeline (pipeline.py),
A) the following scripts must be present in the same directory containing pipeline.py:
     - process.py
     - utils.py
     - utils.pyc  ??
     - xfmjoin 
     - MAGetbrain ? for qbatch  
    
B) the following modules must be loaded
     - python
     - FSL
     - minc toolbox 
     - octave

C) all subjects (minc images) one wishes to process must be in a directory called 
   'inputs' located within the directory containing pipeline.py 
   
D) the target image and target mask (for the linear 6-parameter registration) 
   must located in the directory containing pipeline.py and be named 
   targetimage.mnc and targetmask.mnc, respectively. 
   
   If either file is missing, errors will occur. Alternatively, the 
   "-random_target" command line option will randomly select a subject to be the 
   target. When using this option, ensure targetimage.mnc and targetmask.mnc do
   not exist within the directory (or else silent errors will ensue).   
"""


def submit_jobs(jobname, depends, job_list):
  # Submits a list of jobs to the batch system specified by the user 
  
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
        print thejobname  + " " + command    
        #execute('sge_batch -J %s -H "%s" %s' %(thejobname, depends, command))
    
    elif batch_system == 'pbs':
      # create a temporary file with the list of jobs to submit to qbatch
      cmdfileinfo = tempfile.mkstemp(dir='./') 
      cmdfile = open(cmdfileinfo[1], 'w')
      cmdfile.write("\n".join(job_list))
      cmdfile.close()
       
      if depends[-2] != '_':            # sometimes dependency names without the underscore aren't recognized on scinet
        depends = depends[0:-1] + "_*"  # so, add the underscore to dependency names that don't have one 
      batchsize = 8
      if len(job_list) == 1:
        time = "1:00:00"  # default walltime for 1 batch of 1 tasks
      else:
        time = "2:00:00"  # default walltime for 1 batch of 8 tasks
      execute('./MAGeTbrain/bin/qbatch -N %s --afterok_pattern %s %s %s %s ' %(jobname, depends, basename(cmdfileinfo[1]), batchsize, time))
      os.remove(cmdfile.name)
    
    elif batch_system == 'local':  # run locally
      for command in job_list:
        execute(command)
  return


def call_preprocess():
  # Calls the preprocess stage for every input and submits the jobs
  create_dirs('preprocess')
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
  submit_jobs('s1_a', "something*", job_list) # fix dependency?
  if target_type == 'random' or image_type == 'face':
    call_preprocess2()
  return 


def call_preprocess2():
  # Calls the Part 2 of the preprocessing stage 
  # Executed for craniofacial structure image processing or when the target image is a randomly selected subject
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
  # Sets up the non-pairwise 12-parameter registration stage.
  # This is the alternative to pairwise 12-parameter registrations (when there are too many inputs,for instance)
  
  create_dirs('lsq12n')
  # PART 1: calls lsq12_reg 
  job_list = []
  print "targetname == %s" %targetname
  for sourcename in listofinputs:     
    if sourcename != targetname: 
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py lsq12_reg %s %s lin_tfiles' %(sourcename, targetname))
  submit_jobs('s2', 's1*', job_list)
        
  # PART 2: calls xfmavg_inv_resample
  job_list = ['./process.py xfmavg_inv_resample %s' %targetname]
  if not os.path.exists('avgsize.mnc'):
    submit_jobs('avgsize','s2_*', job_list) 
   
  # PART 3: calls lsq12reg_and_resample
  job_list = []
  for sourcename in listofinputs:    
    if not os.path.exists('%s/output_lsq12/%s_lsq12.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py lsq12reg_and_resample %s' %sourcename)
  submit_jobs('s3', 'avgsize*', job_list)
  
  # PART 4: calls linavg_and_check
  call_linavg()
  return  
    
 
def pairwise():
  # Sets up the pairwise 12-parameter registration stage
  
  create_dirs('lsq12p')
  # PART 1: calls lsq12_reg
  job_list = []
  for sourcename in listofinputs:
    for targetname in listofinputs:
      if sourcename != targetname and not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        job_list.append('./process.py lsq12_reg %s %s pairwise_tfiles' %(sourcename, targetname))      
  submit_jobs('s2', 's1*', job_list)
          
  # PART 2: calls xfmavg_and_resample
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/output_lsq12/%s_lsq12.mnc' %(inputname,inputname)):
      job_list.append('./process.py xfmavg_and_resample %s' %inputname)
  submit_jobs('s3', 's2_*', job_list)
  
  # PART 3: calls linavg_and_check  
  call_linavg()
  return


def call_linavg():
  # Average linearly processed images & check for completion of the lsq12 stage 
  job_list = ['./process.py linavg_and_check output_lsq12 lsq12 linavg.mnc']
  if not os.path.exists('avgimages/linavg.mnc'):
    submit_jobs('linavg', 's3_*', job_list)
  return

  
def ANTS_and_avg(number, sourcefolder,inputregname, targetimage, iterations):
  # Sets up the nonlinear processing stage which uses mincANTS
  # PART 1: calls ants
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/nonlin_timages/%s_nonlin%s.mnc' %(inputname,inputname, number)):
      job_list.append('./process.py ants_and_resample %s %s/%s/%s_%s.mnc %s %s %s' 
                      %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations))
  submit_jobs('reg%s' %number, '%s*' %targetimage[0:-4], job_list)
 
 # PART 2: calls mnc_avg
  job_list = ['./process.py mnc_avg nonlin_timages nonlin%s nonlin%savg.mnc' %(number, number)]
  if not os.path.exists('avgimages/nonlin%savg.mnc' % number):
    submit_jobs('nonlin%savg' %number, 'reg%s_*' %number, job_list)
  return
 
  
def call_ANTS(iteration):
  # Calls each iteration of mincANTS with the appropriate parameters
  create_dirs('ANTS')
  if iteration == '1' or iteration == 'all':
    ANTS_and_avg('1', 'output_lsq12', 'lsq12', 'linavg.mnc', '100x1x1x1')
  if iteration == '2' or iteration == 'all':
    ANTS_and_avg('2', 'nonlin_timages', 'nonlin1', 'nonlin1avg.mnc', '100x20x1')
  if iteration == '3' or iteration == 'all':
    ANTS_and_avg('3', 'nonlin_timages', 'nonlin2', 'nonlin2avg.mnc', '100x5')
  if iteration == '4' or iteration == 'all':
    ANTS_and_avg('4', 'nonlin_timages', 'nonlin3', 'nonlin3avg.mnc', '5x20')
  return


def tracc_resmp(stage, fwhm, iterations, step, model):
  # Sets up the nonlinear processing stage which uses minctracc

  # PART 1: calls model_blur
  #job_list = ['mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4])]
  job_list =['./process.py model_blur %s %s' %(fwhm, model)]
  if not os.path.exists('avgimages/nonlin%savg.mnc' %stage):
    submit_jobs('blurmod%s' %stage, "%s*" %model[0:-4], job_list)
    
    # PART 2: calls tracc
    job_list = []
    for inputname in listofinputs:
      job_list.append('./process.py tracc %s %s %s %s %s %s' %(inputname, stage, fwhm, iterations, step, model))
    submit_jobs('tr%s' %stage, 'blurmod%s*' %stage, job_list)
    
    # PART 3: calls mnc_avg
    job_list = ['./process.py mnc_avg minctracc_out nlin%s nonlin%savg.mnc' %(stage, stage)]
    submit_jobs('nonlin%savg' %stage, 'tr%s_*' %stage, job_list)    
  return


def call_tracc():
  # Calls each iteration of mintracc with the appropriate parameters
  create_dirs('tracc')   
  #tracc_resmp(stage, Gaussian blur, iterations, step size, model name) 
  tracc_resmp(1, 16, 30, 8, 'linavg.mnc')
  tracc_resmp(2, 8, 30, 8, 'nonlin1avg.mnc')
  tracc_resmp(3, 8, 30, 4, 'nonlin2avg.mnc') 
  tracc_resmp(4, 4, 30, 4, 'nonlin3avg.mnc')
  tracc_resmp(5, 4, 10, 2, 'nonlin4avg.mnc')
  tracc_resmp(6, 2, 10, 2, 'nonlin5avg.mnc')  
  return


def call_final_stats():
  # Calls the deformation fields stage
  create_dirs('final_stats')
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
  # Run the entire pipeline with the option selected.
  # rp = pairwise lsq12 
  # rpt = pairwise lsq12 & minctracc
  # rn = non-pairwise lsq12 (& mincANTS)
  # rnt = non-pairwise lsq12 & minctracc
  # rcl = landmarked-based facial feature analysis (default: mincANTS)
  
  call_preprocess()
  if option == 'rp' or option == 'rpt':
    pairwise()
  elif option == 'rn' or option == 'rnt':
    nonpairwise()
  else:   # when no option is specified the method of lsq12 registrations is dependent on the number of inputs
    if count <= 300:
      pairwise()
    elif count > 300:
      nonpairwise()
  if option == 'rpt' or option == 'rnt' or option == 'rt':
    call_tracc()
  else:
    call_ANTS('all')  # default nonlinear 
  call_final_stats()
  #if option == 'rcl':
    #print "landmark"
    #landmark()
  return


def call_longitudinal():
  # Calls the longitudinal analysis option between time-1 and time-2 image
  
  # run entire pipeline on time-1 images 
  run_all('all')
   
  # time-2 inputs must end in "_2", all this is based on that
  # nu_correct time_2 images  
  job_list = []
  for inputname in listofinputs_time2:
    if not os.path.exists(inputname[0:-2] + '/longitudinal'):
      mkdirp(inputname[0:-2] + '/longitudinal')        # create directory
    if not os.path.exists('%s/longitudinal/%s_nuc.mnc' %(inputname[0:-2], inputname)):
      job_list.append('./longitudinal.py preprocess_time2 %s' %inputname)
  submit_jobs('nuc_t2','s6_*',job_list) #TODO: fix dependency name
  
  # longitudinal analysis 
  job_list = []
  for inputname in listofinputs_time2:
    if not os.path.exists('%s/longitudinal/det3_blur.mnc'):
      job_list.append('./longitudinal.py longitudinal %s' %inputname)
  submit_jobs('lng', 'nuc_t2*', job_list)
  return


def landmark():
  # Calls the landmark facial feature analysis option
  job_list = ['./process.py tag_nlinavg']
  if not os.path.exists('model_to_nlinavg.xfm'):
    submit_jobs('ldmk_model','s6_*', job_list)
    
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/%s_landmarks.tag' %(inputname, inputname)):
      job_list.append('./process.py tag_subject %s' %inputname)
  submit_jobs('lndmk', 'lndmk_model*', job_list)    
  return

def call_asymm():
  # Calls the asymmetrical analysis option
  
  # create directory structure
  for inputname in listofinputs:
    if not os.path.exists(inputname):
      mkdirp(inputname)
      mkdirp(inputname + '/NUC')
      mkdirp(inputname + '/lin_tfiles')
      mkdirp(inputname + '/output_lsq9')
      mkdirp(inputname + '/output_lsq6')
      mkdirp(inputname + '/nlin_tfiles')
      mkdirp(inputname + '/stats')
  
  # run the analysis
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/stats/%s_det_in_model_space.mnc' %(inputname, inputname)):
      job_list.append('./asymm.py asymmetric_analysis %s' %inputname)
  submit_jobs('asymm','something',job_list)    
  return


def create_dirs(stage):
  dirs = []
  if stage == 'preprocess':
    dirs.append('NUC')
    dirs.append('NORM')
    dirs.append('masks')
    dirs.append('lin_tfiles')
    dirs.append('output_lsq6')   
  elif stage == 'lsq12p':
    dirs.append('pairwise_tfiles')
    dirs.append('output_lsq12')
  elif stage == 'lsq12n':
    dirs.append('output_lsq12')
  elif stage == 'ANTS':
    dirs.append('nonlin_tfiles')
    dirs.append('nonlin_timages')
  elif stage == 'tracc':
    dirs.append('minctracc_out')
  elif stage == 'final_stats':
    dirs.append('final_stats')

  for directory in dirs:
    for inputname in listofinputs:
      if not os.path.exists(inputname + '/%s' %directory):
        mkdirp(inputname + '/%s' %directory)
  return

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  # Configuration options
  group = parser.add_argument_group('Configuration options')
  group.add_argument("batch_system", choices=['sge', 'pbs', 'local'],
                        help="batch system to process jobs")  
  group.add_argument("-face", action="store_true",
                      help="craniofacial structure imaging [default: brain imaging]")
  group.add_argument("-prefix", action="append",    # can specify more than one prefix
                      help= "specify subset(s) of inputs within the inputs directory to process")
  group.add_argument("-check_inputs", action="store_true",
                      help="generate a file with the list of inputs to be processed")
  group.add_argument("-random_target", action="store_true",
                        help="randomly select one input to be target image\
                        for linear processing")  
  
  # Running individual stages of the pipeline
  group = parser.add_argument_group('Options for running indiviudal stages of pipeline')
  
  group.add_argument("-p", action="store_true", 
                      help="preprocessing")
  group.add_argument("-lsq12",action="store_true",
                      help="lsq12 registrations (method based on number of inputs) [default]")
  group.add_argument("-lsq12p", action="store_true",
                       help="pairwise lsq12 registrations")
  group.add_argument("-lsq12n", action="store_true",
                      help="non-pairwise lsq12 registrations")
  #group.add_argument("-linavg",action="store_true", 
                      #help="average linearly processed images")
  group.add_argument("-tracc",action="store_true",
                      help="minctracc nonlinear transformations (6 iterations with preset parameters)")
  group.add_argument("-ants", action="store_true", 
                      help="4 nonlinear registrations: (mincANTS, resample, average)x4 [default]")
  group.add_argument("-ants_stage", choices=['1','2','3','4'], 
                      help="run a single iteration of mincANTS")
  group.add_argument("-f", action="store_true",
                      help="final stats: deformation fields, determinant")
  
  # Other pipeline options
  group = parser.add_argument_group('Other pipeline options')
  group.add_argument("-longitudinal", action="store_true",
                      help="longitudinal analysis (for time-1 and time-2 images)")
  group.add_argument("-landmark", action="store_true",
                      help="landmark-based facial feature analysis")
  group.add_argument("-asymm", action="store_true", 
                      help="asymmetric analysis")
  group.add_argument("-run_with", action="store_true", 
                     help="run the entire pipeline with the specified option(s). Possible options:\
                     {-lsq12p or -lsq12n} and/or  {-ants or -tracc}")
  
  
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
  #inputfile = open('inputlist.xfm', 'w')    
  #inputfile.write("\n".join(listofinputs))
  #inputfile.close

  listofinputs_time2 = []
  if args.longitudinal:
    for subject in listofinputs:
      # distinguish between the time-1 and time-2 images
      # expected that time-2 image filenames have the additional "_2" suffix
      # Ex. time-1 image: H001.mnc
      #     time-2 image: H001_2.mnc
      if subject[-2:] == '_2':      
        listofinputs_time2.append(subject)
  
    for subject in listofinputs_time2:
      listofinputs.remove(subject)   
    inputfile2 = open('inputlist_time2.xfm', 'w')
    inputfile2.write("\n".join(listofinputs_time2))
    inputfile2.close()    
      
  if len(listofinputs_time2) == 0:
    inputfile = open('inputlist.xfm', 'w')    
  else:
    inputfile = open('inputlist_time1.xfm', 'w')    
  inputfile.write("\n".join(listofinputs))
  inputfile.close()
  

  if args.check_inputs:
    sys.exit(1)
  
  if args.asymm:
    call_asymm()
    sys.exit(1)

  count = len(listofinputs)  # number of inputs to process
  
  if not os.path.exists('avgimages'):
    mkdirp('avgimages')   
    
  target = random.randint(0,count-1) 
  targetname = listofinputs[target]

  if args.run_with: 
    if args.lsq12p and not args.tracc:                      # pairwise & ANTS
      run_all('rp')
    elif args.lsq12p and not args.tracc and args.ants:      # pairwise & ANTS 
      run_all('rp')
    elif args.lsq12n and not args.tracc:                    # nonpairwise & ANTS
      run_all('rn')
    elif args.lsq12n and not args.tracc and args.ants:      # nonpairwise & ANTS
      run_all('rn')
    elif args.lsq12p and args.tracc:                        # pairwise & tracc
      run_all('rpt')
    elif args.lsq12n and args.tracc:                        # nonpairwise & tracc 
      run_all('rnt')
    elif args.tracc:                                        # tracc
      run_all('rt')  
  elif args.p:
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
  #elif args.linavg:
    #call_linavg()
  elif args.ants:
    call_ANTS('all')
  elif args.ants_stage: 
    call_ANTS(args.ants_stage)
  elif args.f:
    call_final_stats()
  elif args.landmark:   # landmark-based facial feature analysis
    landmark()
  #elif args.rcl:
    #image_type = 'face'
    #run_all('rcl')
  elif args.tracc:
    call_tracc()
  elif args.longitudinal:
    call_longitudinal()      
  else:               # execute all stages when no particular stage is specified
    run_all('all')
     
