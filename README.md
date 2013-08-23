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
   `process.py`, `pipeline.py`, `xfmjoin`, `utils.py` and `MAGetbrain` (if you're running it on SciNet).

2. In `my_project`, 
```
mkdir inputs/
```

3. Copy/link all subjects into `inputs/`. 
   
   For the **longitudinal analysis** option, follow-up images must have the same name as the respective baseline image and end in `_2.mnc`. For example, 
    * baseline image:  `H001.mnc`
    * follow-up image: `H001_2.mnc`		

4. Copy/link the preprocessing (linear 6-parameter registration) reference image and its reference mask into               `my_project/` as `targetimage.mnc` and `targetmask.mnc`, respectively,

  Alternatively, use the `-random_target` command line option to randomly select a subject to be the target. When using this option, ensure `targetimage.mnc` and `targetmask.mnc` do not exist within `my_project`(or else silent errors will occur).

5. For the **landmark-based facial feature analysis** option, copy/link the model image and its landmarks (a .tag file) into `my_project` as `face_model.mnc` and `face_tags.tag`, respectively.


Running the pipeline 
-------------------------
#### Usage: 
```
./pipeline.py [batch_system] [-options]
```
 * Batch system options: `local`, `sge` , `pbs`

 * Default stages: `-preprocess`, `-lsq12`, `-ants`, `-stats` (for brain imaging)

 * By default, the pipeline will process all images in `inputs/`. To process only a subset of the images in `inputs/`, use the `-prefix` option and specify a sequence of one or more characters that will flag the inputs you want. For example,
```
            ./pipeline.py sge -prefix 001  
```

 will process all the inputs flagged by `inputs/*001*`.



#### Sample command lines:

> ###### Running the entire pipeline 
> * `./pipeline.py pbs` executes the entire pipeline with default stages
> * `./pipeline.py pbs -run_with -lsq12p` executes the entire pipeline with pairwise 12-parameter registrations          (overiding the default non-pairwise registration method if the number of inputs > 300)
> *  `./pipeline.py pbs -run_with -tracc ` executes the entire pipeline with minctracc (instead of mincANTS)
>
>###### Running individual stages
> * `./pipeline.py pbs -tracc ` executes nonlinear processing stage using minctracc (all six iterations) 
> * `./pipeline.py pbs -tracc_stage 3 ` executes only the third iteration of minctracc
>
>###### Running the craniofacial pipeline
> *  `./pipeline.py pbs -face` executes the entire craniofacial pipeline with default stages 
> *  `./pipeline.py pbs -preprocess -face` executes the preprocessing stage for the craniofacial structure 
> * `./pipeline.py pbs -face -run_with -tracc` executes the entire craniofacial pipeline with minctracc
> *  `./pipeline.py pbs -landmarks` executes only the landmark-based facial feature analysis stage
> *  `./pipeline.py pbs -landmarks` executes the entire craniofacial pipeline & the landmark-based facial feature        analysis option 
>
>###### Running the longitudinal analysis option
> * `./pipeline.py pbs -longitudinal` executes the longitudinal analysis (with default stages for processing baseline    images)
> *  `./pipeline.py pbs -longitudinal -run_with -tracc` executes the longitudinal analysis (using minctracc when processing baseline images)
>
>###### Running the asymmetry analysis option
> *  `./pipeline.py pbs -asymm` executes the asymmetry analysis option
>

 


### Caveats 
-------------------

All dependency names terminate with the * (asterisk) wildcard, and may in turn flag any
files and/or folders in the directory that `pipeline.py` is being executed. The following error may occur:
    
    Unable to run job: Script length does not match declared length.
    Exiting.

To avoid errors, remove or rename any files and/or folders with names that could be flagged by 
any of the following dependency names: 
`avgsize*`, `blurmod*`, `linavg*`, `lndmk_model*`, `nlin*`, `reg*`, `s1*`, `* s2*`, `s3*`, `s6*`, `tr*`.
