# SlicerSAM

[Segment Anything Model (SAM)](https://segment-anything.com/) を 3 次元医用画像で使用できるようにした [SAM-Med3D](https://github.com/uni-medical/SAM-Med3D) の [フォーク](https://github.com/shizoda/SAM-Med3D) を，[3D Slicer](https://www.slicer.org/) から使用できるようにするツールです．

![image](https://github.com/shizoda/SlicerSAM/assets/34496702/f5e6164b-72ae-4034-bd49-5c4aba0137e9)


※以下の説明も含めて，現在作成中です．

## 使い方

### セットアップ

1. コンピュータに CUDA をセットアップします．
1. [3D Slicer をダウンロード](https://download.slicer.org/)・インストールします．
1. このレポジトリと，[SAM-Med3D のフォーク](https://github.com/shizoda/SAM-Med3D/) をクローンします．
   ```
   git clone https://github.com/shizoda/SlicerSAM.git
   cd SlicerSAM
   git clone https://github.com/shizoda/SAM-Med3D.git
   ```
1. [Prepare the Pre-trained Weights](https://github.com/shizoda/SAM-Med3D/#0-recommend-prepare-the-pre-trained-weights) に記される方法に従い，`SAM-Med3D` ディレクトリ内 `ckpt` にモデルファイル `sam_med3d.pth` を配置します．
- `SAM-Med3D` ディレクトリ内に `ckpt` ディレクトリを作ります．`ckpt` とは checkpoint の意です．
- [Google Drive](https://drive.google.com/file/d/1PFeUjlFMAppllS9x1kAWyCYUJM9re2Ub/view?usp=drive_link) から `sam_med3d.pth` をダウンロードします．SAM-Med3D の学習済みモデルです．
- `sam_med3d.pth` を `ckpt` に入れます．
1. 3D Slicer を開きます．Python Console を開いて，必要なライブラリをインストールします．
   ```
   import pip; pip.main(["install", "torch", "torchvision", "tqdm", "torchio", "matplotlib", "edt",  "nibabel", "prefetch_generator", "scikit-image"])
   ```
1. Extension Wizard を開き，SlicerSAM を読み込みます．
1. 3D Slicer を再起動したのち，Segment Editor に SlicerSAM が読み込まれていることを確認します．
