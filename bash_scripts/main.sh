sv_python_dir=/Users/fanweikong/SimVascular/build/SimVascular-build

json_file=/Users/fanweikong/Documents/Modeling/SurfaceModeling/info2.json

model_script=/Users/fanweikong/Documents/Modeling/SurfaceModeling/main.py
registration_script=/Users/fanweikong/Documents/Modeling/SurfaceModeling/elastix_main.py
volume_mesh_script=/Users/fanweikong/Documents/Modeling/SurfaceModeling/volume_mesh_main.py

#${sv_python_dir}/sv --python -- ${model_script} --json_fn ${json_file}

dir=/Users/fanweikong/Downloads/test_ensemble_post

for file in ${dir}/*.nii.gz; do  ${sv_python_dir}/sv --python -- ${model_script} --json_fn ${json_file} --seg_name ${file##*/}; done

#conda activate elastix
#python ${registration_script} --json_fn ${json_file} --write
#conda deactivate

#${sv_python_dir}/sv --python -- ${volume_mesh_script} --json_fn ${json_file}

