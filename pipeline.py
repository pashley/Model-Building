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
import textwrap
"""  
Model-building pipeline

This pipeline takes in a set of images and processes them both linearly and 
nonlinearly to produce an average population model of either the brain or craniofacial structure.
.....

To run the pipeline (pipeline.py),
A) the following scripts must be present in the same directory containing pipeline.py:
     - process.py
     - utils.py
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
   
   
Specialized Options

Landmark-based facial feature analysis
     - the model (minc) image and the landmarks (.tag file) named ?? and ?? , respectively


Longitudinal analysis (for time-1 and time-2 images)
     - all images in 'inputs' directory, 
     - filenames of time-2 images end in "_2.mnc"
        Ex. time-1 image = H001.mnc
            time-2 image = H001_2.mnc

Asymmetrical analysis
     -

***********CAUTION 
- All dependency names terminate with the * (asterisk) wildcard, and may in turn flag any 
  files and/or folders in the directory that pipeline.py is being executed.
  
  This error may occur:
  
  "Unable to run job: Script length does not match declared length.
  Exiting."
  
  To avoid errors, remove or rename any files and/or folders with names that could be flagged 
  by the following dependency names:
     - avgsize*
     - blurmod*
     - linavg*
     - ldmk_model*
     - nlin*
     - reg*
     - s1*
     - s2*
     - s3*
     - s6*
     - tr*    
    
 - "davinci" -problems with sienax (fsl)
****************            
"""


def submit_jobs(jobname, depends, job_list):
  # Submits a list of jobs to the batch system specified by the user. 
  
  # proceed to submitting if there is at least one job in the list 
  if len(job_list) >= 1:     
    
    if batch_system == 'sge':
      for command in job_list:
        # Add the input's name to the name of input-specific jobs 
        if len(job_list) != 1:                      
          command_split = command.split()
          inputname = command_split[2]    # the input's name is the 2nd argument in the command
          thejobname = jobname + "_" + inputname[0:4]
        else:
          thejobname = jobname
          
        # Echo the job details or submit the job
        if echo:
          print 'sge_batch -J %s -H "%s" %s' %(thejobname, depends, command)
        else:
          execute('sge_batch -J %s -H "%s" -o logfiles/ -e logfiles/ %s' %(thejobname, depends, command))
    
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
      
      # Echo the job details or submit the job
      if echo:
        print './MAGeTbrain/bin/qbatch -N %s --afterok_pattern %s %s %s %s' %(jobname, depends, basename(cmdfileinfo[1]), batchsize, time)
      else:
        execute('./MAGeTbrain/bin/qbatch -N %s --afterok_pattern %s %s %s %s' %(jobname, depends, basename(cmdfileinfo[1]), batchsize, time))
      os.remove(cmdfile.name)
    
    elif batch_system == 'local':  # run locally
      for command in job_list:
        if echo:
          print command
        else:
          execute(command)
  return


def call_preprocess():
  # Calls the preprocess stage for every input and submits the jobs
  create_dirs('preprocess')
 
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      job_list.append('./process.py preprocess %s %s %s' %(inputname, image_type, target_type))
  submit_jobs('s1_a', "something*", job_list) # TODO: fix dependency?
  if target_type == 'random' or image_type == 'face':
    call_preprocess2()
  return 


def call_preprocess2():
  # Calls the Part 2 of the preprocessing stage 
  # Executed for craniofacial structure image processing or when the target image is a randomly selected subject
  
  # randomly select a subject to be the target image
  target = random.randint(0,count-1) 
  targetname = listofinputs[target]
  targetname = 'H146_CAMH'
  
  if len(glob.glob('*/NORM/*_crop.mnc')) == 0:
    job_list = ['./process.py autocrop %s %s' %(image_type,targetname)]
    submit_jobs('s1_b', 's1_a_*', job_list)
  
  job_list = []
  for sourcename in listofinputs:
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename)):
      job_list.append('./process.py preprocess2 %s %s %s' %(sourcename, targetname, image_type))
  submit_jobs('s1_c', 's1_b*', job_list)
  return

 
def nonpairwise():
  # Sets up the non-pairwise 12-parameter registration stage.
  # This is the alternative to pairwise 12-parameter registrations (i.e when there are too many inputs)
  
  create_dirs('lsq12n')
  # randomly select a subject to be the target image
  target = random.randint(0,count-1) 
  targetname = listofinputs[target]
  
  # PART 1: calls lsq12_reg 
  if not os.path.exists('avgsize.mnc'):  
    job_list = []
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
    if not os.path.exists('%s/nlin_timages/%s_nlin%s.mnc' %(inputname,inputname, number)):
      job_list.append('./process.py ants_and_resample %s %s/%s/%s_%s.mnc %s %s %s' 
                      %(inputname, inputname, sourcefolder, inputname, inputregname, targetimage, number, iterations))
  submit_jobs('reg%s' %number, '%s*' %targetimage[0:-4], job_list)
 
 # PART 2: calls mnc_avg
  job_list = ['./process.py mnc_avg nlin_timages nlin%s nlin%savg.mnc' %(number, number)]
  if not os.path.exists('avgimages/nlin%savg.mnc' % number):
    submit_jobs('nlin%savg' %number, 'reg%s_*' %number, job_list)
  return
 
  
def call_ANTS(iteration):
  # Calls each iteration of mincANTS with the appropriate parameters
  create_dirs('ANTS')
  if iteration == '1' or iteration == 'all':
    ANTS_and_avg('1', 'output_lsq12', 'lsq12', 'linavg.mnc', '100x1x1x1')
  if iteration == '2' or iteration == 'all':
    ANTS_and_avg('2', 'nlin_timages', 'nlin1', 'nlin1avg.mnc', '100x20x1')
  if iteration == '3' or iteration == 'all':
    ANTS_and_avg('3', 'nlin_timages', 'nlin2', 'nlin2avg.mnc', '100x5')
  if iteration == '4' or iteration == 'all':
    ANTS_and_avg('4', 'nlin_timages', 'nlin3', 'nlin3avg.mnc', '5x20')
  return


def tracc_resmp(stage, fwhm, iterations, step, model):
  # Sets up the nonlinear processing stage which uses minctracc

  # PART 1: calls model_blur
  job_list =['./process.py model_blur %s %s' %(fwhm, model)]
  if not os.path.exists('avgimages/nlin%savg_tracc.mnc' %stage):
    if stage == 1:
      dependency = model[0:-4]
    else:
      dependency = model[0:8]
    submit_jobs('blurmod%s' %stage, "%s*" %dependency, job_list)
    
    # PART 2: calls tracc
    job_list = []
    for inputname in listofinputs:
      job_list.append('./process.py tracc %s %s %s %s %s %s' %(inputname, stage, fwhm, iterations, step, model))
    submit_jobs('tr%s' %stage, 'blurmod%s*' %stage, job_list)
    
    # PART 3: calls mnc_avg
    job_list = ['./process.py mnc_avg minctracc_out nlin%s nlin%savg_tracc.mnc' %(stage, stage)]
    submit_jobs('nlin%savg' %stage, 'tr%s_*' %stage, job_list)    
  return


def call_tracc(iteration):
  # Calls each iteration of mintracc with the appropriate parameters
  create_dirs('tracc')   
  #tracc_resmp(stage, Gaussian blur, iterations, step size, model name) 
  if iteration == '1' or iteration == 'all':
    tracc_resmp(1, 16, 30, 8, 'linavg.mnc')
  if iteration == '2' or iteration == 'all':
    tracc_resmp(2, 8, 30, 8, 'nlin1avg_tracc.mnc')
  if iteration == '3' or iteration == 'all':  
    tracc_resmp(3, 8, 30, 4, 'nlin2avg_tracc.mnc') 
  if iteration == '4' or iteration == 'all':
    tracc_resmp(4, 4, 30, 4, 'nlin3avg_tracc.mnc')
  if iteration == '5' or iteration == 'all':
    tracc_resmp(5, 4, 10, 2, 'nlin4avg_tracc.mnc')
  if iteration == '6' or iteration == 'all':
    tracc_resmp(6, 2, 10, 2, 'nlin5avg_tracc.mnc')  
  return


def call_final_stats():
  # Calls the deformation fields stage
  create_dirs('final_stats')
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/final_stats/%s_det_blur.mnc' %(inputname, inputname)):
      job_list.append( './process.py deformation %s' %inputname)
  if batch_system == 'pbs':           #TODO: fix depends name
    submit_jobs('s6', 'nlin*_*', job_list)
  else:
    submit_jobs('s6', 'nlin*', job_list)
  return



def call_longitudinal():
  # Calls the longitudinal analysis option between time-1 and time-2 images of every subject
  
  # run entire pipeline on time-1 images 
  run_all()
   
  # longitudinal analysis  
  job_list = []
  for inputname_time2 in listofinputs_time2:
    create_dirs('longitudinal')
    if not os.path.exists('%s/longitudinal/det_fwhm8_blur.mnc' %inputname_time2[0:-2]):
      job_list.append('./process.py longitudinal %s' %inputname_time2)
  submit_jobs('lg', 's6_*', job_list)
  return


def landmark():
  # Calls the landmark facial feature analysis option
  job_list = ['./process.py tag_nlinavg']
  if not os.path.exists('nlin_model_face_tags.csv'):
    submit_jobs('ldmk_model','s6_*', job_list)
    
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/%s_size_shape_diff_landmarks.csv' %(inputname, inputname)):
      job_list.append('./process.py tag_subject %s' %inputname)
  submit_jobs('ldmk', 'ldmk_model*', job_list)    
  return

def call_asymm():
  # Calls the asymmetrical analysis option
  create_dirs('asymmetrical')
  
  
  job_list = []
  for inputname in listofinputs:
    if not os.path.exists('%s/asymmetrical/%s_det_blur.mnc' %(inputname, inputname)):
      job_list.append('./process.py asymmetric_analysis %s' %inputname)
  submit_jobs('asymm','s3_*' ,job_list)    
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
    dirs.append('nlin_tfiles')
    dirs.append('nlin_timages')
  
  elif stage == 'tracc':
    dirs.append('minctracc_out')
  
  elif stage == 'final_stats':
    dirs.append('final_stats')
  
  elif stage == 'longitudinal':
    dirs.append('longitudinal')
    dirs.append('longitudinal/NUC_2')
    dirs.append('longitudinal/output_lsq6')
    dirs.append('longitudinal/nlin_tfiles')
  
  elif stage == 'asymmetrical':
    dirs.append('asymmetrical')

  for directory in dirs:
    for inputname in listofinputs:
      if not os.path.exists(inputname + '/%s' %directory):
        mkdirp(inputname + '/%s' %directory)
  return


def run_all():
  # Runs the entire pipeline with specific options (whenever specified).
 
  call_preprocess()
  
  # select method for 12-parameter registrations
  if not os.path.exists('avgimages/linavg.mnc'):
    if lsq12 == 'pairwise':
      pairwise()
    elif lsq12 == 'nonpairwise':
      nonpairwise()
    elif lsq12 == 'number_dependent':  # method dependent on the number of inputs
      if count <= 300:
        pairwise()
      elif count > 300:
        nonpairwise()
  
  # select method for nonlinear processing
  if nlin == 'tracc':
    call_tracc('all')
  elif nlin == 'ants':
    call_ANTS('all')
    
  call_final_stats()
  
  if landmarks == 'True':
    landmark()

  return


if __name__ == '__main__':
  parser = argparse.ArgumentParser(usage="./pipeline.py batch_system [options]", 
                                   formatter_class=argparse.RawDescriptionHelpFormatter,
                                   description=textwrap.dedent('''\
        
        For basic operation  
        -----------------------------------
          Within the current directory, have  
             1) pipeline.py, process.py, utils.py, xfmjoin.
             2) all input images in 'inputs' directory.
             3) targetimage.mnc & targetmask.mnc files (for linear 6-parameter 
                registrations). Or use the '-random_target' option.
        
          Default stages: preprocess, lsq12, ants, stats  (brain imaging)
 
        
        For specialized options 
        -----------------------------------
          Landmark-based facial feature analysis
            - Within current directory, have 
                1) sys_881_face_model.mnc (model image)
                2) face_tags_sys881_June21_2012.tag (model tags)
        
          Longitudinal analysis
            - all time-2 input images in 'inputs' directory must end in "_2"
              Ex. time-1 image = H001.mnc
                  time-2 image = H001_2.mnc
        
          Asymmetrical analysis
            - 
         _______________________________________________________________________  
         '''))                              
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
                        help="randomly select one input to be the target image\
                        for the linear 6-parameter processing [default: Assumes that targetimage.mnc & targetmask.mnc files are in current directory]")
  group.add_argument("-run_with", action="store_true", 
                       help="run the entire pipeline with any single stage options that are specified on the command line")
  group.add_argument("-echo",action="store_true", 
                     help="prints the job submissions")
  
  # Running individual stages of the pipeline
  group = parser.add_argument_group('Options for running indiviudal stages of pipeline')
  
  group.add_argument("-preprocess", action="store_true", 
                      help="preprocessing")
  group.add_argument("-lsq12",action="store_true",
                      help="12-parameter registrations (pairwise if inputs <= 300, otherwise non-pairwise) [default]")
  group.add_argument("-lsq12p", action="store_true",
                       help="pairwise 12-parameter registrations")
  group.add_argument("-lsq12n", action="store_true",
                      help="non-pairwise 12-parameter registrations")
  group.add_argument("-tracc",action="store_true",
                      help="nonlinear processing using minctracc (6 iterations)[default: mincANTS]")
  group.add_argument("-tracc_stage", choices=['1','2','3','4','5','6'], 
                      help="run a single iteration of minctracc")
  group.add_argument("-ants", action="store_true", 
                      help="nonlinear processing using mincANTS (4 iterations)")
  group.add_argument("-ants_stage", choices=['1','2','3','4'], 
                      help="run a single iteration of mincANTS")
  group.add_argument("-stats", action="store_true",
                      help="final stats: deformation fields, determinant")
  group.add_argument("-landmark", action="store_true",
                      help="landmark-based facial feature analysis")  
    
  # Other pipeline options
  group = parser.add_argument_group('Additional pipeline options')
  group.add_argument("-longitudinal", action="store_true",
                      help="longitudinal analysis (Processes time-1 images with all default stages first. Use \
                      -run_with option for non-default stages.)")
  group.add_argument("-asymm", action="store_true", 
                      help="asymmetric analysis (lsq12 stage must be on the queue, running or complete)")
    
  
  args = parser.parse_args()
  batch_system = args.batch_system
  prefix_list = args.prefix
   
  
  if args.face:
    image_type = 'face'
  else:
    image_type = 'brain'  # default
  
  if args.random_target:
    target_type = 'random'
  else:
    target_type = 'given' # default
  
  if args.tracc:
    nlin = 'tracc'
  else:
    nlin = 'ants'         # default
  
  if args.lsq12n:
    lsq12 = 'nonpairwise'
  elif args.lsq12p:
    lsq12 = 'pairwise'
  else:
    lsq12 = 'number_dependent'  # default
  
  if args.landmark:
    landmarks = 'True'
  else:
    landmarks = 'False'   # default
  
  if args.echo:
    echo = True
  else:
    echo = False

  # Generate the list of inputs for processing 
  listofinputs = []
  if prefix_list == None:       # when no prefix is specified, process all inputs
    for subject in glob.glob('inputs/*'):
      thefile = basename(subject)
      listofinputs.append(thefile[0:-4])    # always a minc file??
  else:
    for prefix in prefix_list:
      inputdir = 'inputs/*%s*' % prefix
      for subject in glob.glob(inputdir):
        thefile = basename(subject)
        listofinputs.append(thefile[0:-4])

  # For longitudinal analysis, 
  listofinputs_time2 = []  
  if args.longitudinal:
    for subject in listofinputs:
      # distinguish between the time-1 and time-2 images
      # expected that time-2 image filenames have the additional "_2" suffix
      if subject[-2:] == '_2':      
        listofinputs_time2.append(subject)  # new list with time-2 inputnames

    for subject in listofinputs_time2:       
      listofinputs.remove(subject)         # original list now has only time-1 inputnames 
    inputfile2 = open('inputlist_time2.xfm', 'w')
    inputfile2.write("\n".join(listofinputs_time2))
    inputfile2.close()    
      
  if len(listofinputs_time2) == 0:    # when the longitudinal analysis is not being executed
    inputfile = open('inputlist.xfm', 'w')    
  else:
    inputfile = open('inputlist_time1.xfm', 'w')    
  inputfile.write("\n".join(listofinputs))
  inputfile.close()
  

  if args.check_inputs:
    sys.exit(1)
  

  count = len(listofinputs)  # number of inputs to process
  
  for inputname in listofinputs:
    if not os.path.exists(inputname + '/'):
      mkdirp(inputname)  
  if not os.path.exists('avgimages'):
    mkdirp('avgimages')   
  if not os.path.exists('logfiles'):
    mkdirp('logfiles')
 
  # Run the entire pipeline with specific options 
  if args.run_with and not args.longitudinal:          
    run_all()
  elif args.run_with and args.longitudinal:
    call_longitudinal()

  # Run single stages   
  elif args.preprocess:    
    call_preprocess()            # preprocessing stage
  elif args.lsq12:               # 12-parameter registrations (method based on the number of inputs)
    if count > 300:            
      nonpairwise()
    elif count <= 300:
      pairwise()    
  elif args.lsq12p:              # pairwise 12-parameter registrations 
    pairwise()
  elif args.lsq12n:
    nonpairwise()                # non-pairwise 12-parameter registrations
  elif args.ants:                # mincANTS (all 4 stages) 
    call_ANTS('all')
  elif args.ants_stage:          # mincANTS (single stage)
    call_ANTS(args.ants_stage)
  elif args.tracc:               # mintracc
    call_tracc('all')  
  elif args.tracc_stage:         # minctracc (single stage)
      call_tracc(args.tracc_stage)
  elif args.stats:               # final stats 
    call_final_stats()
    
  # Run additional analysis options
  elif args.landmark:         
    landmark()
  elif args.longitudinal:
    call_longitudinal() 
  elif args.asymm:
    call_asymm()
    
  # Run the entire pipeline (with default stages) when no options are specified 
  else:               
    run_all()
     
