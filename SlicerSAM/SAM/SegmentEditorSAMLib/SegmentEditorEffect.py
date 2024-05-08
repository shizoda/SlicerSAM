import logging
import os
import qt
import vtk

import slicer
from vtk.util import numpy_support

import numpy as np
from SegmentEditorEffects import *

import sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from process import processSAM3D



class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
    """This effect uses Watershed algorithm to partition the input volume"""

    def __init__(self, scriptedEffect):
        scriptedEffect.name = 'SAM'
        scriptedEffect.perSegment = False  # this effect operates on all segments at once (not on a single selected segment)
        scriptedEffect.requireSegments = True  # this effect requires segment(s) existing in the segmentation
        AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

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



    def processAndImportSegmentation(self, imageArray, voxelPoints, segmentationNode, selectedSegmentID, volumeNode):

        processedArray = processSAM3D(imageArray, voxelPoints, self.samDir, self.tempDir, "image.nii.gz")
        processedLabelMapVolumeNode = self.numpyArrayToLabelMapVolumeNode(processedArray, volumeNode)
        print("selectedSegmentID", selectedSegmentID)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(processedLabelMapVolumeNode, segmentationNode, selectedSegmentID)

    def onProcess(self):
        
        # テキストボックスからパスを取得
        self.samDir = self.samDirTextBox.text
        self.tempDir = self.tempDirTextBox.text

        volumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        imageArray = slicer.util.arrayFromVolume(volumeNode)

        rasToIJKMatrix = vtk.vtkMatrix4x4()
        volumeNode.GetRASToIJKMatrix(rasToIJKMatrix)

        voxelPoints = []
        print(voxelPoints)
        for i in range(self.fiducialNode.GetNumberOfControlPoints()):
            rasPoint = [0.0, 0.0, 0.0]
            self.fiducialNode.GetNthControlPointPositionWorld(i, rasPoint)
            voxelPoint = [0, 0, 0, 1]  # ここで 1 を追加
            rasToIJKMatrix.MultiplyPoint(rasPoint + [1], voxelPoint)  # ここで座標変換
            voxelPoint = [int(round(x)) for x in voxelPoint[:-1]]  # 最終的な座標
            voxelPoints.append(voxelPoint)

        segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
        selectedSegmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()

        segmentation = segmentationNode.GetSegmentation()
        for i in range(segmentation.GetNumberOfSegments()):
            segmentID = segmentation.GetNthSegmentID(i)
            segment = segmentation.GetSegment(segmentID)
            print("Segment ID:", segmentID, "Name:", segment.GetName())

        self.processAndImportSegmentation(imageArray, voxelPoints, segmentationNode, selectedSegmentID, volumeNode)

        # 画像データとセグメントの表示を更新
        segmentationNode.GetDisplayNode().SetVisibility2DFill(True)
        segmentationNode.GetDisplayNode().SetVisibility2DOutline(True)
        volumeNode.GetImageData().Modified()
        volumeNode.Modified()


    def setupOptionsFrame(self):
        # Select Seed button
        self.selectSeedButton = qt.QPushButton("Select Seed")
        self.selectSeedButton.setToolTip("Click to select a seed point on the image.")
        self.scriptedEffect.addOptionsWidget(self.selectSeedButton)
        self.selectSeedButton.connect('clicked()', self.onSelectSeed)

        # Process button
        self.processButton = qt.QPushButton("Process")
        self.processButton.setToolTip("Process the data at the selected point.")
        self.scriptedEffect.addOptionsWidget(self.processButton)
        self.processButton.connect('clicked()', self.onProcess)

        # Directories section
        self.setupDirectories()

    def setupDirectories(self):
        # OSに応じたデフォルトディレクトリの設定
        if os.name == 'nt':  # Windows
            homeDir = os.path.join(os.path.dirname(__file__), 'SAM-Med3D')
            tempDir = os.path.join(os.environ['TEMP'], 'sam')
        else:  # Linux and others
            homeDir = os.path.join(os.path.dirname(__file__), 'SAM-Med3D')
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
