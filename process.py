#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import re


def preprocess(thefile,image_type):
  #thefile = basename(subject)
  name = thefile[0:-4]
  execute('nu_correct -clob inputs/%s %s/NUC/%s' %(thefile, name, thefile))
  themax = execute('mincstats -max ' + name + '/NUC/' + thefile + ' | cut -c20-31') 	
  themin = execute('mincstats -min ' + name + '/NUC/' + thefile + ' | cut -c20-31')
  execute ('minccalc -clob %s/NUC/%s -expression "10000*(A[0]-0)/(%s-%s)" %s/NORM/%s' %(name, thefile, themax, themin, name, thefile))
  execute ('mincbet %s/NORM/%s %s/masks/%s -m' %(name, thefile, name, name))
  mask = name + '_mask.mnc'
  # face
  if image_type == 'face':
    # convert to nii
    execute("mnc2nii %s/NORM/%s %s/%s.nii" %(name, thefile, name, name))
    execute("sienax %s/%s.nii -d -o %s/sienax_output_tmp/" %(name, name, name))
    execute("gzip -d %s/sienax_output_tmp/I_stdmaskbrain_seg.nii.gz" %(name))
    execute("nii2mnc %s/sienax_output_tmp/I_stdmaskbrain_seg.nii %s/sienax_output_tmp/I_stdmaskbrain_seg.mnc")
    execute("minccalc -expression "A[0] > 0.5" I_stdmaskbrain_seg.mnc I_stdmaskbrain_seg_discrete.mnc")


    
    
    
    
    
    
      execute("minccalc -clob %s/masks/%s -expression '(-1)*A[0]' %s/masks/%s_mask_inverse.mnc" %(name, mask, name, name))
      execute('bestlinreg -clob -lsq6 -source_mask %s/masks/%s_mask_inverse.mnc -target_mask targetmask_inv.mnc %s/NORM/%s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, name, name, thefile, name, name))
  # brain
  elif image_type == 'brain':
    execute('bestlinreg -clob -lsq6 -source_mask %s/masks/%s -target_mask ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc %s/NORM/%s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, mask, name, thefile, name, name))  
  resample('%s/lin_tfiles/%s_lsq6.xfm' %(name, name), '%s/NORM/%s' %(name, thefile), '%s/output_lsq6/%s_lsq6.mnc' %(name, name))
  
  #/home/mallar/models/ICBM_nl$ Display icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc -label icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc
  return


def pairwise_reg(sourcename, targetname):
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return


def check_lsq6():  
  for subject in glob.glob('inputs/'):
    inputname = subject[7:11]
    try:
      execute('minccomplete %s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname))
    except subprocess.CalledProcessError:
      execute("qdel s2*, s3*, check*, reg*, nonlin*, s6*")
  return 


def check_lsq12():
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    #for subject2 in glob.glob('inputs/*'):
      #targetname = subject2[7:11]
      #if targetname != inputname:
        #try:
          #execute('minccomplete %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(inputname, inputname, targetname)) # check all pairwise transformation files (necessary?)
        #except subprocess.CalledProcessError:
          #execute("qdel reg*, nonlin*,s*")
          #sys.exit(1)
    try: 
      execute('mincomplete %s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)) # check for lsq12.mnc for every input
    except subprocess.CalledProcessError:
      execute("qdel reg*, nonlin*, s6*")
  try: 
    execute('minccomplete avgimages/linavg.mnc')   # check for average 
  except subprocess.CalledProcessError:
    execute("qdel reg*, nonlin*, s6*")
    #print e.output
  return  


def lsq12reg(sourcename, targetname):
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return

   
def xfmavg_inv_resample(targetname):
  execute('xfmavg -clob H*/lin_tfiles/H*_H*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  resample('lsq12avg_inverse.xfm','%s/output_lsq6/%s_lsq6.mnc' %(targetname, targetname), 'avgsize.mnc')
  return 


def lsq12reg_and_resample(sourcename):
  lsq12reg('%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename), 'avgsize.mnc', '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename))
  resample('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename), '%s/output_lsq6/%s_lsq6.mnc' %(sourcename, sourcename), '%s/timage_lsq12/%s_lsq12.mnc' %(sourcename, sourcename))
  return


def resample(xfm, inputpath, outputpath):
  execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(xfm, inputpath, outputpath))
  return 


def xfmavg_and_resample(inputname):
  execute('xfmavg -clob %s/pairwise_tfiles/* %s/pairwise_tfiles/%s.xfm' %(inputname, inputname, inputname))
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname), '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname), '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname))
  return


def mnc_avg(inputfolder,inputreg,outputname):
  execute('mincaverage -clob H0*/%s/H0*_%s.mnc avgimages/%s' %(inputfolder,inputreg,outputname))
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
  execute('/projects/utilities/xfmjoin %s/tfiles_nonlin/%s_nonlin1.xfm %s/tfiles_nonlin/%s_nonlin2.xfm %s/tfiles_nonlin/%s_nonlin3.xfm %s/tfiles_nonlin/%s_nonlin4.xfm %s/%s_merged2.xfm' %(inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname))
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
    preprocess(sys.argv[2], sys.argv[3])
  elif cmd == 'pairwise_reg':
    pairwise_reg(sys.argv[2], sys.argv[3])
  elif cmd == 'check_lsq6':
    check_lsq6()      
  elif cmd == 'check_lsq12':
    check_lsq12()
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
