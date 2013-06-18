'''
# wait for all _lsq6.mnc files
# ./pipeline_main.py -depends on ###  

count = 0
for subject in glob.glob('inputs/*'):
  count += 1



# alternative to pairwise registrations (when many inputs)
if count > 16:
  
  #targetname = random.randint(1,count)
  targetname = 2
  print "targetname == %s" % targetname
    
  if targetname < 10:
    targetname = "H00%s" % targetname
  else:
    targetname = "H0%s" % targetname

  for subject in glob.glob('H*/output_lsq6/*'):
    sourcename = subject[0:4]
    targetpath = "%s/output_lsq6/%s_lsq6.mnc" %(targetname, targetname)
    outputpath = "%s/lin_tfiles/%s_%s_lsq12.xfm" %(sourcename,sourcename,targetname)    
    if sourcename != targetname:
      if not os.path.exists('%s/lin_tfiles/%s_%s_lsq12.xfm' %(sourcename, sourcename, targetname)):
        pbs_submit('./process.py lsq12reg %s %s %s' %(subject, targetpath, outputpath))   
  if job_submitted:
    sys.exit(1)
    
  # wait for all H*_targetname_lsq12.xfm files     
  if not os.path.exists('xfmavg.xfm'):
    pbs_submit('./process.py xfmavg')
  if job_submitted:
    sys.exit(1)    
  
  # wait for average
  for subject in glob.glob('H*/output_lsq6/*'):
    inputname = subject[0:4]
    xfm = 'xfmavg.xfm'
    outputpath = '%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)
    if not os.path.exists('%s/timage_lsq12/%s_avglsq12.mnc' %(inputname, inputname)):
      pbs_submit('./process.py resample %s %s %s' %(xfm, subject, outputpath))
  if job_submitted:
    sys.exit(1)  

  # wait for H*_avglsq12.mnc of a single output
  for subject in glob.glob('H*/output_lsq6/*'):
    sourcename = subject[0:4]
    targetpath = '%s/timage_lsq12/%s_avglsq12.mnc' %(sourcename, sourcename)
    outputpath = '%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename) 
    if not os.path.exists('%s/lin_tfiles/%s_lsq12.xfm' %(sourcename, sourcename)):
      pbs_submit('./process.py lsq12reg %s %s %s' %(subject,targetpath,outputpath))
  if job_submitted:
    sys.exit(1)

  # wait for H*_lsq12.xfm of a single output  
  for subject in glob.glob('H*/output_lsq6/*'):
    inputname = subject[0:4]
    xfm = '%s/lin_tfiles/%s_lsq12.xfm' %(inputname, inputname)
    outputpath = '%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)
    if not os.path.exists('%s/timage_lsq12/%s_lsq12.mnc' %(inputname, inputname)):
      pbs_submit('./process.py resample %s %s %s' %(xfm, subject, outputpath))
  if job_submitted:
    sys.exit(1)  
'''

