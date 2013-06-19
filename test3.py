#!/usr/bin/env python
import glob
import os
from os.path import join as join, basename as basename, exists
import os
from utils import *
import sys
import random


job_submitted = False

def pbs_submit(command): 
  execute("sge_batch " + command)
  global job_submitted
  job_submitted = True
  return





#decision = raw_input("Perform: ")
#print decision

def pp():
  for subject in glob.glob('inputs/*'):
    inputname = subject[7:11]
    if not os.path.exists('%s/output_lsq6/%s_lsq6.mnc' %(inputname, inputname)):
      pbs_submit("-J s1_%s ./process.py preprocess %s" % (inputname,subject))     

  if job_submitted:
    sys.exit(1)
  return


def pairwise():
  for subject in glob.glob('inputs/*'):
    sourcename = subject[7:11]
    for subject2 in glob.glob('inputs/*'):
      targetname = subject2[7:11]
      if sourcename != targetname:
        if not os.path.exists('%s/pairwise_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
          pbs_submit("-J s2_%s_%s -H 's1_*' ./process.py pairwise_reg %s %s" %(sourcename[1:4], targetname[1:4], sourcename, targetname))
  if job_submitted:
    sys.exit(1)
  return



if __name__ == '__main__':
  cmd = sys.argv[1]
  
  if cmd == 'preprocess':
    pp()
  elif cmd == 'pairwise':
    pairwise()
   
   
def check(path,targetnum):
  targetnum = int(targetnum)  
  num = 0
  for subject in glob.glob(path):
    try:
      execute('minccomplete -e 6 %s' %subject):
    except subprocess.CalledProcessError as e: 
      print e.output
      num += 1
    
  if num != targetnum:
    execute("qdel s2*, reg*, nonlin*avg, s6*, s7*")
  return 