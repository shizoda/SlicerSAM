import logging
import os
import qt
import vtk

import slicer
from vtk.util import numpy_support

import numpy as np
from SegmentEditorEffects import *

import sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from process import processSAM3D, adjust_image_orientation



class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
    def __init__(self, scriptedEffect):
        scriptedEffect.name = 'SAM'
        scriptedEffect.perSegment = False  # this effect operates on all segments at once
        scriptedEffect.requireSegments = True  # this effect requires segment(s) existing in the segmentation
        AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)
        self.setup_markup_nodes()

        # 属性の初期化
        self.samDir = ""  # SAMディレクトリの初期値を設定
        self.tempDir = ""  # 一時ディレクトリの初期値を設定

        self.voxelPoints = []
        self.negVoxelPoints = []


    def get_window_level_and_width(self, volumeNode):
        """ ボリュームノードからウィンドウレベルとウィンドウ幅を取得 """
        displayNode = volumeNode.GetDisplayNode()
        if not displayNode or not isinstance(displayNode, slicer.vtkMRMLScalarVolumeDisplayNode):
            raise ValueError("Invalid display node or display node is not a scalar volume display node")

        windowLevel = displayNode.GetLevel()
        windowWidth = displayNode.GetWindow()
        return windowLevel, windowWidth
    
    def normalize_image_to_255(self, imageArray, windowLevel, windowWidth):
        """ ウィンドウレベルとウィンドウ幅を使用して画像を0～255に正規化 """
        minValue = windowLevel - (windowWidth / 2.0)
        maxValue = windowLevel + (windowWidth / 2.0)

        # 正規化の公式を適用
        normalizedImage = np.clip((imageArray - minValue) * (255.0 / (maxValue - minValue)), 0, 255)
        return normalizedImage.astype(np.uint8)

    def clone(self):
        # It should not be necessary to modify this method
        import qSlicerSegmentationsEditorEffectsPythonQt as effects
        clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
        clonedEffect.setPythonSource(__file__.replace('\\', '/'))
        return clonedEffect

    def icon(self):
        # It should not be necessary to modify this method
        iconPath = os.path.join(os.path.dirname(__file__), 'SegmentEditorEffect.png')
        if os.path.exists(iconPath):
            return qt.QIcon(iconPath)
        return qt.QIcon()

    def helpText(self):
        return """Existing segments are grown to fill the image.
The effect is different from the Grow from seeds effect in that smoothness of structures can be defined, which can prevent leakage.
To segment a single object, create a segment and paint inside and create another segment and paint outside on each axis.
"""

    def onSelectSeed(self):
        # 以前に作成したフィデューシャルノードがあればそれを使用し、なければ新規作成
        self.fiducialNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsFiducialNode")
        if not self.fiducialNode:
            self.fiducialNode = slicer.vtkMRMLMarkupsFiducialNode()
            slicer.mrmlScene.AddNode(self.fiducialNode)
            self.fiducialNode.CreateDefaultDisplayNodes()  # これが重要
            self.fiducialNode.SetName("SelectedPoints")

        # インタラクションノードの設定を変更して、マークアッププレースメントモードに設定
        interactionNode = slicer.app.applicationLogic().GetInteractionNode()
        interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        interactionNode.SetPlaceModePersistence(1)  # これを設定することで、モードが保持される

        # フィデューシャルノードをアクティブに設定
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActivePlaceNodeID(self.fiducialNode.GetID())


    def handlePointPlaced(self, caller, event):
        self.selectSeedButton.enabled = True  # Re-enable the button
        node = caller.GetNodeByID(event)
        if isinstance(node, slicer.vtkMRMLMarkupsFiducialNode):
            coord = [0.0, 0.0, 0.0]
            node.GetNthFiducialPosition(0, coord)
            self.lastClickedPoint = coord
            # Set the crosshair to the selected point in 3D
            crosshairNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLCrosshairNode")
            if not crosshairNode:
                crosshairNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLCrosshairNode")
                slicer.mrmlScene.AddNode(crosshairNode)
            crosshairNode.SetCrosshairRAS(coord)
            crosshairNode.SetCrosshairThickness(slicer.vtkMRMLCrosshairNode.ThreeD)
            slicer.mrmlScene.RemoveObserver(self.pointPlacedObserver)

    def numpyArrayToLabelMapVolumeNode(self, array, volumeNode, name="ProcessedLabelMap"):
        
        """ NumPy array を vtkMRMLLabelMapVolumeNode に変換する関数 """
        vtk_data_array = numpy_support.numpy_to_vtk(num_array=array.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        image_data = vtk.vtkImageData()
        image_data.SetDimensions(array.shape[2], array.shape[1], array.shape[0])
        image_data.GetPointData().SetScalars(vtk_data_array)

        labelMapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", name)
        labelMapVolumeNode.SetAndObserveImageData(image_data)

        # 元のボリュームノードからスペーシング、原点をコピー
        labelMapVolumeNode.SetSpacing(volumeNode.GetSpacing())
        labelMapVolumeNode.SetOrigin(volumeNode.GetOrigin())

        # 方向を設定
        directions =  [[1.0, 0, 0], [0, 1, 0], [0, 0, 1]]
        labelMapVolumeNode.SetIJKToRASDirections(directions)

        return labelMapVolumeNode

    def setup_markup_nodes(self):
        # Foreground points setup
        self.foregroundNode = slicer.mrmlScene.GetFirstNodeByName("ForegroundPoints")
        if not self.foregroundNode:
            self.foregroundNode = slicer.vtkMRMLMarkupsFiducialNode()
            self.foregroundNode.SetName("ForegroundPoints")
            slicer.mrmlScene.AddNode(self.foregroundNode)
            self.foregroundNode.CreateDefaultDisplayNodes()
            self.foregroundNode.GetDisplayNode().SetColor(0, 1, 1)  # Cyan
            self.foregroundNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onPointAdded)

        # Background points setup
        self.backgroundNode = slicer.mrmlScene.GetFirstNodeByName("BackgroundPoints")
        if not self.backgroundNode:
            self.backgroundNode = slicer.vtkMRMLMarkupsFiducialNode()
            self.backgroundNode.SetName("BackgroundPoints")
            slicer.mrmlScene.AddNode(self.backgroundNode)
            self.backgroundNode.CreateDefaultDisplayNodes()
            self.backgroundNode.GetDisplayNode().SetColor(0.6, 0.3, 0.1)  # Brown
            self.backgroundNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onPointAdded)

        self.foregroundNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onPointAdded)
        self.backgroundNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent, self.onPointAdded)
        
    def onPointAdded(self, caller, event):
        
        pointIndex = caller.GetNumberOfControlPoints() - 1

        # import pdb; pdb.set_trace()
        if "Foreground" in caller.GetName():
            pointName = f"Fore_{pointIndex + 1}"
            caller.SetNthControlPointLabel(pointIndex, pointName)
            caller.GetDisplayNode().SetSelectedColor(0, 1, 1)  # Cyan
        elif "Background" in caller.GetName():
            pointName = f"Back_{pointIndex + 1}"
            caller.SetNthControlPointLabel(pointIndex, pointName)
            caller.GetDisplayNode().SetSelectedColor(0.6, 0.3, 0.1)  # Brown


    def create_label_image(self, arr_shape):
        """前景と背景の点を使用してラベル画像を生成"""
        label_array = np.zeros(arr_shape, dtype=np.uint8)

        print("Foreground points:", self.voxelPoints)
        print("Background points:", self.negVoxelPoints)


        # Foreground points
        for voxelPoint in self.voxelPoints:
            if all(0 <= p < s for p, s in zip(voxelPoint, arr_shape)):  # 座標が画像範囲内であることを確認
                label_array[tuple(voxelPoint)] = 1  # 前景を1でラベル付け
            else:
                print("Foreground point is out of image range:", voxelPoint)

        # Background points
        for voxelPoint in self.negVoxelPoints:
            if all(0 <= p < s for p, s in zip(voxelPoint, arr_shape)):  # 座標が画像範囲内であることを確認
                label_array[tuple(voxelPoint)] = 100  # 背景を100でラベル付け
            else:
                print("Background point is out of image range:", voxelPoint)

        return label_array


    def processAndImportSegmentation(self, imageArray, labelArray, voxelPoints, segmentationNode, selectedSegmentID, volumeNode):

        processedArray = processSAM3D(imageArray, labelArray, voxelPoints, self.samDir, self.tempDir, "image.nii.gz")
        processedLabelMapVolumeNode = self.numpyArrayToLabelMapVolumeNode(processedArray, volumeNode)
        print("selectedSegmentID", selectedSegmentID)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(processedLabelMapVolumeNode, segmentationNode, selectedSegmentID)

    def convert_ras_to_ijk(self, rasPoint, origin, spacing):
        voxelPoint = [0, 0, 0, 1]
        self.rasToIJKMatrix.MultiplyPoint(rasPoint + [1], voxelPoint)

        '''
        ijkPoint = [
            (voxelPoint[0] - origin[0]) / spacing[0],
            (voxelPoint[1] - origin[1]) / spacing[1],
            (voxelPoint[2] - origin[2]) / spacing[2]
        ]
        return [int(round(x)) for x in ijkPoint]
        '''
        return [int(round(x)) for x in voxelPoint[:3]]
    
    def onProcess(self):  
        
        # テキストボックスからパスを取得
        self.samDir = self.samDirTextBox.text
        self.tempDir = self.tempDirTextBox.text

        volumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        imageArray = slicer.util.arrayFromVolume(volumeNode)

        self.rasToIJKMatrix = vtk.vtkMatrix4x4()
        volumeNode.GetRASToIJKMatrix(self.rasToIJKMatrix)


        # スペーシングとオリジンを取得
        spacing = volumeNode.GetSpacing()
        origin = volumeNode.GetOrigin()
        print(f"Spacing: {spacing}, Origin: {origin}")


        # 前景と背景のボクセルポイントリストを初期化
        self.voxelPoints = []
        self.negVoxelPoints = []

        # Foreground points
        if self.foregroundNode:
            for i in range(self.foregroundNode.GetNumberOfControlPoints()):
                rasPoint = [0.0, 0.0, 0.0]
                self.foregroundNode.GetNthControlPointPositionWorld(i, rasPoint)
                voxelPoint = self.convert_ras_to_ijk(rasPoint, origin, spacing)
                self.voxelPoints.append(voxelPoint)

        # Background points
        if self.backgroundNode:
            for i in range(self.backgroundNode.GetNumberOfControlPoints()):
                rasPoint = [0.0, 0.0, 0.0]
                self.backgroundNode.GetNthControlPointPositionWorld(i, rasPoint)
                voxelPoint = self.convert_ras_to_ijk(rasPoint, origin, spacing)
                self.negVoxelPoints.append(voxelPoint)

        segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
        selectedSegmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()

        windowLevel, windowWidth = self.get_window_level_and_width(volumeNode)
        print("windowLevel", windowLevel, "windowWidth", windowWidth)
        imageArray = self.normalize_image_to_255(imageArray, windowLevel, windowWidth)

        imageArray = adjust_image_orientation(imageArray, inverse=False)
        try:
          label_array = self.create_label_image(imageArray.shape)
        except Exception as e:
          import traceback; traceback.print_exc()          
          import pdb; pdb.set_trace()

        self.processAndImportSegmentation(imageArray, label_array, self.voxelPoints, segmentationNode, selectedSegmentID, volumeNode)

        # 画像データとセグメントの表示を更新
        segmentationNode.GetDisplayNode().SetVisibility2DFill(True)
        segmentationNode.GetDisplayNode().SetVisibility2DOutline(True)
        volumeNode.GetImageData().Modified()
        volumeNode.Modified()


    def setupOptionsFrame(self):
        # フォアグラウンド点選択ボタン
        self.selectForegroundButton = qt.QPushButton("Select Foreground Seed")
        self.selectForegroundButton.setToolTip("Select foreground points on the image.")
        self.scriptedEffect.addOptionsWidget(self.selectForegroundButton)
        self.selectForegroundButton.connect('clicked(bool)', lambda: self.onSelectSeed('Foreground'))

        # バックグラウンド点選択ボタン
        self.selectBackgroundButton = qt.QPushButton("Select Background Seed")
        self.selectBackgroundButton.setToolTip("Select background points on the image.")
        self.scriptedEffect.addOptionsWidget(self.selectBackgroundButton)
        self.selectBackgroundButton.connect('clicked(bool)', lambda: self.onSelectSeed('Background'))

        # Process button
        self.processButton = qt.QPushButton("Process")
        self.processButton.setToolTip("Process the data at the selected point.")
        self.scriptedEffect.addOptionsWidget(self.processButton)
        self.processButton.connect('clicked()', self.onProcess)

        # TextBox にデフォルトディレクトリを設定
        # self.samDirTextBox.setText(self.samDir)
        # self.tempDirTextBox.setText(self.tempDir)

        # Directories section
        self.setupDirectories()


    def onSelectSeed(self, nodeType):
        # nodeType は 'Foreground' または 'Background' とする
        nodeName = f"{nodeType}Points"
        fiducialNode = slicer.mrmlScene.GetFirstNodeByName(nodeName)
        if not fiducialNode:
            fiducialNode = slicer.vtkMRMLMarkupsFiducialNode()
            fiducialNode.SetName(nodeName)
            slicer.mrmlScene.AddNode(fiducialNode)
            fiducialNode.CreateDefaultDisplayNodes()

        # インタラクションノードの設定をマークアッププレースメントモードに設定
        interactionNode = slicer.app.applicationLogic().GetInteractionNode()
        interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        interactionNode.SetPlaceModePersistence(1)

        # 選択されたマークアップノードをアクティブに設定
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActivePlaceNodeID(fiducialNode.GetID())



    def setupDirectories(self):
        # OSに応じたデフォルトディレクトリの設定
        homeDir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", 'SAM-Med3D'))
        if os.name == 'nt':  # Windows
            tempDir = os.path.join(os.environ['TEMP'], 'sam')
        else:  # Linux and others
            tempDir = os.path.join('/tmp', 'sam')

        # SAM Directory TextBox
        self.samDirLabel = qt.QLabel("SAM Directory:")
        self.scriptedEffect.addOptionsWidget(self.samDirLabel)
        self.samDirTextBox = qt.QLineEdit(homeDir)
        self.samDirTextBox.setToolTip("Set the SAM directory.")
        self.scriptedEffect.addOptionsWidget(self.samDirTextBox)

        # Temp Directory TextBox
        self.tempDirLabel = qt.QLabel("Temp Directory:")
        self.scriptedEffect.addOptionsWidget(self.tempDirLabel)
        self.tempDirTextBox = qt.QLineEdit(tempDir)
        self.tempDirTextBox.setToolTip("Set the temporary directory.")
        self.scriptedEffect.addOptionsWidget(self.tempDirTextBox)
