Model-Building Pipeline
================================
This pipeline takes in a set of MR images and processes them (both linearly & nonlinearly) to generate the average 
population model and the voxelwise jacobian of the deformation field mapping each subject to it.

Basic configuration  
-------------------------
1. Create a directory for your project,
```
mkdir my_project
cd my_project
```
   and copy/link the following scripts into it: 
`process.py`, `pipeline.py`, `xfmjoin`, `utils.py` and `MAGetbrain` (if running you're it on scinet).

2. In `my_project`, 
```
mkdir inputs/
```

3. Copy/link all subjects into `inputs/`. 
     
	For the longitudinal analysis option, follow-up images must have the same name 	 as the respective baseline image and end in `_2.mnc`. For example, 
 * baseline image:  `H001.mnc`
 * follow-up image:  `H001_2.mnc`		

4. Copy/link the preprocessing (linear 6-parameter registration) reference image and its reference mask as `targetimage.mnc` and `targetmask.mnc`, respectively. 

  Alternatively, use the `-random_target` command line option to randomly select a subject to be the target. When using this option, ensure `targetimage.mnc` and `targetmask.mnc` do not exist within `my_project`(or else silent errors will occur).

5. For the landmark-based facial feature analysis option, copy/link the model image and its landmarks (a .tag file) into `my_project` as `face_model.mnc` and `face_tags.tag`, respectively.

Name this section
-------------------------
###### Usage: 
```
./pipeline.py [batch_system] [-options]
```
Batch system options: `local`, `sge` , `pbs`

`./pipeline.py --help` for more information regarding the options

Default stages:
`-preprocess`, `-lsq12`, `ants`, `stats` (for brain imaging)


### Example command lines:


**Comand line Examples**             | **Executes** 
-------------                        | ---------------------  
`./pipeline.py sge`                  | entire pipeline with default stages
`./pipeline.py sge -run_with -tracc` | entire pipeline with minctracc (instead of mincANTS)
`./pipeline.py sge -tracc`           | minctracc (all 6 iterations)
`./pipeline.py sge -tracc_stage 2`    | second iteration of minctracc (& will be fail if iteration 1 was not previously complete)     
`./pipeline.py sge -longitudinal`    | longitudinal analysis (with default stages for processing baseline images)
`./pipeline.py sge -longitudinal -run_with -tracc` | longitudinal analysis with minctracc for processing baseline images
`./pipeline.py sge -asymm`           | asymmetrical analysis


`./pipeline.py pbs -ants_stage` 




###### Caveats 
-------------------
All dependency names terminate with the * (asterisk) wildcard, and may in turn flag any
files and/or folders in the directory that pipeline.py is being executed. The following error may occur:
    
    Unable to run job: Script length does not match declared length.
    Exiting.

To avoid errors, remove or rename any files and/or folders with names that could be flagged by 
any of the following dependency names: 
`avgsize*`, `blurmod*`, `linavg*`, `lndmk_model*`, `nlin*`, `reg*`, `s1*`, `* s2*`, `s3*`, `s6*`, `tr*`.
        
