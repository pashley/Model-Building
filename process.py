#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import re
import tempfile
import shutil


""" Rough draft of description:
- Functions are organized according to the necessary dependencies between stages of the pipeline

Stage 1: Preprocess 
Stage 2: Pairwise or non-pairwise 12-parameter registration 
Stage 3: Nonlinear registrations using mincANTS or minctracc
Stage 4: Deformation fields
"""

def mask(inputname, inputfolder):
  """ Generates brain mask using sienax"""
  execute("mnc2nii %s/%s/%s.mnc %s/%s.nii" %(inputname,inputfolder, inputname, inputname, inputname))
  tmpdir = tempfile.mkdtemp(dir = '%s/' %inputname)
  execute("sienax %s/%s.nii -d -o %s" %(inputname, inputname, tmpdir)) 
  execute("gzip -d %s/I_stdmaskbrain_seg.nii.gz" %(tmpdir))
  execute("nii2mnc %s/I_stdmaskbrain_seg.nii %s/I_stdmaskbrain_seg.mnc" %(tmpdir, tmpdir))
  execute('minccalc -clob -expression "A[0] > 0.5" %s/I_stdmaskbrain_seg.mnc %s/masks/I_stdmaskbrain_seg_discrete.mnc' %(tmpdir,inputname))
  shutil.rmtree(tmpdir)
  execute('mincresample -clob %s/masks/I_stdmaskbrain_seg_discrete.mnc %s/masks/mask.mnc -like %s/%s/%s.mnc' %(inputname, inputname, inputname, inputfolder,inputname))  
  return
  

def preprocess(inputfolder, image_type, target_type):
  """ Preprocessing Stage    
                                      Brain
   PART 1                                    PART 2 (if target image is provided)
   1) Intensity inhomogeneity correction     4) linear 6-parameter registration 
   2) Normalization                          5) resample
   3) Masking (with sienax)
   
                             Craniofacial Structure 
   1) Intensity inhomogeneity correction
   2) Brain extraction
   3) Normalization 
   """  
  execute('nu_correct -clob inputs/%s.mnc %s/NUC/%s.mnc' %(inputfolder, inputfolder, inputfolder)) 
  if image_type == 'brain':
    themax = execute('mincstats -max -quiet %s/NUC/%s.mnc' %(inputfolder, inputfolder))   	
    themin = execute('mincstats -min -quiet %s/NUC/%s.mnc' %(inputfolder, inputfolder)) 
    # both themax & themin contain the newline character at the end of the string (ex. themax = '7054.400964\n', themin = '0\n')
    # themax[0:-1] is the string of the numerical value without the newline character 
    execute('minccalc -clob %s/NUC/%s.mnc -expression "10000*(A[0]-0)/(%s-%s)" %s/NORM/%s.mnc' %(inputfolder, inputfolder, themax[0:-1], themin[0:-1], inputfolder, inputfolder)) 
    mask(inputfolder, 'NORM') # use normalized image to generate the mask
    if target_type == 'given': # if target image is provided by the user 
      execute('bestlinreg -clob -lsq6 -source_mask %s/masks/mask.mnc -target_mask targetmask.mnc %s/NORM/%s.mnc targetimage.mnc %s/lin_tfiles/%s_lsq6.xfm' %(inputfolder, inputfolder, inputfolder, inputfolder, inputfolder))  
      resample('%s/lin_tfiles/%s_lsq6.xfm' %(inputfolder, inputfolder), '%s/NORM/%s.mnc' %(inputfolder, inputfolder), '%s/output_lsq6/%s_lsq6.mnc' %(inputfolder, inputfolder))
  
  elif image_type == 'face':  
    mask(inputfolder,'NUC') # use the nu_corrected image to generate the mask
    vartype = execute('mincinfo -vartype image %s/NUC/%s.mnc' %(inputfolder,inputfolder))
    # by default minccalc takes the vartype of the first file on the command line & the mask generated by sienax is 'long' by default
    # don't want 'long' before 'short' ??? 
    # TODO: check this! 
    if vartype == 'short\n':
      execute('minccalc -clob -expression "(1-A[1])*A[0]" %s/NUC/%s.mnc %s/masks/mask.mnc %s/NUC/%s_face.mnc' %(inputfolder, inputfolder, inputfolder, inputfolder, inputfolder))
    elif vartype == 'long\n':
      execute('minccalc -clob -expression "(1-A[0])*A[1]" %s/masks/mask.mnc %s/NUC/%s.mnc %s/NUC/%s_face.mnc' %(inputfolder, inputfolder, inputfolder, inputfolder, inputfolder))
    themax = execute('mincstats -max -quiet %s/NUC/%s_face.mnc' %(inputfolder, inputfolder)) 	
    themin = execute('mincstats -min -quiet %s/NUC/%s_face.mnc' %(inputfolder, inputfolder))
    execute('minccalc -clob %s/NUC/%s_face.mnc -expression "10000*(A[0]-0)/(%s-%s)" %s/NORM/%s_face.mnc' %(inputfolder, inputfolder, themax[0:-1], themin[0:-1], inputfolder, inputfolder))         
  return


def autocrop(image_type, targetname): 
  """Expands the bounds of the target image MINC file by 10% for all axes.
  Executed when the target image is a randomly selected subject."""
  if image_type == 'brain':
    execute('autocrop -clobber -isoexpand 10 %s/NORM/%s.mnc %s/NORM/%s_crop.mnc' %(targetname,targetname,targetname,targetname))
    execute('autocrop -clobber -isoexpand 10 %s/masks/mask.mnc %s/masks/mask_crop.mnc' %(targetname, targetname))
  elif image_type == 'face':
    execute('autocrop -clobber -isoexpand 10 %s/NORM/%s_face.mnc %s/NORM/%s_face_crop.mnc' %(targetname,targetname,targetname,targetname))
  return

  
def preprocess2(sourcename, targetname, image_type):   
  """Preprocessing Stage - Continued
  Executed when the target image is a randomly selected (normalized) subject.
  1) Estimate the linear 6-parameter transformation (using the expanded version of the randomly selected subject as the target image) 
  2) Resample
  """
  if image_type == 'brain':
    execute('bestlinreg -clob -lsq6 -source_mask %s/masks/mask.mnc -target_mask %s/masks/mask_crop.mnc %s/NORM/%s.mnc %s/NORM/%s_crop.mnc %s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, targetname, sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
    resample('%s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, sourcename, targetname), '%s/NORM/%s.mnc' %(sourcename, sourcename), '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename))   
  elif image_type == 'face':    
    execute('bestlinreg -clob -lsq6 %s/NORM/%s_face.mnc %s/NORM/%s_face_crop.mnc %s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
    resample('%s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, sourcename, targetname), '%s/NORM/%s_face.mnc' %(sourcename, sourcename), '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename))       
  return


def pairwise_reg(sourcename, targetname):
  """Pairwise 12-parameter registrations: PART 1
  1) Estimate the linear 12-parameter transformation of each subject to all the other subjects"""
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return

def xfmavg_and_resample(inputname):
  """Pairwise 12-parameter registrations: PART 2
  1) Average the transformation (xfm) files of each subject to all the other subjects
  2) Resample (i.e. apply the subject's average transformation)"""
  execute('xfmavg -clob %s/pairwise_tfiles/* %s/pairwise_tfiles/%s.xfm' %(inputname, inputname, inputname))
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname), '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname), '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname))
  return


def lsq12reg(sourcename, targetname):
  '''Non-pairwise 12-parameter registrations: PART 1
  1) Estimate the linear 12-parameter transformation of each subject to the randomly selected target subject '''
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return

   
def xfmavg_inv_resample(targetname):
  """Non-pairwise 12-parameter registrations: PART 2
  1) Average all 12-parameter transformation (xfm) files
  2) Invert the average transformation
  3) Resample (i.e. apply inverted average transformation to the randomly selected subject)"""
  execute('xfmavg -clob */lin_tfiles/*_*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  resample('lsq12avg_inverse.xfm','%s/output_lsq6/%s_lsq6.mnc' %(targetname, targetname), 'avgsize.mnc')
  return 


def lsq12reg_and_resample(sourcename):
  """Non-pairwise 12-parameter registrations: PART 3
  Repeat 12-parameter transformation of each input to this 'average size' & resample"""
  execute('bestlinreg -clob -lsq12 %s/output_lsq6/%s_lsq6.mnc avgsize.mnc %s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename, sourcename, sourcename))
  resample('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename), '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename), '%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename))
  return


def resample(xfm, inputpath, outputpath):
  """Mincresample a minc file using a transformation file"""
  if os.path.exists('targetimage.mnc'):   # better way??
    execute('mincresample -clob -transformation %s %s %s -sinc -like targetimage.mnc' %(xfm, inputpath, outputpath))  
  else:
    if len(glob.glob('H*/NORM/*_crop.mnc')) == 1:
      execute('mincresample -clob -transformation %s %s %s -sinc -like H*/NORM/*_crop.mnc' %(xfm, inputpath, outputpath))
    #if len(glob.glob('H*/NORM/*_face_crop.mnc')) == 1:
      #execute('mincresample -clob -transformation %s %s %s -sinc -like H*/NORM/*_face_crop.mnc' %(xfm, inputpath, outputpath))    
  return



def linavg_and_check(inputfolder, inputreg, outputname):
  """Creates the linear model by averaging the linearly processed images. 
  Also, checks for the successful completion of the 12-parameter registration stage"""
  mnc_avg(inputfolder, inputreg, outputname)
  try:
    execute('minccomplete avgimages/linavg.mnc')   # check for average 
  except subprocess.CalledProcessError:
    execute("qdel reg*, nonlin*, s6*, tr*, blur*")
    #print e.output
  return


def mnc_avg(inputfolder,inputreg,outputname):
  """Generates a model by averaging the given images"""
  execute('mincaverage -clob */%s/*_%s.mnc avgimages/%s' %(inputfolder,inputreg,outputname))
  return


def nonlin_reg(inputname, sourcepath, targetimage, number, iterations):
  """Nonlinear processing using mincANTS
  1) Using mincANTS, estimate the nonlinear transformation of each subject to the model created from the previous iteration of mincANTS
     For the first iteration, subjects are registered to the linear model.
  2) Resample (i.e. apply the output transformation from mincANTS) """
  execute('mincANTS 3 -m PR[%s,avgimages/%s,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s/tfiles_nonlin/%s_nonlin%s.xfm \
      -i %s' %(sourcepath, targetimage, inputname, inputname, number, iterations))
  resample('%s/tfiles_nonlin/%s_nonlin%s.xfm' %(inputname, inputname, number), sourcepath, '%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname,number))   
  return
  
  
 

def tracc(inputname, num, fwhm, iterations, step, model):
  """Nonlinear processing using minctracc
  1) Gaussian kernel blurring of the linearly processed (12-parameter) subject images with the specified FWHM.
  2) Using minctracc, estimate the nonlinear transformation of each subject to the model created from the previous iteration.
     For each iteration except the first, the blurred subject image, blurred model image and the transformation file from the previous iteration are forked in.
     For the first iteration, the blurred subject image is registered to the blurred linear model. 
  3) Resample """
  
  lttdiam = int(step)*3  # lattice diameter is 3 x step size
  if not os.path.exists('%s/minctracc_out/%s_lsq12_%s_blur.mnc' %(inputname, inputname,fwhm)):
    execute('mincblur -clob -fwhm %s %s/timage_lsq12/%s_lsq12.mnc %s/minctracc_out/%s_lsq12_%s' %(fwhm, inputname, inputname, inputname, inputname,fwhm))
  if num == '1':     # no -transformation option for first minctracc
    execute('minctracc -clob -nonlinear corrcoeff \
        -iterations 30 \
        -step 8 8 8 \
        -sub_lattice 6 \
        -lattice_diameter 24 24 24 \
        -stiffness 1 \
        -weight 1 \
        -similarity 0.3 \
        %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/linavg_blur.mnc %s/minctracc_out/%s_out1.xfm' %(inputname, inputname, fwhm, inputname, inputname))
  else:
    execute('minctracc -clob -nonlinear corrcoeff \
      -iterations %s \
      -step %s %s %s \
      -sub_lattice 6 \
      -lattice_diameter %s %s %s \
      -stiffness 1 \
      -weight 1 \
      -similarity 0.3 \
      -transformation %s/minctracc_out/%s_out%s.xfm \
      %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/%s_blur.mnc %s/minctracc_out/%s_out%s.xfm' %(iterations, step, step, step, lttdiam, lttdiam, lttdiam, inputname, inputname, int(num)-1, inputname, inputname, fwhm, model[0:-4], inputname, inputname, num))
  resample('%s/minctracc_out/%s_out%s.xfm' %(inputname,inputname,num), '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname), '%s/minctracc_out/%s_nlin%s.mnc' %(inputname,inputname,num))
  return

def deformation(inputname):
  """ Final statistics stage """
  try:
    # assume minctracc was executed 
    execute('minccalc -clob %s/minctracc_out/%s_out6_grid* -expression "-1*A[0]" %s/final_stats/%s_inversegrid.mnc' %(inputname, inputname, inputname, inputname))
  except subprocess.CalledProcessError:
    # can't access minctracc output grid, so assume mincANTS was executed
    # /projects/utilities/xfmjoin
    execute('xfmjoin %s/tfiles_nonlin/%s_nonlin1.xfm %s/tfiles_nonlin/%s_nonlin2.xfm %s/tfiles_nonlin/%s_nonlin3.xfm %s/tfiles_nonlin/%s_nonlin4.xfm %s/%s_merged2.xfm' %(inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname))
    outputfile = open('%s/%s_merged.xfm' %(inputname,inputname), 'w')
    info = open('%s/%s_merged2.xfm' %(inputname,inputname)).read()
    outputfile.write(re.sub("= %s/" %inputname, "= ",info))
    outputfile.close()
    os.remove('%s/%s_merged2.xfm' %(inputname,inputname))
    execute('minc_displacement %s/timage_lsq12/%s_lsq12.mnc %s/%s_merged.xfm %s/final_stats/%s_grid.mnc' %(inputname, inputname, inputname, inputname, inputname, inputname))
    execute('minccalc -clob %s/final_stats/%s_grid.mnc -expression "-1*A[0]" %s/final_stats/%s_inversegrid.mnc' %(inputname, inputname, inputname, inputname)) 
  execute('mincblob -determinant %s/final_stats/%s_inversegrid.mnc %s/final_stats/%s_det.mnc' %(inputname, inputname, inputname, inputname))
  execute('mincblur -fwhm 6 %s/final_stats/%s_det.mnc %s/final_stats/%s' %(inputname, inputname, inputname, inputname))  
  return 
    
if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess':
    preprocess(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'autocrop':
    autocrop(sys.argv[2], sys.argv[3])
  elif cmd == 'preprocess2':
    preprocess2(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'pairwise_reg':
    pairwise_reg(sys.argv[2], sys.argv[3])
  elif cmd == 'linavg_and_check':
    linavg_and_check(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'lsq12reg':
    lsq12reg(sys.argv[2], sys.argv[3])
  elif cmd == 'xfmavg_inv_resample':
    xfmavg_inv_resample(sys.argv[2]) 
  elif cmd == 'lsq12reg_and_resample':
    lsq12reg_and_resample(sys.argv[2])    
  elif cmd == 'xfmavg_and_resample':
    xfmavg_and_resample(sys.argv[2])
  elif cmd == 'mnc_avg':
    mnc_avg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'nonlin_reg':
    nonlin_reg(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])
  elif cmd == 'deformation':
    deformation(sys.argv[2])
  elif cmd == 'tracc':
    tracc(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],sys.argv[7])