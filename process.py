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

            Stage                           Associated Functions (called by pipeline.py)           
1  Preprocessing                       preprocess, autocrop, preprocess2

2  Pairwise linear 12-parameter        lsq12_reg, xfmavg_and_resample, linavg_and_check
   registrations (3 Parts)
   
   Non-Pairwise linear 12-parameter    lsq12_reg, xfmavg_inv_resample, lsq12reg_and_resample, linavg_and_check 
   registrations (4 Parts)               

3  Nonlinear processing                ants_and_resample
   using mincANTS 
   
   Nonlinear processing                model_blur, tracc 
   using minctracc

4  Deformation fields                  deformation


   Landmarked-based facial feature     (functions from stages 1-4), tag_nlinavg, tag_subject
   analysis (optional)
   
   Longitudinal analysis (optional)    longitudinal

   Asymmetrical analysis (optional)    asymmetric_analysis

        
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
  #   (Preprocessing is completed in preprocess2)
  
  execute('nu_correct -clob inputs/%s.mnc %s/NUC/%s.mnc' %(subject, subject, subject)) 
  if image_type == 'brain':
    themax = execute('mincstats -max -quiet %s/NUC/%s.mnc' %(subject, subject))   	
    themin = execute('mincstats -min -quiet %s/NUC/%s.mnc' %(subject, subject)) 
    # both themax & themin contain the newline character at the end of the string 
    # Ex. themax = '7054.400964\n', themin = '0\n'
    # themax[0:-1] is the string of the numerical value without the newline character 
    execute('minccalc -clob -expression "10000*(A[0]-0)/(%s-%s)" \
                      %s/NUC/%s.mnc %s/NORM/%s.mnc'
            %(themax[0:-1], themin[0:-1], subject, subject, subject, subject)) 
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
            %(themax[0:-1], themin[0:-1], subject, subject, subject, subject))
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
  #   Estimates the linear 12-parameter transformation of each subject to
  #     a) all the other subjects (pairwise) or 
  #     b) the randomly selected target subject (non-pairwise)
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/%s/%s_%s_lsq12.xfm'
          %(sourcename, sourcename, targetname,targetname, sourcename, outputfolder, sourcename, targetname))
  return


def xfmavg_and_resample(inputname):
  # STAGE 2 (Pairwise Registrations): Part 2 (of 3)
  #   Averages the transformation (xfm) files of each subject to all the other 
  #   subjects and resamples (i.e. apply the subject's average transformation)
  execute('xfmavg -clob %s/pairwise_tfiles/* %s/pairwise_tfiles/%s.xfm'
          %(inputname, inputname, inputname))   
  execute('cp %s/pairwise_tfiles/%s.xfm %s/lin_tfiles/%s_lsq12.xfm' %(inputname, inputname, inputname, inputname))   
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname),      # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname),     # source
           '%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname))   # output 
  return

   
def xfmavg_inv_resample(targetname):
  # STAGE 2 (Non-Pairwise Registrations): Part 2 (of 4)
  #   Averages all 12-parameter transformation (xfm) files. Inverts the average 
  #   transformation and applies it to the randomly selected target subject
  execute('xfmavg -clob */lin_tfiles/*_*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  resample('lsq12avg_inverse.xfm',                                  # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(targetname, targetname),  # source
           'avgsize.mnc')                                           # output 
  return 


def lsq12reg_and_resample(sourcename):
  # STAGE 2 (Non-Pairwise Registrations): Part 3 (of 4)
  #   Estimates the linear 12-parameter transformation of each input to the 
  #   'average size' generated from Part 2 & resamples.
  execute('bestlinreg -clob -lsq12 %s/output_lsq6/%s_lsq6.mnc avgsize.mnc %s/lin_tfiles/%s_lsq12.xfm'
          %(sourcename, sourcename, sourcename, sourcename))
  resample('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename),    # xfm
           '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename),    # source
           '%s/output_lsq12/%s_lsq12.mnc' %(sourcename, sourcename))  # output
  return


def linavg_and_check(inputfolder, inputreg, outputname):
  # STAGE 2 (Pairwise/Non-Pairwise Registrations): Part 3 (of 3) / Part 4 (of 4)   
  #   Creates a linear model by averaging the linearly processed images. 
  #   Also checks for the successful completion of the 12-parameter registration stage.
  mnc_avg(inputfolder, inputreg, outputname)
  try:
    execute('minccomplete avgimages/linavg.mnc')   # check for average 
  except subprocess.CalledProcessError:
    execute("qdel reg*, nlin*, s6*, tr*, blur*")
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

def mincANTS(from_image, to_image, output_xfm, iterations):
  # Executes nonlinear registrations using mincANTS

  execute('mincANTS 3 -m PR[%s,%s,1,4] \
      --number-of-affine-iterations 0 \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s \
      -i %s' %(from_image, to_image, output_xfm, iterations))
  #--number-of-affine-iterations 10000x10000x10000x10000x10000 \
  #--MI-option 32x16000 \
  #--affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
  #--use-Histogram-Matching \
  return 

def ants_and_resample(inputname, sourcepath, targetimage, number, iterations):
  # STAGE 3 : Nonlinear processing using mincANTS
  #   1) Estimates the nonlinear transformation of each subject to the model 
  #      created from the previous iteration of mincANTS. For the first iteration,
  #      subjects are registered to the linear model.
  #   2) Resamples.
  from_image = sourcepath
  to_image = 'avgimages/%s' %targetimage
  output_xfm = '%s/nlin_tfiles/%s_nlin%s.xfm' %(inputname, inputname, number)
  mincANTS(from_image, to_image, output_xfm, iterations)
  #execute('mincANTS 3 -m PR[%s,avgimages/%s,1,4] \
      #--number-of-affine-iterations 10000x10000x10000x10000x10000 \
      #--MI-option 32x16000 \
      #--affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      #--use-Histogram-Matching \
      #-r Gauss[3,0] \
      #-t SyN[0.5] \
      #-o %s/nlin_tfiles/%s_nlin%s.xfm \
      #-i %s' %(sourcepath, targetimage, inputname, inputname, number, iterations))
  resample('%s/nlin_tfiles/%s_nlin%s.xfm' %(inputname, inputname, number),
           sourcepath, '%s/nlin_timages/%s_nlin%s.mnc'
           %(inputname,inputname,number))   
  return
  
  
def model_blur(fwhm, model):
  # Performs a Gaussian kernel blur on the model image with the specified FWHM
  execute('mincblur -clob -fwhm %s avgimages/%s avgimages/%s' %(fwhm,model,model[0:-4]))
  return


def tracc(inputname, num, fwhm, iterations, step, model):
  # STAGE 3: Nonlinear processing using minctracc
  #   1) Gaussian kernel blurring of the linearly processed (12-parameter) subject
  #      images with the specified FWHM.
  #   2) Estimates the nonlinear transformation of each subject to the model 
  #      created from the previous iteration. For each iteration except the first,
  #      the blurred subject image, blurred model image and the transformation file
  #      from the previous iteration are inputted. For the first iteration, the blurred
  #      subject image is registered to the blurred linear model with no 
  #      input transformation file. 
  #   3) Resamples
  
  lttdiam = int(step)*3  # lattice diameter is 3 x step size
  if not os.path.exists('%s/minctracc_out/%s_lsq12_%s_blur.mnc' %(inputname, inputname,fwhm)):
    execute('mincblur -clob -fwhm %s %s/output_lsq12/%s_lsq12.mnc %s/minctracc_out/%s_lsq12_%s'
            %(fwhm, inputname, inputname, inputname, inputname,fwhm))
  if num == '1':     # no -transformation option for first minctracc iteration
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
      -transformation %s/minctracc_out/%s_out%s.xfm \
      %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/%s_blur.mnc %s/minctracc_out/%s_out%s.xfm' 
      %(iterations, step, step, step, lttdiam, lttdiam, lttdiam, inputname, inputname, int(num)-1, 
        inputname, inputname, fwhm, model[0:-4], inputname, inputname, num))
  resample('%s/minctracc_out/%s_out%s.xfm' %(inputname,inputname,num),   # xfm
           '%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname),       # source 
           '%s/minctracc_out/%s_nlin%s.mnc' %(inputname,inputname,num))  # output
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
    xfms = ""
    for xfm in glob.glob('%s/nlin_tfiles/*.xfm' %inputname):  
      if xfm[-11:] != 'inverse.xfm':
        xfms += xfm
        xfms += " "
    execute('xfmjoin %s %s/%s_merged2.xfm' %(xfms, inputname, inputname))
    outfile = open('xfms.xfm', 'w')
    outfile.write(xfms)
    outfile.close()      
    #execute('xfmjoin %s/nlin_tfiles/%s_nlin1.xfm \
                     #%s/nlin_tfiles/%s_nlin2.xfm \
                     #%s/nlin_tfiles/%s_nlin3.xfm \
                     #%s/nlin_tfiles/%s_nlin4.xfm \
                     #%s/%s_merged2.xfm' 
                     #%(inputname, inputname, inputname, inputname, inputname, 
                       #inputname, inputname, inputname, inputname, inputname))
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


def tag_nlinavg():
  # Landmark-based facial feature analysis: Part 1 (of 2)
  #   Transforms the model tags (landmarks) by the input transform that maps the 
  #   model image to the nonlinear average image.
  
  from_image = 'sys_881_face_model.mnc' #TODO: filename for now
  to_image = 'avgimages/nlin4avg.mnc' # when minctracc, nlin6avg.mnc??
  output_xfm = 'model_to_nlinavg.xfm'
  iterations = '100x1x1x1'
  mincANTS(from_image, to_image, output_xfm, iterations) 
  
  input_tag = 'face_tags_sys881_June21_2012.tag' #TODO: filename for now
  input_xfm = output_xfm
  output_tag = 'nlin_face_tags'
  execute('transform_tags %s %s %s' %(input_tag, input_xfm, output_tag))
  return


def tag_subject(inputname):
  # Landmark-based facial feature analysis: Part 2 (of 2)
  #   Warps the landmarks to each subject using the inverse of the nonlinear transformation 
  #   that maps the subject to the nonlinear average image.
  
  # Volumetric differences
  xfms = []
  for xfm in glob.glob('%s/nlin_tfiles/%s_nlin?.xfm' %(inputname, inputname)):
    xfms.append(xfm)
  xfms = " ".join(xfms) # string of nonlinear xfms  
  # concate nonlinear transformation files only
  execute('xfmjoin %s %s/nlin_tfiles/%s_nlin_merged.xfm' %(xfms, inputname, inputname))  
  
  input_tag = 'nlin_face_tags.tag'
  input_xfm = '%s/nlin_tfiles/%s_nlin_merged.xfm' %(inputname, inputname) # maps craniofacial structure of subject to average image
  output_tag = '%s/%s_voldiff_landmarks' %(inputname, inputname)
  iterations = '100x1x1x1'
  execute('transform_tags %s %s %s invert' %(input_tag, input_xfm, output_tag)) # use inverse of the transform (to bring landmarks to subject space)
  
  tagfile = open('%s/%s_voldiff_landmarks.tag' %(inputname, inputname), 'r')
  csvfile = open('%s/%s_voldiff_landmarks.csv' %(inputname, inputname), 'w')
  create_csv(tagfile, csvfile)
  
  # Shape & volumetric differences  
  avg_lsq12_xfm = ' %s/lin_tfiles/%s_lsq12.xfm' %(inputname, inputname)  # average lsq12 transform file
  xfms += avg_lsq12_xfm 
  # concate lsq12 & nonlinear transformation files
  execute('xfmjoin %s %s/nlin_tfiles/%s_lsq12_nlin_merged.xfm' %(xfms, inputname, inputname))
  
  input_xfm = '%s/nlin_tfiles/%s_lsq12_nlin_merged.xfm' %(inputname, inputname)
  output_tag = '%s/%s_vol_shape_diff_landmarks' %(inputname, inputname)
  execute('transform_tags %s %s %s invert' %(input_tag, input_xfm, output_tag)) 
  
  tagfile = open('%s/%s_vol_shape_diff_landmarks.tag' %(inputname, inputname), 'r')
  csvfile = open('%s/%s_vol_shape_diff_landmarks.csv' %(inputname, inputname,'w'))
  create_csv(tagfile, csvfile) 
  return 


def create_csv(tagfile, csvfile):
  # Create a csv tag file.
  csvfile.write("x,y,z\n")
  for line in tagfile:
    if len(line) > 50:
      values = line.split()
      thevalues = values[0] + "," + values[1] + "," + values[2]
      csvfile.write(thevalues)
      csvfile.write("\n")  
  return


def longitudinal(inputname_time2):
  # Longitudinal analysis 

  inputname = inputname_time2[0:-2]  # inputname without the "_2" suffix
  
  # 1) Intensity inhomogeneity correction for time-2 images
  execute('nu_correct inputs/%s.mnc %s/longitudinal/%s_nuc.mnc' %(inputname_time2, inputname, inputname_time2))
  
  # 2) Rigid body 6-parameter transformation of the (corrected) time-2 image to the (original corrected) time-1 image of every subject. 
  execute('bestlinreg -lsq6 -clob \
                      %s/longitudinal/%s_nuc.mnc \
                      %s/NUC/%s.mnc \
                      %s/longitudinal/time2to1.xfm'
                      %(inputname, inputname_time2, inputname, inputname, inputname))  
  
  execute('mincresample -clob -transformation \
                        %s/longitudinal/time2to1.xfm \
                        %s/longitudinal/%s_nuc.mnc \
                        %s/longitudinal/time2_lsq6.mnc \
                        -like %s/NUC/%s.mnc' 
                        %(inputname, inputname, inputname_time2, inputname, inputname, inputname))
  
  # 3) Nonlinear registration (with mincANTS) of (original corrected) time-1 to (transformed) time-2 
       
  mincANTS('%s/NUC/%s.mnc' %(inputname, inputname),                # from_image  (nu-corrected original)
           '%s/longitudinal/time2_lsq6.mnc' %inputname,            # to_image
           '%s/longitudinal/time1to2_nlin.xfm' %inputname,         # output_xfm 
           '100x1x1x1')                                            # iterations
  
  # 4) Compute the Jacobian determinant of the output grid (displacement volume/deformation field) from mincANTS (to detect volumetric change)
  execute('mincblob -clob -determinant \
                    %s/longitudinal/time1to2_nlin_grid_0.mnc %s/longitudinal/det.mnc' 
                    %(inputname, inputname))
  
  # 5) Concatenate nonlinear transformation files
  xfms = ""
  for xfm in glob.glob('%s/nlin_tfiles/%s_nlin?.xfm' %(inputname, inputname)):
    xfms += xfm
    xfms += " "
  execute('xfmjoin %s %s/nlin_tfiles/%s_nlin_merged.xfm' %(xfms, inputname, inputname))
  
  # 6) Warp back to the model space (generated from time-1 nonlinear processing)
  execute('mincresample -clob \
                        -transformation %s/nlin_tfiles/%s_nlin_merged.xfm \
                        %s/longitudinal/det.mnc \
                        %s/longitudinal/det2model.mnc \
                        -like avgimages/nlin4avg.mnc' %(inputname, inputname, inputname, inputname))  #TODO: minctracc? will have nlin6avg.mnc
  # 7) Blur
  execute('mincblur -clob -fwhm 4 %s/longitudinal/det2model.mnc %s/longitudinal/det_fwhm4' %(inputname, inputname))
  execute('mincblur -clob -fwhm 6 %s/longitudinal/det2model.mnc %s/longitudinal/det_fwhm6' %(inputname, inputname))
  execute('mincblur -clob -fwhm 8 %s/longitudinal/det2model.mnc %s/longitudinal/det_fwhm8' %(inputname, inputname))
  return


def asymmetric_analysis(inputname):
  # Asymmetrical analysis
  
  # flip 
  execute('volflip -x -clob %s/output_lsq12/%s_lsq12.mnc %s/output_lsq12/%s_flipped_lsq12.mnc' %(inputname, inputname, inputname, inputname))
  if not os.path.exists()
  
  # Nonlinearly register each MRI volume to its respective flippped coronal image volume
  if not os.path.exists('%s/nlin_tfiles/%s_nlin_grid_0.mnc' %(inputname, inputname)):
    mincANTS('%s/output_lsq12/%s_lsq12.mnc' %(inputname, inputname),          # from_image
             '%s/output_lsq12/%s_flipped_lsq12.mnc' %(inputname, inputname),  # to_image
             '%s/asymmetrical/%s_nlin.xfm' %(inputname, inputname),           # output_xfm
             '100x1x1x1')                                                     # iterations
    
  # 6) Get Jacobian determinant of each transformation
  execute('mincblob -clob -determinant %s/asymmetrical/%s_nlin_grid_0.mnc %s/asymmetrical/%s_det.mnc' %(inputname, inputname, inputname,inputname))
    
  # 7) Blur
  execute('mincblur -clob -fwhm 8 %s/asymmetrical/%s_det.mnc %s/asymmetrical/%s_det' %(inputname, inputname, inputname, inputname))

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
  elif cmd == 'ants_and_resample':
    ants_and_resample(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])
  elif cmd == 'deformation':
    deformation(sys.argv[2])
  elif cmd == 'tracc':
    tracc(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],sys.argv[7])
  elif cmd == 'model_blur':
    model_blur(sys.argv[2], sys.argv[3])
  elif cmd == 'tag_nlinavg':
    tag_nlinavg()
  elif cmd == 'tag_subject':
    tag_subject(sys.argv[2])
  elif cmd == 'longitudinal':
    longitudinal(sys.argv[2])
    