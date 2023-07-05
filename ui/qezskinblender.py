import os
import webbrowser

from Qt import QtCore, QtWidgets, QtGui
from dcc import fnscene, fnnode, fnmesh, fnskin, fnnotify
from dcc.ui import quicwindow
from .dialogs import qeditinfluencesdialog, qeditweightsdialog
from .models import qinfluenceitemfiltermodel
from ..libs import skinutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def validate(func):
    """
    Returns a wrapper that validates functions against the UI before executing.
    This will help reduce the amount of conditions needed when we're not in edit mode.

    :type func: Callable
    :rtype: Callable
    """

    def wrapper(*args, **kwargs):

        window = args[0]  # type: QEzSkinBlender

        if window.skin.isValid():

            return func(*args, **kwargs)

        else:

            return

    return wrapper


class QEzSkinBlender(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` that manipulates skin weights.
    """

    # region Dunderscores
    __presets__ = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)
    __sign__ = (1.0, -1.0)

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QEzSkinBlender, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._scene = fnscene.FnScene()
        self._skin = fnskin.FnSkin()
        self._currentInfluence = None
        self._softSelection = {}
        self._selection = []
        self._vertexWeights = {}
        self._weights = {}
        self._precision = False
        self._blendByDistance = False
        self._selectShell = False
        self._slabOption = 0
        self._search = ''
        self._mirrorAxis = 0
        self._mirrorTolerance = 1e-3
        self._clipboard = None
        self._notifies = fnnotify.FnNotify()

        # Declare public variables
        #
        self.fileMenu = None
        self.saveWeightsAction = None
        self.loadWeightsAction = None

        self.editMenu = None
        self.copyWeightsAction = None
        self.pasteWeightsAction = None
        self.pasteAverageWeightsAction = None
        self.copySkinAction = None
        self.pasteSkinAction = None
        self.blendVerticesAction = None
        self.blendBetweenVerticesAction = None
        self.blendByDistanceAction = None
        self.resetIntermediateObjectAction = None
        self.resetBindPreMatricesAction = None

        self.settingsMenu = None
        self.xAction = None
        self.yAction = None
        self.zAction = None
        self.setMirrorToleranceAction = None

        self.helpMenu = None
        self.usingEzSkinBlenderAction = None

        self.envelopeGroupBox = None
        self.envelopePushButton = None

        self.skinWidget = None
        self.skinSplitter = None

        self.influenceWidget = None
        self.influenceHeader = None
        self.searchLineEdit = None
        self.influenceTable = None
        self.influenceItemModel = None
        self.influenceItemFilterModel = None
        self.influenceInteropWidget = None
        self.addInfluencePushButton = None
        self.removeInfluencePushButton = None
        self.influenceFooter = None

        self.weightWidget = None
        self.weightHeader = None
        self.weightTable = None
        self.weightItemModel = None
        self.weightItemFilterModel = None
        self.modeWidget = None
        self.precisionCheckBox = None
        self.selectShellCheckBox = None
        self.optionsWidget = None
        self.mirrorWidget = None
        self.mirrorPushButton = None
        self.pullPushButton = None
        self.slabDropDownButton = None
        self.weightPresetWidget = None
        self.weightPresetPushButton1 = None
        self.weightPresetPushButton2 = None
        self.weightPresetPushButton3 = None
        self.weightPresetPushButton4 = None
        self.weightPresetPushButton5 = None
        self.weightPresetPushButton6 = None
        self.weightPresetPushButton7 = None
        self.setWeightLabel = None
        self.setWeightSpinBox = None
        self.setWeightPushButton1 = None
        self.setWeightPushButton2 = None
        self.incrementWeightLabel = None
        self.incrementWeightSpinBox = None
        self.incrementWeightWidget = None
        self.incrementWeightPushButton1 = None
        self.incrementWeightPushButton2 = None
        self.scaleWeightLabel = None
        self.scaleWeightSpinBox = None
        self.scaleWeightWidget = None
        self.scaleWeightPushButton1 = None
        self.scaleWeightPushButton2 = None
        self.weightFooter = None

        self.weightTableMenu = None
        self.selectAffectedVerticesAction = None

        self.slabMenu = None
        self.closestPointAction = None
        self.nearestNeighbourAction = None
        self.alongNormalAction = None
        self.slabActionGroup = None
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Getter method that returns the scene function set.

        :rtype: fnscene.FnScene
        """

        return self._scene

    @property
    def skin(self):
        """
        Getter method that returns the skin function set.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @property
    def precision(self):
        """
        Getter method that returns the precision flag.

        :rtype: bool
        """

        return self._precision

    @property
    def mirrorAxis(self):
        """
        Getter method used to retrieve the current mirror axis.

        :rtype: int
        """

        return self._mirrorAxis

    @property
    def slabOption(self):
        """
        Getter method that returns the current slab option.

        :rtype: int
        """

        return self._slabOption

    @property
    def blendByDistance(self):
        """
        Getter method that returns the blend by distance flag.

        :rtype: bool
        """

        return self._blendByDistance

    @property
    def selectShell(self):
        """
        Getter method that returns a flag that indicates if shells should be selected.

        :rtype: bool
        """

        return self._selectShell

    @property
    def mirrorTolerance(self):
        """
        Getter method that returns the mirror tolerance.

        :rtype: float
        """

        return self._mirrorTolerance

    @mirrorTolerance.setter
    def mirrorTolerance(self, mirrorTolerance):
        """
        Setter method that updates the mirror tolerance.

        :type mirrorTolerance: float
        :rtype: None
        """

        self._mirrorTolerance = mirrorTolerance

    @property
    def search(self):
        """
        Getter method that returns the search string.

        :rtype: str
        """

        return self._search
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzSkinBlender, self).postLoad(*args, **kwargs)

        # Initialize influence item model
        #
        self.influenceItemModel = QtGui.QStandardItemModel(parent=self.influenceTable)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Name'])

        self.influenceItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.influenceTable)
        self.influenceItemFilterModel.setObjectName('influenceItemFilterModel')
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)

        self.influenceTable.setModel(self.influenceItemFilterModel)
        self.influenceTable.selectionModel().selectionChanged.connect(self.on_influenceSelectionModel_selectionChanged)
        
        # Initialize weight item model
        #
        self.weightItemModel = QtGui.QStandardItemModel(parent=self.weightTable)
        self.weightItemModel.setObjectName('weightItemModel')
        self.weightItemModel.setHorizontalHeaderLabels(['Name', 'Weight'])

        self.weightItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.weightTable)
        self.weightItemFilterModel.setObjectName('weightItemFilterModel')
        self.weightItemFilterModel.setSourceModel(self.weightItemModel)

        self.weightTable.setModel(self.weightItemFilterModel)

        # Create weight table context menu
        #
        self.weightTableMenu = QtWidgets.QMenu(parent=self.weightTable)
        self.weightTableMenu.setObjectName('weightTableMenu')

        self.selectAffectedVerticesAction = QtWidgets.QAction('&Select Affected Vertices', self.weightTableMenu)
        self.selectAffectedVerticesAction.setObjectName('selectAffectedVerticesAction')
        self.selectAffectedVerticesAction.triggered.connect(self.on_selectAffectedVerticesAction_triggered)

        self.weightTableMenu.addActions([self.selectAffectedVerticesAction])

        # Set table buddies
        #
        self.influenceTable.setBuddy(self.weightTable)
        self.weightTable.setBuddy(self.influenceTable)

        # Create slab button context menu
        #
        self.slabMenu = QtWidgets.QMenu(parent=self.slabDropDownButton)
        self.slabMenu.setObjectName('slabMenu')

        self.closestPointAction = QtWidgets.QAction('&Closest Point', self.slabMenu)
        self.closestPointAction.setObjectName('closestPointAction')
        self.closestPointAction.setCheckable(True)
        self.closestPointAction.setChecked(True)

        self.nearestNeighbourAction = QtWidgets.QAction('&Nearest Neighbour', self.slabMenu)
        self.nearestNeighbourAction.setObjectName('nearestNeighbourAction')
        self.nearestNeighbourAction.setCheckable(True)

        self.alongNormalAction = QtWidgets.QAction('&Along Normal', self.slabMenu)
        self.alongNormalAction.setObjectName('alongNormalAction')
        self.alongNormalAction.setCheckable(True)

        self.slabActionGroup = QtWidgets.QActionGroup(self.slabMenu)
        self.slabActionGroup.setObjectName('slabActionGroup')
        self.slabActionGroup.setExclusive(True)
        self.slabActionGroup.addAction(self.closestPointAction)
        self.slabActionGroup.addAction(self.nearestNeighbourAction)
        self.slabActionGroup.addAction(self.alongNormalAction)

        self.slabMenu.addActions([self.closestPointAction, self.nearestNeighbourAction, self.alongNormalAction])

        self.slabDropDownButton.setMenu(self.slabMenu)

        # Assign button group ids
        #
        self.mirrorWeightButtonGroup.setId(self.mirrorPushButton, 0)
        self.mirrorWeightButtonGroup.setId(self.pullPushButton, 1)

        self.weightPresetButtonGroup.setId(self.weightPresetPushButton1, 0)  # 0.0
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton2, 1)  # 0.1
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton3, 2)  # 0.25
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton4, 3)  # 0.5
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton5, 4)  # 0.75
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton6, 5)  # 0.9
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton7, 6)  # 1.0

        self.incrementWeightButtonGroup.setId(self.incrementWeightPushButton1, 0)  # +
        self.incrementWeightButtonGroup.setId(self.incrementWeightPushButton2, 1)  # -

        self.scaleWeightButtonGroup.setId(self.scaleWeightPushButton1, 0)  # +
        self.scaleWeightButtonGroup.setId(self.scaleWeightPushButton2, 1)  # -

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QEzSkinBlender, self).saveSettings(settings)

        # Save user settings
        #
        settings.setValue('editor/mirrorAxis', self.mirrorAxis)
        settings.setValue('editor/mirrorTolerance', self.mirrorTolerance)
        settings.setValue('editor/blendByDistance', int(self.blendByDistance))
        settings.setValue('editor/slabOption', self.slabOption)

    def loadSettings(self, settings):
        """
        Loads the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QEzSkinBlender, self).loadSettings(settings)

        # Load user settings
        #
        mirrorAxis = int(settings.value('editor/mirrorAxis', defaultValue=0))
        self.mirrorAxisActionGroup.actions()[mirrorAxis].setChecked(True)

        blendByDistance = bool(settings.value('editor/blendByDistance', defaultValue=0))
        self.blendByDistanceAction.setChecked(blendByDistance)

        slabOption = int(settings.value('editor/slabOption', defaultValue=0))
        self.slabActionGroup.actions()[slabOption].setChecked(True)

        self.mirrorTolerance = float(settings.value('editor/mirrorTolerance', defaultValue='1e-3'))

    def selection(self):
        """
        Returns the vertex indices from the active selection.

        :rtype: List[int]
        """

        return list(self._softSelection.keys())

    def softSelection(self):
        """
        Returns the soft values from the active selection.

        :rtype: Dict[int, float]
        """

        return self._softSelection

    def vertexWeights(self):
        """
        Returns the vertex weights from the active selection.

        :rtype: Dict[int, Dict[int, float]]
        """

        return self._vertexWeights

    def weights(self):
        """
        Returns the averaged vertex weights from the active selection.

        :rtype: Dict[int, float]
        """

        return self._weights

    def currentInfluence(self):
        """
        Returns the current influence ID.

        :rtype: int
        """

        return self._currentInfluence

    def sourceInfluences(self):
        """
        Returns the source influences IDs to redistribute from.
        This value changes depending on whether the user is in precision mode.

        :rtype: List[int]
        """

        # Get selected rows
        #
        selectedRows = self.weightTable.selectedRows()
        numSelected = len(selectedRows)

        if numSelected == 0:

            raise TypeError('sourceInfluences() expects at least 1 selected influence!')

        # Check if tool is in lazy mode
        #
        influenceIds = []

        if self.precision:

            # Remove target influence if in source
            #
            influenceIds = selectedRows
            currentInfluence = self.currentInfluence()

            if currentInfluence in influenceIds:

                influenceIds.remove(currentInfluence)

        else:

            influenceIds = [x for x in self.weightItemFilterModel.activeInfluences() if x not in selectedRows]

        # Return influence ids
        #
        log.debug('Source Influences: %s' % influenceIds)
        return influenceIds

    @validate
    def copyWeights(self):
        """
        Copies the skin weights from the current skin.

        :rtype: None
        """

        self.skin.copyWeights()

    @validate
    def pasteWeights(self, average=False):
        """
        Pastes the internal weights to the current skin.

        :type average: bool
        :rtype: None
        """

        # Check if weights should be averaged
        #
        if average:

            self.skin.pasteAveragedWeights()

        else:

            self.skin.pasteWeights()

        # Invalidate weights
        #
        self.invalidateWeights()

    @validate
    def slabPasteWeights(self):
        """
        Slab pastes the active component selection.

        :rtype: None
        """

        self.skin.slabPasteWeights(self.selection(), mode=self.slabOption)
        self.invalidateWeights()

    def copySkin(self):
        """
        Copies the skin from the selected mesh.

        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.scene.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount == 0:

            log.warning('Invalid selection!')
            return

        # Check if selection is valid
        #
        skin = fnskin.FnSkin()
        success = skin.trySetObject(selection[0])

        if success:

            self._clipboard = skinutils.cacheSkin(skin)

        else:

            log.warning('Invalid skin selected!')

    def pasteSkin(self):
        """
        Pastes the internal skin to the selected mesh.

        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.scene.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount == 0:

            log.warning('Invalid selection!')
            return

        # Check if selection and clipboard are valid
        #
        mesh = fnmesh.FnMesh()
        success = mesh.trySetObject(selection[0])

        if success and self._clipboard is not None:

            self._clipboard.applySkin(mesh)

        else:

            log.warning('Invalid mesh selected!')

    @validate
    def blendVertices(self):
        """
        Blends the active component selection.

        :rtype: None
        """

        self.skin.blendVertices(self.selection())
        self.invalidateWeights()

    @validate
    def blendBetweenVertices(self):
        """
        Blends between the active selection pairs.

        :rtype: None
        """

        self.skin.blendBetweenVertices(self.selection(), blendByDistance=self.blendByDistance)
        self.invalidateWeights()

    @validate
    def mirrorWeights(self, pull=False):
        """
        Mirrors the active component selection.

        :type pull: bool
        :rtype: None
        """

        # Mirror vertex weights
        #
        vertexWeights = self.skin.mirrorVertexWeights(
            self.selection(),
            pull=pull,
            axis=self.mirrorAxis,
            tolerance=self.mirrorTolerance
        )

        self.skin.applyVertexWeights(vertexWeights)

        # Check if active selection should be reset
        #
        resetActiveSelection = self.resetActiveSelectionAction.isChecked()

        if resetActiveSelection:

            self.skin.setSelection(list(vertexWeights.keys()))

        else:

            self.invalidateWeights()

    @validate
    def selectAffectedVertices(self):
        """
        Selects the vertices associated with current weight table selection.

        :rtype: None
        """

        # Get selected rows
        #
        selectedRows = self.weightTable.selectedRows()

        # Update active selection
        #
        selection = self.skin.getVerticesByInfluenceId(*selectedRows)
        self.skin.setSelection(selection)

    def fillItemModel(self, model, rowCount, columnCount):
        """
        Fills the supplied model with standard items.

        :type model: QtGui.QStandardItemModel
        :type rowCount: int
        :type columnCount: int
        :rtype: None
        """

        for row in range(model.rowCount(), rowCount, 1):

            model.setVerticalHeaderItem(row, QtGui.QStandardItem(str(row)))

            for column in range(columnCount):

                model.setItem(row, column, QtGui.QStandardItem(''))

    @validate
    def invalidateInfluences(self):
        """
        Invalidates the influence item model.

        :rtype: None
        """

        # Fill item model
        #
        influences = self.skin.influences()
        maxInfluenceId = influences.lastIndex()
        rowCount = maxInfluenceId + 1

        self.fillItemModel(self.influenceItemModel, rowCount, 1)

        # Iterate through influences
        #
        for i in range(rowCount):

            # Get influence name
            #
            influence = influences[i]
            name = ''

            if influence is not None:

                name = influence.name()

            # Update item data
            #
            item = self.influenceItemModel.item(i)
            item.setText(name)
            item.setTextAlignment(QtCore.Qt.AlignCenter)

    @validate
    def invalidateSelection(self):
        """
        Invalidates the internal vertex selection.

        :rtype: None
        """

        # Check if skin is partially selected
        #
        if self.skin.isPartiallySelected():

            self._softSelection = self.skin.softSelection()
            self._selection = list(self._softSelection.keys())

            self.invalidateWeights()

        else:

            log.debug('No selection changes detected...')

    @validate
    def invalidateWeights(self, *args, **kwargs):
        """
        Invalidates the weight item model.

        :rtype: None
        """

        # Fill item model
        #
        influences = self.skin.influences()
        maxInfluenceId = influences.lastIndex()
        rowCount = maxInfluenceId + 1

        self.fillItemModel(self.weightItemModel, rowCount, 2)

        # Get vertex weights
        #
        self._vertexWeights = self.skin.vertexWeights(*self._selection)

        if len(self._vertexWeights) > 0:

            self._weights = self.skin.averageWeights(*list(self._vertexWeights.values()))

        else:

            self._weights = {}

        # Iterate through influences
        #
        for i in range(maxInfluenceId + 1):

            # Get influence name and weight
            #
            influence = influences[i]

            name = ''
            weight = self._weights.get(i, None)

            if influence is not None:

                name = influence.name()

            # Update item data
            #
            item1 = self.weightItemModel.item(i)
            item1.setText(name)
            item1.setTextAlignment(QtCore.Qt.AlignCenter)

            item2 = self.weightItemModel.item(i, column=1)
            item2.setText(str(round(weight, 2)) if weight is not None else '')
            item2.setTextAlignment(QtCore.Qt.AlignCenter)

        # Invalidate vertex colours
        #
        self.weightItemFilterModel.invalidateFilter()
        self.invalidateColors()

    @validate
    def invalidateColors(self, *args, **kwargs):
        """
        Invalidates the vertex color display.

        :rtype: None
        """

        self.skin.refreshColors()
    # endregion

    # region Callbacks
    def activeSelectionChanged(self, *args, **kwargs):
        """
        Callback method used to invalidate the active selection.

        :rtype: None
        """

        self.invalidateSelection()

    def undoBufferChanged(self, *args, **kwargs):
        """
        Callback method used to invalidate the display colors.

        :rtype: None
        """

        self.invalidateWeights()
    # endregion

    # region Events
    def closeEvent(self, event):
        """
        Event method called after the window has been closed.

        :type event: QtGui.QCloseEvent
        :rtype: None
        """

        # Exit envelope mode
        #
        if self.envelopePushButton.isChecked():

            self.envelopePushButton.setChecked(False)

        # Call parent method
        #
        super(QEzSkinBlender, self).closeEvent(event)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_envelopePushButton_toggled(self, checked):
        """
        Slot method for the envelopePushButton's `toggled` signal.
        Toggles the edit envelope mode.

        :type checked: bool
        :rtype: None
        """

        # Check if envelope is checked
        #
        sender = self.sender()

        if checked:

            # Evaluate active selection
            # If nothing is selected then uncheck button
            #
            selection = self.scene.getActiveSelection()
            selectionCount = len(selection)

            if selectionCount == 0:

                sender.setChecked(False)
                return

            # Try and set object
            # If selected node is invalid then exit envelope mode
            #
            success = self.skin.trySetObject(selection[0])

            if not success:

                sender.setChecked(False)
                return

            # Add scene notifies
            #
            self._notifies.addSelectionChangedNotify(self.activeSelectionChanged)
            self._notifies.addUndoNotify(self.undoBufferChanged)
            self._notifies.addRedoNotify(self.undoBufferChanged)

            # Display vertex colors
            #
            self.skin.showColors()

            # Invalidate item models
            #
            self.invalidateInfluences()
            self.invalidateSelection()
            self.influenceTable.selectFirstRow()

        else:

            # Clear notifies
            #
            self._notifies.clear()

            # Reset skin function set
            #
            if self.skin.isValid():

                self.skin.hideColors()
                self.skin.resetObject()

            # Reset item models
            #
            self.influenceItemModel.setRowCount(0)
            self.weightItemModel.setRowCount(0)

    @QtCore.Slot(bool)
    def on_saveWeightsAction_triggered(self, checked=False):
        """
        Slot method for the saveWeightsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.scene.getActiveSelection()
        selectionCount = len(selection)

        skin = fnskin.FnSkin()

        if selectionCount == 0:

            log.warning('Invalid selection!')
            return

        elif selectionCount == 1:

            # Try and initialize skin interface
            #
            success = skin.trySetObject(selection[0])

            if not success:

                log.warning('Invalid selection...')
                return

            # Concatenate default export path
            #
            directory = self.scene.currentDirectory()
            nodeName = fnnode.FnNode(skin.transform()).name()

            defaultFilePath = os.path.join(directory, '{name}.json'.format(name=nodeName))

            # Prompt user for save path
            #
            filePath, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
                self,
                'Save Skin Weights',
                defaultFilePath,
                'All JSON Files (*.json)'
            )

            if len(filePath) > 0:

                skinutils.exportSkin(filePath, skin)

            else:

                log.info('Operation aborted...')

        else:

            # Prompt user for save path
            #
            defaultDirectory = self.scene.currentDirectory()

            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                'Save Skin Weights',
                defaultDirectory,
                QtWidgets.QFileDialog.ShowDirsOnly
            )

            if not os.path.exists(directory):

                log.info('Operation aborted...')
                return

            # Iterate through selected nodes
            #
            for obj in selection:

                # Try and initialize skin interface
                #
                success = skin.trySetObject(obj)

                if not success:

                    continue

                # Export weights to directory
                #
                nodeName = fnnode.FnNode(skin.transform()).name()
                filePath = os.path.join(directory, '{name}.json'.format(name=nodeName))

                skinutils.exportSkin(filePath, skin)

    @QtCore.Slot(bool)
    def on_loadWeightsAction_triggered(self, checked=False):
        """
        Slot method for the loadWeightsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.scene.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount != 1:

            log.warning('Invalid selection!')
            return

        # Prompt user for file path
        #
        defaultDirectory = self.scene.currentDirectory()

        filePath, selectedFilter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            'Load Weights',
            defaultDirectory,
            r'All JSON Files (*.json)'
        )

        # Check if a file was specified
        #
        if os.path.exists(filePath):

            log.info('Loading weights from: %s' % filePath)
            qeditweightsdialog.loadWeights(selection[0], filePath, parent=self)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_resetIntermediateObjectAction_triggered(self, checked=False):
        """
        Slot method for the resetIntermediateObjectAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user
        #
        reply = QtWidgets.QMessageBox.question(
            self,
            'Seat Skin',
            'Are you sure you want to reset the intermediate object?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes and self.skin.isValid():

            self.skin.resetIntermediateObject()

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_resetBindPreMatricesAction_triggered(self, checked=False):
        """
        Slot method for the resetBindPreMatricesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user
        #
        reply = QtWidgets.QMessageBox.question(
            self,
            'Reset Influences',
            'Are you sure you want to reset the bind-pre matrices?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes and self.skin.isValid():

            self.skin.resetPreBindMatrices()

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_blendByDistanceAction_triggered(self, checked=False):
        """
        Slot method for the blendByDistanceAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self._blendByDistance = checked

    @QtCore.Slot(bool)
    def on_setMirrorToleranceAction_triggered(self, checked=False):
        """
        Slot method for the setMirrorToleranceAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Define input dialog
        #
        threshold, ok = QtWidgets.QInputDialog.getDouble(
            self,
            'Set Mirror Threshold',
            'Enter radius for closest point consideration:',
            self.mirrorTolerance,
            minValue=1e-3,
            decimals=3
        )

        # Check dialog result before setting value
        #
        if ok:

            self.mirrorTolerance = threshold

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_copyWeightsAction_triggered(self, checked=False):
        """
        Slot method for the copyWeightsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.copyWeights()

    @QtCore.Slot(bool)
    def on_pasteWeightsAction_triggered(self, checked=False):
        """
        Slot method for the pasteWeightsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteWeights()

    @QtCore.Slot(bool)
    def on_copySkinAction_triggered(self, checked=False):
        """
        Slot method for the copySkinAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.copySkin()

    @QtCore.Slot(bool)
    def on_pasteSkinAction_triggered(self, checked=False):
        """
        Slot method for the pasteSkinAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteSkin()

    @QtCore.Slot(bool)
    def on_pasteAverageWeightsAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for pasting averaged skin weights to the active selection.

        :type checked: bool
        :rtype: None
        """

        self.pasteWeights(average=True)

    @QtCore.Slot(bool)
    def on_blendVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for blending the active selection.

        :type checked: bool
        :rtype: None
        """

        self.blendVertices()

    @QtCore.Slot(bool)
    def on_blendBetweenVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for blending between vertex pairs.

        :type checked: bool
        :rtype: None
        """

        self.blendBetweenVertices()

    @QtCore.Slot(QtWidgets.QAction)
    def on_mirrorAxisActionGroup_triggered(self, action):
        """
        Triggered slot method responsible for updating the internal mirror axis.

        :type action: QtWidgets.QAction
        :rtype: None
        """

        self._mirrorAxis = self.sender().actions().index(action)

    @QtCore.Slot()
    def on_searchLineEdit_editingFinished(self):
        """
        Editing finished slot method called whenever the user is done editing the search field.
        This search value will be passed to the filter model.

        :rtype: None
        """

        text = self.sender().text()
        filterWildcard = '*{text}*'.format(text=text)

        log.info('Searching for: %s' % filterWildcard)
        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

    @QtCore.Slot(bool)
    def on_addInfluencePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for showing the add influence dialog.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.addInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_removeInfluencePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for showing the remove influence dialog.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.removeInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(QtCore.QItemSelection, QtCore.QItemSelection)
    def on_influenceSelectionModel_selectionChanged(self, selected, deselected):
        """
        Slot method for the influenceSelectionModel's `selectionChanged signal.
        Updates the influence colours based on the selected influence item.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        # Get selected rows from table
        #
        rows = self.influenceTable.selectedRows()
        numRows = len(rows)

        if numRows == 1:

            # Update current influence
            #
            self._currentInfluence = rows[0]

            # Select influence and redraw
            #
            self.skin.selectInfluence(self._currentInfluence)
            self.invalidateColors()

    @QtCore.Slot(QtCore.QPoint)
    def on_weightTable_customContextMenuRequested(self, point):
        """
        Slot method for the weightTable's `customContextMenuRequested signal.
        Displays the weight table menu the selected influence-weight item.

        :type point: QtCore.QPoint
        :rtype: None
        """

        numRows = self.weightItemModel.rowCount()
        hasSelection = self.weightTable.selectionModel().hasSelection()

        if numRows > 1 and hasSelection:

            return self.weightTableMenu.exec_(self.weightTable.mapToGlobal(point))

    @QtCore.Slot(QtCore.QModelIndex)
    def on_weightTable_doubleClicked(self, index):
        """
        Selects the text value from the opposite table.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Map index to source model
        #
        index = self.weightItemFilterModel.mapToSource(index)
        row = index.row()

        # Select row
        #
        self.influenceTable.selectRow(row)

    @QtCore.Slot(int)
    def on_mirrorWeightButtonGroup_idClicked(self, index):
        """
        Mirrors the selected vertex weights across the mesh.

        :type index: int
        :rtype: None
        """

        self.mirrorWeights(pull=bool(index))

    @QtCore.Slot(bool)
    def on_slabDropDownButton_clicked(self, checked=False):
        """
        Trigger method used to copy the selected vertex influences to the nearest neighbour.
        See "getSlabMethod" for details.

        :rtype: bool
        """

        self.slabPasteWeights()

    @QtCore.Slot(QtWidgets.QAction)
    def on_slabActionGroup_triggered(self, action):
        """
        Triggered slot method responsible for updating the internal slab option.

        :type action: QtWidgets.QAction
        :rtype: None
        """

        self._slabOption = self.sender().actions().index(action)

    @QtCore.Slot(int)
    def on_weightPresetButtonGroup_idClicked(self, index):
        """
        ID clicked slot method responsible for applying the selected preset.

        :type index: int
        :rtype: None
        """

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        vertexWeights = self.vertexWeights()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.setWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                self.__presets__[index],
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_setWeightPushButton_clicked(self, checked=False):
        """
        ID clicked slot method responsible for setting the selected vertex weights.

        :type checked: bool
        :rtype: None
        """

        # Check if skin is valid
        #
        if not self.skin.isValid():

            return

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        amount = self.setWeightSpinBox.value()
        vertexWeights = self.vertexWeights()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.setWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(int)
    def on_incrementWeightButtonGroup_idClicked(self, index):
        """
        ID clicked slot method responsible for incrementing the selected vertex weights.

        :type index: int
        :rtype: None
        """

        # Check if skin is valid
        #
        if not self.skin.isValid():

            return

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        amount = self.incrementWeightSpinBox.value() * self.__sign__[index]
        vertexWeights = self.vertexWeights()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.incrementWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(int)
    def on_scaleWeightButtonGroup_idClicked(self, index):
        """
        ID clicked slot method responsible for scaling the selected vertex weights.

        :type index: bool
        :rtype: None
        """

        # Check if skin is valid
        #
        if not self.skin.isValid():

            return

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        percent = self.scaleWeightSpinBox.value() * self.__sign__[index]
        vertexWeights = self.vertexWeights()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.scaleWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                percent,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_precisionCheckBox_toggled(self, checked):
        """
        Toggled slot method responsible for toggling precision mode.

        :type checked: bool
        :rtype: None
        """

        # Toggle auto select behaviour
        #
        self._precision = checked

        if self._precision:

            # Change selection mode to extended
            #
            self.weightTable.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

            # Disable auto select
            #
            self.influenceTable.setAutoSelect(False)
            self.weightTable.setAutoSelect(False)

        else:

            # Change selection model to single
            #
            self.weightTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

            # Enable auto select
            #
            self.influenceTable.setAutoSelect(True)
            self.weightTable.setAutoSelect(True)

            # Force synchronize
            #
            self.influenceTable.synchronize()

    @QtCore.Slot(bool)
    def on_selectShellCheckBox_toggled(self, checked):
        """
        Toggled slot method responsible for updating the internal select shell flag.

        :type checked: bool
        :rtype: None
        """

        self._selectShell = checked

    @QtCore.Slot(bool)
    def on_selectAffectedVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for selecting vertices associated with the weight table selection.

        :type checked: bool
        :rtype: None
        """

        self.selectAffectedVertices()

    @QtCore.Slot(bool)
    def on_usingEzSkinBlenderAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for opening the github documentation.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezskinblender')
    # endregion
