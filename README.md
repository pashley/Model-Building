Model-Building Pipeline
================================
-------------------------
This pipeline takes in a set of MR images and processes them (both linearly & nonlinearly) to generate the average 
population model and the voxelwise jacobian of the deformation field mapping each subject to it.

Basic Operation 
-------------------------
1. Create a directory for your project,
```
mkdir my_project
cd my_project
```
   and copy/link the following scripts into it: `process.py`, `pipeline.py`, `xfmjoin` and `utils.py`, `MAGetbrain` (if running it on scinet).

2. In `my_project`, 
```
mkdir inputs/
```

3. Copy/link all subjects into `inputs/`.  

4. Copy/link the target reference image and its mask as targetimage.mnc and targetmask.mnc,respectively, to my_project.  

to be continued



Pipeline stages: 

            Stage       
1. Preprocessing  preprocess
lsq12, lsq12n, lsq12p  [default: lsq12]
ants,tracc             [default: ants]
stats



Specialized options






** Caveats **

All dependency names terminate with the * (asterisk) wildcard, and may in turn flag any
files and/or folders in the directory that pipeline.py is being executed. 

The following error may result:
    
    Unable to run job: Script length does not match declared length.
    Exiting.

To avoid errors, remove or rename any files and/or folders with names that could be flagged by 
any of the following dependency names:
        - avgsize*
        - blurmod*
        - linavg*
        - lndmk_model*
        - nlin*
        - reg*
        - s1*
        - s2*
        - s3*
        - s6*
        - tr*
        
