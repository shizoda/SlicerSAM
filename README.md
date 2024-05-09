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
1. 3D Slicer を開きます．Python Console を開いて，必要なライブラリをインストールします．以下は CUDA 11.7 がセットアップされている場合の例です．
   ```
   import pip
   pip.main(["install", "tqdm", "torchio", "matplotlib", "edt",  "nibabel", "prefetch_generator", "scikit-image"])
   pip.main(["install", "torch", "torchvision", "--extra-index-url", "https://download.pytorch.org/whl/cu117"])
   ```
1. Extension Wizard を開きます．
虫眼鏡マークを押すと検索画面 (Module Finder) が開きます．`Extension Wizard` を選んで `Switch to Module` ボタンを押します．

<img src="https://github.com/shizoda/SlicerSAM/assets/34496702/1665f25f-6485-4575-be73-3596a4a1000e" width="300">

<img src="https://github.com/shizoda/SlicerSAM/assets/34496702/a537cff7-0411-4fd7-ae77-4847056811af" width="300">

1. `SlicerSAM` 内の `SlicerSAM` ディレクトリを読み込みます（内側のディレクトリ）．
`Select Extension` ボタンから `SlicerSAM` 内の `SlicerSAM` を選びます． 
<img src="https://github.com/shizoda/SlicerSAM/assets/34496702/3b276582-040b-4022-a2db-82956f8c73d7" width="500">

1. 3D Slicer を再起動したのち，`Segment Editor` に SlicerSAM が読み込まれていることを確認します．
<img src="https://github.com/shizoda/SlicerSAM/assets/34496702/ccc2e4c3-9a5d-4443-a7cd-1fd5438c2f49" width="500">
