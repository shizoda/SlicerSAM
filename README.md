# SlicerSAM

Segment Anything Model (SAM) を 3 次元医用画像で使用できるようにした [SAM-Med3D](https://github.com/uni-medical/SAM-Med3D) の [フォーク](https://github.com/shizoda/SAM-Med3D) を，[3D Slicer](https://www.slicer.org/) から使用できるようにするツールです．

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
1. 3D Slicer を開きます．Python Console を開いて，必要なライブラリをインストールします．
   ```
   import pip; pip.main(["install", "torch", "torchvision", "tqdm", "torchio", "matplotlib", "edt",  "nibabel", "prefetch_generator", "scikit-image"])
   ```
1. Extension Wizard を開き，SlicerSAM を読み込みます．
