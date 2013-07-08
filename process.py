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

def preprocess(thefile, image_type, target_type):
  name = thefile[0:-4]
  execute('nu_correct -clob inputs/%s %s/NUC/%s' %(thefile, name, thefile))
  themax = execute('mincstats -max ' + name + '/NUC/' + thefile + ' | cut -c20-31') 	
  themin = execute('mincstats -min ' + name + '/NUC/' + thefile + ' | cut -c20-31')
  execute ('minccalc -clob %s/NUC/%s -expression "10000*(A[0]-0)/(%s-%s)" %s/NORM/%s' %(name, thefile, themax, themin, name, thefile))
  execute("mnc2nii %s/NORM/%s %s/%s.nii" %(name, thefile, name, name))
  # use sienax to generate mask
  tmpdir = tempfile.mkdtemp(dir = '%s/' %name)
  execute("sienax %s/%s.nii -d -o %s" %(name, name, tmpdir)) # -r option ??
  execute("gzip -d %s/I_stdmaskbrain_seg.nii.gz" %(tmpdir))
  execute("nii2mnc %s/I_stdmaskbrain_seg.nii %s/I_stdmaskbrain_seg.mnc" %(tmpdir, tmpdir))
  execute('minccalc -clob -expression "A[0] > 0.5" %s/I_stdmaskbrain_seg.mnc %s/masks/I_stdmaskbrain_seg_discrete.mnc' %(tmpdir,name))
  shutil.rmtree(tmpdir)
  execute('mincresample -clob %s/masks/I_stdmaskbrain_seg_discrete.mnc %s/masks/mask.mnc -like %s/NORM/%s.mnc' %(name,name,name,name))
  if target_type == 'given':
    # face
    if image_type == 'face':
      execute('minccalc -clob -expression "(1-A[0])*A[1]" %s/masks/mask.mnc %s/NORM/%s.mnc %s/%s_face.mnc' %(name, name, name, name, name))
      execute('bestlinreg -clob -lsq6 %s/%s_face.mnc targetfaceimage.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, name,name, name))
      execute('mincresample -transformation %s/lin_tfiles/%s_lsq6.xfm %s/%s_face.mnc %s/output_lsq6/%s_lsq6.mnc -sinc -like targetfaceimage.mnc' %(name, name, name, name, name, name))
 
    # brain
    else:
      execute('bestlinreg -clob -lsq6 -source_mask %s/masks/mask.mnc -target_mask targetmask.mnc %s/NORM/%s targetimage.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, name, thefile, name, name))  
      resample('%s/lin_tfiles/%s_lsq6.xfm' %(name, name), '%s/NORM/%s' %(name, thefile), '%s/output_lsq6/%s_lsq6.mnc' %(name, name))
  
    
    # execute ('mincbet %s/NORM/%s %s/masks/%s -m' %(name, thefile, name, name))
    # mask = name + '_mask.mnc'     
    # targetmask = ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc
    # targetimage = ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc 
  return



def pairwise_reg(sourcename, targetname):
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return


def lsq12reg(sourcename, targetname):
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return

   
def xfmavg_inv_resample(targetname):
  execute('xfmavg -clob */lin_tfiles/*_*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  resample('lsq12avg_inverse.xfm','%s/output_lsq6/%s_lsq6.mnc' %(targetname, targetname), 'avgsize.mnc')
  return 


def lsq12reg_and_resample(sourcename):
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc avgsize.mnc %s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename, sourcename, sourcename))
  #lsq12reg('%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename), 'avgsize.mnc', '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename))
  resample('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename), '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename), '%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename))
  return


def resample(xfm, inputpath, outputpath):
  execute('mincresample -clob -transformation %s %s %s -sinc -like targetimage.mnc' %(xfm, inputpath, outputpath))
  return 


def xfmavg_and_resample(inputname):
  execute('xfmavg -clob %s/pairwise_tfiles/* %s/pairwise_tfiles/%s.xfm' %(inputname, inputname, inputname))
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname), '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname), '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname))
  return


def check_lsq12(string):
  listofinputs = string.split()
  for subject in listofinputs:
    inputname = subject[0:-4]
    #for subject2 in glob.glob('inputs/*'):
      #targetname = subject2[7:11]
      #if targetname != inputname:
        #try:
          #execute('minccomplete %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(inputname, inputname, targetname)) # check all pairwise transformation files (necessary?)
        #except subprocess.CalledProcessError:
          #execute("qdel reg*, nonlin*,s*")
          #sys.exit(1)
    try: 
      execute('minccomplete %s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)) # check for lsq12.mnc for every input
    except subprocess.CalledProcessError:
      execute("qdel reg*, nonlin*, s6*")
  try: 
    execute('minccomplete avgimages/linavg.mnc')   # check for average 
  except subprocess.CalledProcessError:
    execute("qdel reg*, nonlin*, s6*")
    #print e.output
  return  


def linavg_and_check(inputfolder, inputreg, outputname, string):
  execute('mincaverage -clob */%s/*_%s.mnc avgimages/%s' %(inputfolder, inputreg, outputname))
  check_lsq12(string)
  return


def mnc_avg(inputfolder,inputreg,outputname):
  execute('mincaverage -clob */%s/*_%s.mnc avgimages/%s' %(inputfolder,inputreg,outputname))
  return

def nonlin_reg(inputname, sourcepath, targetimage, number, iterations):
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
  
  
def deformation(inputname):
  # /projects/utilities/xfmjoin
  try:
    # assume minctracc was executed 
    execute('minccalc -clob %s/minctracc_out/%s_out6_grid* -expression "-1*A[0]" %s/final_stats/%s_inversegrid.mnc' %(inputname, inputname, inputname, inputname))
  except subprocess.CalledProcessError:
    # can't access minctracc output files, so assume mincANTS was executed
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


def tracc(inputname, num, fwhm, iterations, step, model):
  lttdiam = int(step)*3
  # change path for lsq12 images!!!!   %s/timage_lsq12/%s_lsq12.mnc
  if not os.path.exists('%s/minctracc_out/%s_lsq12_%s_blur.mnc' %(inputname, inputname,fwhm)):
    execute('mincblur -clob -fwhm %s ../timages/%s_lsq12.mnc %s/minctracc_out/%s_lsq12_%s' %(fwhm, inputname, inputname, inputname,fwhm))
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
    #execute('mincresample -clob -transformation %s/minctracc_out/%s_out%s.xfm ../timages/%s_lsq12.mnc %s/minctracc_out/%s_nlin%s.mnc -like targetimage.mnc' %(inputname, inputname, num, inputname, inputname, inputname, num))
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
      %s/minctracc_out/%s_lsq12_%s_blur.mnc avgimages/%s_blur.mnc %s/minctracc_out/%s_out%s.xfm' %(iterations, step,step, step, lttdiam, lttdiam, lttdiam, inputname, inputname, int(num)-1, inputname, inputname, fwhm, model[0:-4], inputname, inputname, num))
  execute('mincresample -clob -transformation %s/minctracc_out/%s_out%s.xfm ../timages/%s_lsq12.mnc %s/minctracc_out/%s_nlin%s.mnc -like targetimage.mnc' %(inputname, inputname, num, inputname, inputname, inputname, num))
  return

#emacs `which nlfit_smr_modelless`  
    
if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess':
    preprocess(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'pairwise_reg':
    pairwise_reg(sys.argv[2], sys.argv[3])
  elif cmd == 'linavg_and_check':
    check_lsq12(sys.argv[2], sys.argv[3], sys.argv[4]. sys.argv[5])
  elif cmd == 'lsq12reg':
    lsq12reg(sys.argv[2], sys.argv[3])
  elif cmd == 'xfmavg_inv_resample':
    xfmavg_inv_resample(sys.argv[2])
  elif cmd == 'lsq12reg_and_resample':
    lsq12reg_and_resample(sys.argv[2])
  elif cmd == 'resample':
    resample(sys.argv[2], sys.argv[3], sys.argv[4])     
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