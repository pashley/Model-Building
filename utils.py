from os.path import join as join, basename as basename, exists
import os
import subprocess
import errno

def execute(command, cwd = None, shell=True, dry_run = False):
  """Spins off a subprocess to run the given command"""

  print command
  if dry_run: 
    return
  return subprocess.check_output(command, shell=shell, cwd=cwd, universal_newlines=True)

def mkdirp(*p):
    """Like mkdir -p"""
    path = os.path.join(*p)
         
    try:
      os.makedirs(path)
    except OSError as exc: 
      if exc.errno == errno.EEXIST:
        pass
      else: raise
    return path

def read_fslinfo(nii_file): 
  """Returns a dictionary of keys and values from the output of fslinfo"""

  fslinfo = execute("fslinfo %s" % nii_file)

  info = {} 
  for k,v in map(lambda x: x.split(), fslinfo.strip().split('\n')):
    info[k] = v
  return info
