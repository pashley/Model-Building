Model-Building
==============

This pipeline takes in a set of MR images and processes them (both linearly & nonlinearly) to generate the average 
population model and the voxelwise jacobian of the deformation field mapping each subject to it.


Basic Operation

1.  mkdir my_project
    Create a directory for your project containing the following scripts:
       - pipeline.py
       - process.py
       - utils.py
       - xfmjoin
       - MAGetbrain (if running it on scinet)

2. mkdir my_project/inputs
   Create an "inputs" directory (within my_project)
   
3. Copy/link all input subject (minc) images to the inputs directory

4. Copy/link the target reference image and its mask as targetimage.mnc and targetmask.mnc,respectively, to my_project.  

to be continued




** Caveats **


