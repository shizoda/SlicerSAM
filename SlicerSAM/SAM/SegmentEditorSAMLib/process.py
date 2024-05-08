import os, sys
import numpy as np
import json

if not hasattr(np, 'float'):
    np.float = np.float32
import nibabel as nib

# SAM-Med3D\data\medical_preprocessed_mmwhs_cropped\LAc\MMWHSct\imagesTr\image.nii.gz
def setup_directories_and_files(base_dir, filename="image.nii.gz", anatomy="dummy", dataset="dummy"):
    # ディレクトリの作成
    images_dir = os.path.join(base_dir, anatomy, dataset, 'imagesTr')
    labels_dir = os.path.join(base_dir, anatomy, dataset, 'labelsTr')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    # ファイルパスの生成
    image_path = os.path.join(images_dir, filename)
    label_path = os.path.join(labels_dir, filename)

    return image_path, label_path

### 2. 画像とラベルの保存

def save_image_and_labels(image_array, label_array, image_path, label_path):
    # 画像データの保存
    image_nifti = nib.Nifti1Image(image_array, affine=np.eye(4))
    nib.save(image_nifti, image_path)

    # ラベルデータの保存
    label_nifti = nib.Nifti1Image(label_array, affine=np.eye(4))
    nib.save(label_nifti, label_path)


### 4. JSONファイルの生成

def create_json_file(base_dir, filename, image_path, label_path):
    json_path = os.path.join(base_dir, filename.replace('.nii.gz', '.json'))
    data = {
        "image": os.path.basename(image_path),
        "label": os.path.basename(label_path)
    }
    with open(json_path, 'w') as json_file:
        json.dump(data, json_file)


'''
python3 inference.py --seed 2024\
 -cp ./ckpt/sam_med3d.pth \
 -tdp ./data/medical_preprocessed_mmwhs_cropped -nc $num_points \
 --output_dir ./results  \
 --task_name infer_orig_nc$num_points
 '''

from contextlib import contextmanager
@contextmanager
def change_dir(destination):
    current_dir = os.getcwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(current_dir)


def adjust_image_orientation(image_array, inverse=False):
    if not inverse:
        # Coronal プレーンでの反転 (Y軸)
        # flipped_coronal = np.flip(image_array, 1)  # 1 はY軸を指す
        flipped_coronal = image_array
        
        # Axial が Sagittal に見えるのを修正（X軸とZ軸の入れ替え）
        adjusted_image = np.swapaxes(flipped_coronal, 0, 2)  # 0 はZ軸, 2 はX軸
        return adjusted_image
    else:
        # Inverse
        # Axial と Sagittal の軸入れ替えを元に戻す
        adjusted_image = np.swapaxes(image_array, 0, 2)  # 0 はZ軸, 2 はX軸
        
        # Coronal プレーンの反転を元に戻す
        flipped_coronal = adjusted_image # np.flip(adjusted_image, 1)  # 1 はY軸を指す
        return flipped_coronal


def processSAM3D(arr, label_array, voxel_points, samdir, tmpdir="/tmp/sam", filename="image.nii.gz", anatomy="dummy", dataset="dummy"):
    
    if samdir not in sys.path:
        sys.path.append(samdir)

    # Prepare directories and files
    image_path, label_path = setup_directories_and_files(tmpdir, filename, anatomy, dataset)
    arr = adjust_image_orientation(arr)

    # label_array = create_label_image(arr.shape, voxel_points)
    save_image_and_labels(arr, label_array, image_path, label_path)
    create_json_file(tmpdir, filename, image_path, label_path)

    # Run inference
    with change_dir(samdir):

      sys.argv = ['inference.py', '--seed', '2024', '-cp', os.path.join(samdir, 'ckpt/sam_med3d.pth'), '-tdp', tmpdir, '-nc', str(len(voxel_points)), '--output_dir', os.path.join(tmpdir, "out"), '--task_name', 'infer']
      print("Running:", sys.argv)
      import inference2
      inference2.run()

    # Load the result
    result_name = filename.replace('.nii.gz', '') + "_pred" + str(len(voxel_points)-1) + ".nii.gz"
    result_path = os.path.join(tmpdir, "out", "infer", "pred", anatomy, dataset, result_name)
    result = np.array(nib.load(result_path).dataobj).astype(np.uint8)
    result = adjust_image_orientation(result, inverse=True)

    return result

