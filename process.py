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


""" 
A series a functions which execute the stages of the Model-Building Pipeline when 
called upon by pipeline.py

          Stage                            Associated Functions (called by pipeline.py)           
1) Preprocessing                       preprocess, autocrop, preprocess2

2) Pairwise linear 12-parameter        lsq12_reg, xfmavg_and_resample, linavg_and_check
   registrations (3 Parts)
   
   Non-Pairwise linear 12-parameter    lsq12_reg, xfmavg_inv_resample, lsq12reg_and_resample, linavg_and_check 
   registrations (4 Parts)               

3) Nonlinear processing                ants
   using mincANTS 
   
   Nonlinear processing                model_blur, tracc 
   using minctracc

4) Deformation fields                  deformation
"""

def mask(inputname, inputfolder):
  # Generates brain mask using sienax
  execute("mnc2nii %s/%s/%s.mnc %s/%s.nii" %(inputname,inputfolder, inputname, inputname, inputname))
  tmpdir = tempfile.mkdtemp(dir = '%s/' %inputname)
  execute("sienax %s/%s.nii -d -o %s" %(inputname, inputname, tmpdir)) 
  execute("gzip -d %s/I_stdmaskbrain_seg.nii.gz" %(tmpdir))
  execute("nii2mnc %s/I_stdmaskbrain_seg.nii %s/I_stdmaskbrain_seg.mnc" %(tmpdir, tmpdir))
  execute('minccalc -clob -expression "A[0] > 0.5" %s/I_stdmaskbrain_seg.mnc %s/masks/I_stdmaskbrain_seg_discrete.mnc' 
          %(tmpdir,inputname))
  shutil.rmtree(tmpdir)
  execute('mincresample -clob %s/masks/I_stdmaskbrain_seg_discrete.mnc %s/masks/mask.mnc -like %s/%s/%s.mnc' 
          %(inputname, inputname, inputname, inputfolder,inputname))  
  return
  

def preprocess(subject, image_type, target_type):
  # STAGE 1: Preprocesses the input dataset
  # 
  # Summary of steps executed:
  #
  # Brain Imaging
  #  1) Intensity inhomogeneity correction
  #  2) Normalization 
  #  3) Masking (with sienax)
  #  4) Linear 6-parameter registration & resampling ** 
  #     ** If target image and target mask minc files are provided.
  #        Otherwise, the registration is carried out in preprocess2.  
  #  
  # Craniofacial Structure Imaging 
  #  1) Intensity inhomogeneity correction
  #  2) Brain extraction (with sienax)
  #  3) Normalization
  #  (Preprocessing is completed in preprocess2)
  
  execute('nu_correct -clob inputs/%s.mnc %s/NUC/%s.mnc' %(subject, subject, subject)) 
  if image_type == 'brain':
    themax = execute('mincstats -max -quiet %s/NUC/%s.mnc' %(subject, subject))   	
    themin = execute('mincstats -min -quiet %s/NUC/%s.mnc' %(subject, subject)) 
    # both themax & themin contain the newline character at the end of the string 
    # Ex. themax = '7054.400964\n', themin = '0\n'
    # themax[0:-1] is the string of the numerical value without the newline character 
    execute('minccalc -clob -expression "10000*(A[0]-0)/(%s-%s)" \
                      %s/NUC/%s.mnc %s/NORM/%s.mnc'
            %(subject, subject, themax[0:-1], themin[0:-1], subject, subject)) 
    mask(subject, 'NORM') # use the normalized image to generate the mask
    if target_type == 'given': # if target image is provided by the user 
      execute('bestlinreg -clob -lsq6 \
                          -source_mask %s/masks/mask.mnc \
                          -target_mask targetmask.mnc \
                          %s/NORM/%s.mnc targetimage.mnc %s/lin_tfiles/%s_lsq6.xfm' 
              %(subject, subject, subject, subject, subject))
      resample('%s/lin_tfiles/%s_lsq6.xfm' %(subject, subject),   # xfm
               '%s/NORM/%s.mnc' %(subject, subject),              # source 
               '%s/output_lsq6/%s_lsq6.mnc' %(subject, subject))  # output
  
  elif image_type == 'face':  
    mask(subject,'NUC') # use the (intensity non-uniformity) corrected image to generate the mask
    execute('minccalc -clob -expression "(1-A[1])*A[0]" \
                  %s/NUC/%s.mnc %s/masks/mask.mnc %s/NUC/%s_face.mnc' 
                  %(subject, subject, subject, subject, subject))    
    themax = execute('mincstats -max -quiet %s/NUC/%s_face.mnc' %(subject, subject)) 	
    themin = execute('mincstats -min -quiet %s/NUC/%s_face.mnc' %(subject, subject))
    execute('minccalc -clob -expression "10000*(A[0]-0)/(%s-%s)" \
                      %s/NUC/%s_face.mnc %s/NORM/%s_face.mnc' 
            %(subject, subject, themax[0:-1], themin[0:-1], subject, subject))
  return


def autocrop(image_type, targetname):
  # Expands the bounds of the target image by 10% for all axes.
  # Executed when the target image (for the linear 6-parameter registration
  # in STAGE 1) is a randomly selected subject.
  if image_type == 'brain':
    execute('autocrop -clobber -isoexpand 10 %s/NORM/%s.mnc %s/NORM/%s_crop.mnc' 
            %(targetname,targetname,targetname,targetname))
    execute('autocrop -clobber -isoexpand 10 %s/masks/mask.mnc %s/masks/mask_crop.mnc' 
            %(targetname, targetname))
  elif image_type == 'face':
    execute('autocrop -clobber -isoexpand 10 %s/NORM/%s_face.mnc %s/NORM/%s_face_crop.mnc' 
            %(targetname,targetname,targetname,targetname))
  return

  
def preprocess2(sourcename, targetname, image_type):
  # STAGE 1 Continued**: Linear 6-parameter transformation (using the expanded 
  #                      version of the randomly selected subject as the target
  #                      image) & resampling 
  #                    
  #    ** Executed only when the target image (for the linear 6-parameter 
  #       registration) is a randomly selected (normalized) subject.
  
  if image_type == 'brain':
    execute('bestlinreg -clob -lsq6 \
              -source_mask %s/masks/mask.mnc \
              -target_mask %s/masks/mask_crop.mnc \
              %s/NORM/%s.mnc %s/NORM/%s_crop.mnc %s/lin_tfiles/%s_%s_lsq6.xfm'
              %(sourcename, targetname, sourcename, sourcename, targetname,
                targetname, sourcename, sourcename, targetname))
    resample('%s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, sourcename, targetname), # xfm
             '%s/NORM/%s.mnc' %(sourcename, sourcename),                           # source  
             '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename))               # output
  elif image_type == 'face':    
    execute('bestlinreg -clob -lsq6 %s/NORM/%s_face.mnc %s/NORM/%s_face_crop.mnc %s/lin_tfiles/%s_%s_lsq6.xfm'
            %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
    resample('%s/lin_tfiles/%s_%s_lsq6.xfm' %(sourcename, sourcename, targetname), # xfm
             '%s/NORM/%s_face.mnc' %(sourcename, sourcename),                      # source  
             '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename))               # output    
  return


def lsq12_reg(sourcename, targetname, outputfolder):
  # STAGE 2 (Pairwise/Non-Pairwise Registrations): Part 1 (of 3) / Part 1 (of 4) 
  # 
  # Estimates the linear 12-parameter transformation of each subject to
  #   a) all the other subjects (pairwise) or 
  #   b) the randomly selected target subject (non-pairwise)
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/%s/%s_%s_lsq12.xfm'
          %(sourcename, sourcename, targetname,targetname, sourcename, outputfolder, sourcename, targetname))
  return


def xfmavg_and_resample(inputname):
  # STAGE 2 (Pairwise Registrations): Part 2 (of 3)
  # 
  # Averages the transformation (xfm) files of each subject to all the other 
  # subjects and resamples (i.e. apply the subject's average transformation)
  execute('xfmavg -clob %s/pairwise_tfiles/* %s/pairwise_tfiles/%s.xfm'
          %(inputname, inputname, inputname))
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname),      # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname),     # source
           '%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname))   # output 
  return

   
def xfmavg_inv_resample(targetname):
  # STAGE 2 (Non-Pairwise Registrations): Part 2 (of 4)
  # 
  # Averages all 12-parameter transformation (xfm) files. Inverts the average 
  # transformation and applies it to the randomly selected target subject
  execute('xfmavg -clob */lin_tfiles/*_*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  resample('lsq12avg_inverse.xfm',                                  # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(targetname, targetname),  # source
           'avgsize.mnc')                                           # output 
  return 


def lsq12reg_and_resample(sourcename):
  # STAGE 2 (Non-Pairwise Registrations): Part 3 (of 4)
  # 
  # Estimates the linear 12-parameter transformation of each input to the 
  # 'average size' generated from Part 2 & resamples.
  execute('bestlinreg -clob -lsq12 %s/output_lsq6/%s_lsq6.mnc avgsize.mnc %s/lin_tfiles/%s_lsq12.xfm'
          %(sourcename, sourcename, sourcename, sourcename))
  resample('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename),    # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename),    # source
           '%s/output_lsq12/%s_lsq12.mnc' %(sourcename, sourcename))  # output
  return


def linavg_and_check(inputfolder, inputreg, outputname):
  # STAGE 2 (Pairwise/Non-Pairwise Registrations): Part 3 (of 3) / Part 4 (of 4)   
  # 
  # Creates a linear model by averaging the linearly processed images. 
  # Also checks for the successful completion of the 12-parameter registration stage.
  mnc_avg(inputfolder, inputreg, outputname)
  try:
    execute('minccomplete avgimages/linavg.mnc')   # check for average 
  except subprocess.CalledProcessError:
    execute("qdel reg*, nonlin*, s6*, tr*, blur*")
    #print e.output
  return


def resample(xfm, inputpath, outputpath):
  # Mincresample using a transformation file
  if os.path.exists('targetimage.mnc'):   #TODO:better way??
    execute('mincresample -clob -transformation %s %s %s -sinc -like targetimage.mnc'
            %(xfm, inputpath, outputpath))  
  else:
    if len(glob.glob('H*/NORM/*_crop.mnc')) == 1:
      execute('mincresample -clob -transformation %s %s %s -sinc -like H*/NORM/*_crop.mnc'
              %(xfm, inputpath, outputpath))
    #if len(glob.glob('H*/NORM/*_face_crop.mnc')) == 1:
      #execute('mincresample -clob -transformation %s %s %s 
      #-sinc -like H*/NORM/*_face_crop.mnc' %(xfm, inputpath, outputpath))    
  return


def mnc_avg(inputfolder,inputreg,outputname):
  # Generates a model by averaging the given images
  execute('mincaverage -clob */%s/*_%s.mnc avgimages/%s' %(inputfolder,inputreg,outputname))
  return


def ants(inputname, sourcepath, targetimage, number, iterations):
  # STAGE 3 : Nonlinear processing using mincANTS
  #
  # 1) Estimates the nonlinear transformation of each subject to the model 
  #    created from the previous iteration of mincANTS. For the first iteration,
  #    subjects are registered to the linear model.
  # 2) Resamples.
  execute('mincANTS 3 -m PR[%s,avgimages/%s,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s/nonlin_tfiles/%s_nonlin%s.xfm \
      -i %s' %(sourcepath, targetimage, inputname, inputname, number, iterations))
  resample('%s/nonlin_tfiles/%s_nonlin%s.xfm' %(inputname, inputname, number),
           sourcepath, '%s/nonlin_timages/%s_nonlin%s.mnc'
           %(inputname,inputname,number))   
  return
  
  
def model_blur(fwhm, model):
  # Performs a Gaussian kernel blur on the model image with the specified FWHM
  execute('mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4]))
  return


def tracc(inputname, num, fwhm, iterations, step, model):
  # STAGE 3: Nonlinear processing using minctracc
  #
  # 1) Gaussian kernel blurring of the linearly processed (12-parameter) subject
  #    images with the specified FWHM.
  # 2) Estimates the nonlinear transformation of each subject to the model 
  #    created from the previous iteration. For each iteration except the first,
  #    the blurred subject image, blurred model image and the transformation file
  #    from the previous iteration are inputted. For the first iteration, the blurred
  #    subject image is registered to the blurred linear model with no 
  #    input transformation file. 
  # 3) Resamples
  
  lttdiam = int(step)*3  # lattice diameter is 3 x step size
  if not os.path.exists('%s/minctracc_out/%s_lsq12_%s_blur.mnc' %(inputname, inputname,fwhm)):
    execute('mincblur -clob -fwhm %s %s/output_lsq12/%s_lsq12.mnc %s/minctracc_out/%s_lsq12_%s'
            %(fwhm, inputname, inputname, inputname, inputname,fwhm))
  if num == '1':     # no -transformation option for first minctracc
    execute('minctracc -clob -nonlinear corrcoeff \
        -iterations 30 \
        -step 8 8 8 \
        -sub_lattice 6 \
        -lattice_diameter 24 24 24 \
        -stiffness 1 \
        -weight 1 \
        -similarity 0.3 \
        %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/linavg_blur.mnc %s/minctracc_out/%s_out1.xfm' 
        %(inputname, inputname, fwhm, inputname, inputname))
  else:
    execute('minctracc -clob -nonlinear corrcoeff \
      -iterations %s \
      -step %s %s %s \
      -sub_lattice 6 \
      -lattice_diameter %s %s %s \
      -stiffness 1 \
      -weight 1 \
      -similarity 0.3 \
      -transformation %s/minctracc_out/%s_out%s.xfm %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/%s_blur.mnc %s/minctracc_out/%s_out%s.xfm' 
      %(iterations, step, step, step, lttdiam, lttdiam, lttdiam, inputname, inputname, int(num)-1, inputname, inputname, fwhm, model[0:-4], inputname, inputname, num))
  resample('%s/minctracc_out/%s_out%s.xfm' %(inputname,inputname,num),
           '%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname),
           '%s/minctracc_out/%s_nlin%s.mnc' %(inputname,inputname,num))
  return


def deformation(inputname):
  # STAGE 4: Generates the deformation field between the linearly processed 
  #          and nonlinearly processed images of each subject. Also outputs 
  #          the determinant of the deformation field.
  try:
    # assume minctracc was executed (in which case the displacement volume grid representing all
    # nonlinear transformations was already generated by minctracc)
    execute('minccalc -clob -expression "-1*A[0]" %s/minctracc_out/%s_out6_grid* %s/final_stats/%s_inversegrid.mnc'
            %(inputname, inputname, inputname, inputname))
  except subprocess.CalledProcessError:
    # can't access minctracc output grid, so assume mincANTS was executed
    # join all the nonlinear transformation files
    execute('xfmjoin %s/nonlin_tfiles/%s_nonlin1.xfm \
                     %s/nonlin_tfiles/%s_nonlin2.xfm \
                     %s/nonlin_tfiles/%s_nonlin3.xfm \
                     %s/nonlin_tfiles/%s_nonlin4.xfm \
                     %s/%s_merged2.xfm' 
                     %(inputname, inputname, inputname, inputname, inputname, 
                       inputname, inputname, inputname, inputname, inputname))
    # re-write the merged transformation file without the absolute pathnames 
    # of the displacement volumes
    outputfile = open('%s/%s_merged.xfm' %(inputname,inputname), 'w')
    info = open('%s/%s_merged2.xfm' %(inputname,inputname)).read()
    outputfile.write(re.sub("= %s/" %inputname, "= ",info))
    outputfile.close()
    os.remove('%s/%s_merged2.xfm' %(inputname,inputname))
    execute('minc_displacement %s/output_lsq12/%s_lsq12.mnc %s/%s_merged.xfm %s/final_stats/%s_grid.mnc'
            %(inputname, inputname, inputname, inputname, inputname, inputname))
    execute('minccalc -clob -expression "-1*A[0]" %s/final_stats/%s_grid.mnc %s/final_stats/%s_inversegrid.mnc' 
            %(inputname, inputname, inputname, inputname)) 
  execute('mincblob -determinant %s/final_stats/%s_inversegrid.mnc %s/final_stats/%s_det.mnc'
          %(inputname, inputname, inputname, inputname))
  execute('mincblur -fwhm 6 %s/final_stats/%s_det.mnc %s/final_stats/%s' 
          %(inputname, inputname, inputname, inputname))  
  return 
    
if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess':
    preprocess(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'autocrop':
    autocrop(sys.argv[2], sys.argv[3])
  elif cmd == 'preprocess2':
    preprocess2(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'lsq12_reg':
    lsq12_reg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'linavg_and_check':
    linavg_and_check(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'xfmavg_inv_resample':
    xfmavg_inv_resample(sys.argv[2]) 
  elif cmd == 'lsq12reg_and_resample':
    lsq12reg_and_resample(sys.argv[2])    
  elif cmd == 'xfmavg_and_resample':
    xfmavg_and_resample(sys.argv[2])
  elif cmd == 'mnc_avg':
    mnc_avg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'ants':
    ants(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])
  elif cmd == 'deformation':
    deformation(sys.argv[2])
  elif cmd == 'tracc':
    tracc(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],sys.argv[7])
  elif cmd == 'model_blur':
    model_blur(sys.argv[2], sys.argv[3])