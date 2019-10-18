# -*- coding: utf-8 -*-

import os
import glob
import functools
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
import numpy as np
import matplotlib.pyplot as plt
import SimpleITK as sitk 
from skimage.transform import resize

from utils import getTrainNLabelNames, writeIm, sample_in_range
from skimage.transform import resize
from preProcess import resample_scale, resample_spacing, cropMask
import argparse
"""
This scripts generate scaled image volumes to match the size of heart from ct and mr
The image folder should be the MMWHS folder which contains all the training images (20 per modality)
augmentation number can be changed"
"""
def blankSpaces(y_train_filenames_ct, y_train_filenames_mr):
  num = len(y_train_filenames_ct)
  ratio_mr = []
  ratio_ct = []
  for i in range(num):
    mask_ct, ratio = cropMask(sitk.GetArrayFromImage(resample_spacing(y_train_filenames_ct[i])[0]),1.)
    print(ratio)
    ratio_ct = np.concatenate((ratio_ct, ratio))
    mask_mr, ratio = cropMask(sitk.GetArrayFromImage(resample_spacing(y_train_filenames_mr[i])[0]),1.)
    print(ratio)
    ratio_mr = np.concatenate((ratio_mr, ratio))
  return ratio_ct, ratio_mr

  
def main(args):

    modality = args.modality
    data_folder = args.image_dir
    fdr_postfix = args.folder_attr
    output_data_folder = args.output
    aug_num = args.aug_num
    # TO-DO: NEED TO CHECK/FIX THIS BEFORE NEXT RUNS
    if fdr_postfix == '_train':
        ids = range(0,16)
    elif fdr_postfix =='_val':
        ids = range(16,20)
        #ids = range(0,4)

    for m in modality:
        try:
            os.makedirs(os.path.join(output_data_folder,m+fdr_postfix))
        except Exception as e: print(e)
        try:
            os.makedirs(os.path.join(output_data_folder,m+fdr_postfix+'_masks'))
        except Exception as e: print(e)
    
    filenames_dic = {}
    for m in modality:
        x_train_filenames, y_train_filenames = getTrainNLabelNames(data_folder, m)
        print("Number of training volumes %d" % len(x_train_filenames))
        print("Number of mask volumes %d" % len(y_train_filenames))
        filenames_dic[m+'_x'] = x_train_filenames
        filenames_dic[m+'_y'] = y_train_filenames

    #find the blank spaces for image volumes 
    ratios = {}
    ratios['ct'], ratios['mr'] = blankSpaces(filenames_dic['ct_y'], filenames_dic['mr_y'])

    for m in modality:
    	ratios[m] = ratios[m].reshape(int(len(ratios[m])/3),3)
    #assume uniform distribution, find the range of blank space ratios
    dim = 3
    range_adjust = [None]*dim
    for i in range(dim):
        range_adjust[i] = [np.min([np.min(ratios[m][:,i]) for m in modality]), np.max([np.max(ratios[m][:,i]) for m in modality])]
    print("The ratio of blank space found for ct and mr is: ", range_adjust)



    # Apply data augmentation so that the scale, spacing, orientation of MR and CT volumes are consistant
    
    

    def _augment(train_filenames, range_adjust, ratio, scale_factor=None, order=1):
        if scale_factor is None:
            scale_factor = np.mean([sample_in_range(range_adjust[0]), sample_in_range(range_adjust[1]), sample_in_range(range_adjust[2])]/ratio)
        sitkIm, ref_img = resample_spacing(train_filenames, order=order)
        image = resample_scale(sitkIm, ref_img, scale_factor, order)
        return image, scale_factor
      
        
    for m in modality:
      num = len(filenames_dic[m+'_x'])
      for i in ids:
          fn = os.path.join(output_data_folder, m+fdr_postfix, os.path.basename(filenames_dic[m+'_x'][i]))
          img,_ = resample_spacing(filenames_dic[m+'_x'][i], order=1)
          sitk.WriteImage(img, fn)

          fn = os.path.join(output_data_folder, m+fdr_postfix+'_masks', os.path.basename(filenames_dic[m+'_y'][i]))
          mask,_ = resample_spacing(filenames_dic[m+'_y'][i], order=0)
          sitk.WriteImage(mask, fn)
          
          for j in range(aug_num):
              mask, scale_factor = _augment(filenames_dic[m+'_y'][i], range_adjust, ratios[m][i,:], order=0)
              fn =  os.path.join(output_data_folder, m+fdr_postfix+'_masks', m+'_aug_'+str(i)+'_'+str(j)+'_label.nii.gz')
              sitk.WriteImage(mask, fn)
              img, _ = _augment(filenames_dic[m+'_x'][i], range_adjust, ratios[m][i,:], scale_factor=scale_factor, order=1)
              fn =  os.path.join(output_data_folder, m+fdr_postfix, m+'_aug_'+str(i)+'_'+str(j)+'_image.nii.gz')
              sitk.WriteImage(img, fn)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--modality', nargs='+', help='Name of the modality, mr, ct, split by space')
    parser.add_argument('--image_dir',  help='Name of the folder containing the image data')
    parser.add_argument('--output',  help='Name of the output folder')
    parser.add_argument('--folder_attr',  help='Name of the image folder _train or _val')
    parser.add_argument('--aug_num',  type=int, help='Number of augmented volumes per image')
    args = parser.parse_args()
    main(args)
