#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import re


# def preprocess(subject, targetimage)
# targetimage can either be a previously obtained average, a randomly selected input???, longitudinal image of same input 
def preprocess(subject, image_type):
  thefile = basename(subject)
  name = thefile[0:4]
  execute('nu_correct -clob %s %s/NUC/%s' %(subject, name, thefile))
  themax = execute('mincstats -max ' + name + '/NUC/' + thefile + ' | cut -c20-31') 	
  themin = execute('mincstats -min ' + name + '/NUC/' + thefile + ' | cut -c20-31')
  execute('minccalc -clob %s/NUC/%s -expression "10000*(A[0]-0)/(%s-%s)" %s/NORM/%s' %(name, thefile, themax, themin, name, thefile)) 
  execute('mincbet %s/NORM/%s %s/masks/%s -m' %(name, thefile, name, name))
  mask = name + '_mask.mnc'
  # craniofacial
  if image_type == 'f':
    execute("minccalc -clob %s/masks/%s -expression '(-1)*A[0]' %s/masks/%s_mask_inverse.mnc" %(name, mask, name, name))
    execute('bestlinreg -clob -lsq6 -source_mask %s/masks/%s_mask_inverse.mnc -target_mask targetmask_inv.mnc %s/NORM/%s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, name, name, thefile, name, name))
  # brain
  elif image_type == 'b':
    execute('bestlinreg -clob -lsq6 -source_mask %s/masks/%s -target_mask ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI_mask_res.mnc %s/NORM/%s ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc %s/lin_tfiles/%s_lsq6.xfm' %(name, mask, name, thefile, name, name)) 
  resample('%s/lin_tfiles/%s_lsq6.xfm' %(name, name), '%s/NORM/%s' %(name, thefile), '%s/output_lsq6/%s_lsq6.mnc' %(name, name))
  return


def pairwise_reg(sourcename, targetname):
  # CLOBBER???
  execute('bestlinreg -lsq12 %s/output_lsq6/%s_lsq6.mnc %s/output_lsq6/%s_lsq6.mnc %s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname, targetname, sourcename, sourcename, targetname))
  return


def check(path,targetnum):
  targetnum = int(targetnum)
  if len(glob.glob(path)) != targetnum:
    execute("qdel -u ashley")
    execute("qdel s2*, reg*, nonlin*avg, s6*, s7*")  
  #num = 0
  #for subject in glob.glob(path):
    #if execute('minccomplete -e 6 %s' %subject):
      #num += 1
  #if num != targetnum:
    #execute("qdel s2*, reg*, nonlin*avg, s6*, s7*")
  return 



def check_lsq12(number):
  num = int(number)
  numofpwfiles = (num -1)*num  # total number of pairwise transformation files 
  if len(glob.glob('H*/pairwise_tfiles/*_*_lsq12.xfm')) != numofpwfiles and len(glob.glob('H*/lin_tfiles/H*_H*_lsq12.xfm')) != (num - 1):
    execute("qdel reg*, check*, nonlin*avg, s6*, s7*")
  elif len(glob.glob('H*/pairwise_tfiles/*.xfm')) != (numofpwfiles + num) and len(glob.glob('H*/lin_tfiles/H*')) != (3*num -1):
    execute("qdel reg*, check*, nonlin*avg, s6*, s7*")
  elif len(glob.glob('H*/timage_lsq12/H*_lsq12.mnc')) != num:
    execute("qdel reg*, check*, nonlin*avg, s6*, s7*")
  elif not os.path.exists('avgimages/linavg.mnc'):
    execute("qdel reg*, check*, nonlin*avg, s6*, s7*")
  return  



def lsq12reg(sourcepath, targetpath, outputpath):
  execute('bestlinreg -lsq12 %s %s %s' %(sourcepath, targetpath, outputpath))
  return


def xfmavg_and_inv():
  execute('xfmavg -clob H*/lin_tfiles/H*_H*_lsq12.xfm lsq12avg.xfm')
  execute('xfminvert -clob lsq12avg.xfm lsq12avg_inverse.xfm')
  return 


def resample(xfm, inputpath, outputpath):
  execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(xfm, inputpath, outputpath))
  return 


def avg_and_resample(inputname):
  execute('xfmavg -clob %s %s' %(inputname + '/pairwise_tfiles/*', inputname + '/pairwise_tfiles/' + inputname + '.xfm'))
  resample('%s/pairwise_tfiles/%s.xfm' %(inputname, inputname), '%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname), '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname))
  #execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(inputname + '/lin_tfiles/' + inputname + '.xfm', inputname + '/output_lsq6/' + inputname + '_lsq6.mnc', inputname + '/timage_lsq12/' + inputname + '_lsq12.mnc'))
  return


def mnc_avg(inputfolder,inputreg,outputname):
  execute('mincaverage -clob H0*/%s/H0*_%s.mnc avgimages/%s' %(inputfolder,inputreg,outputname))
  return


def check_reg(sourcefolder,inputregname,targetimage):
  if len(glob.glob('H*/%s/*_%s.mnc' % (sourcefolder,inputregname))) != count and not os.path.exists('avgimages/%s' % targetimage):
    execute("qdel reg*, nonlin*avg, s6*, s7*")
  return


def nonlin_reg(inputname, sourcepath, targetimage, number, iterations):
  execute('mincANTS 3 -m PR[%s,%s,1,4] \
      --number-of-affine-iterations 10000x10000x10000x10000x10000 \
      --MI-option 32x16000 \
      --affine-gradient-descent-option 0.5x0.95x1.e-4x1.e-4 \
      --use-Histogram-Matching \
      -r Gauss[3,0] \
      -t SyN[0.5] \
      -o %s \
      -i %s' %(sourcepath, 'avgimages/' + targetimage, inputname + '/tfiles_nonlin/' + inputname + '_nonlin' + number + '.xfm', iterations))
  resample('%s/tfiles_nonlin/%s_nonlin%s.xfm' %(inputname, inputname, number), sourcepath, '%s/timages_nonlin/%s_nonlin%s.mnc' %(inputname,inputname,number))   
  #execute('mincresample -clob -transformation %s %s %s -sinc -like ~mallar/models/ICBM_nl/icbm_avg_152_t1_tal_nlin_symmetric_VI.mnc' %(inputname + '/tfiles_nonlin/' + inputname + '_nonlin' + number + '.xfm', sourcepath, inputname + '/timages_nonlin/' + inputname +'_nonlin' + number + '.mnc'))
  return
  
  
def deformation(inputname):
  execute('/projects/utilities/xfmjoin %s/tfiles_nonlin/%s_nonlin1.xfm %s/tfiles_nonlin/%s_nonlin2.xfm %s/tfiles_nonlin/%s_nonlin3.xfm %s/tfiles_nonlin/%s_nonlin4.xfm %s/%s_merged2.xfm' %(inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname))
  outputfile = open('%s/%s_merged.xfm' %(inputname,inputname), 'w')
  info = open('%s/%s_merged2.xfm' %(inputname,inputname)).read()
  outputfile.write(re.sub("= %s/" %inputname, "= ",info))
  outputfile.close()
  os.remove('%s/%s_merged2.xfm' %(inputname,inputname))
  execute('minc_displacement %s/timage_lsq12/%s_lsq12.mnc %s/%s_merged.xfm %s/final_stats/%s_grid.mnc' %(inputname, inputname, inputname, inputname, inputname, inputname))
  return
  

#def deformation(inputname):
  #execute('/projects/utilities/xfmjoin %s/tfiles_nonlin/%s_nonlin1.xfm %s/tfiles_nonlin/%s_nonlin2.xfm %s/tfiles_nonlin/%s_nonlin3.xfm %s/tfiles_nonlin/%s_nonlin4.xfm %s_merged.xfm' %(inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname, inputname))
  #execute('minc_displacement %s/timage_lsq12/%s_lsq12.mnc %s_merged.xfm %s/final_stats/%s_grid.mnc' %(inputname, inputname, inputname, inputname, inputname))
  #return


def det_and_blur(inputname):
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
  elif cmd == 'check':
    check(sys.argv[2], sys.argv[3])      
  elif cmd == 'check_lsq12':
    check_lsq12(sys.argv[2])
  elif cmd == 'lsq12reg':
    lsq12reg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'xfmavg_and_inv':
    xfmavg_and_inv()
  elif cmd == 'resample':
    resample(sys.argv[2], sys.argv[3], sys.argv[4])     
  elif cmd == 'avg_and_resample':
    avg_and_resample(sys.argv[2])
  elif cmd == 'mnc_avg':
    mnc_avg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'check_reg':
    check_reg(sys.argv[2], sys.argv[3], sys.argv[4])
  elif cmd == 'nonlin_reg':
    nonlin_reg(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6])
  elif cmd == 'deformation':
    deformation(sys.argv[2])
  elif cmd == 'det_and_blur':
    det_and_blur(sys.argv[2])


