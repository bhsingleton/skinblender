import os
import webbrowser

from PySide2 import QtCore, QtWidgets, QtGui
from dcc import fnscene, fnnotify, fnnode, fnskin
from dcc.userinterface import quicwindow
from vertexblender.dialogs import qeditinfluencesdialog, qeditweightsdialog
from vertexblender.models import qinfluenceitemmodel, qweightitemmodel, qinfluenceitemfiltermodel, qweightitemfiltermodel
from vertexblender.views import qinfluenceview

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def validate(func):
    """
    Returns a wrapper that validates functions against the UI before executing.
    This will help reduce the amount of conditions needed when we're not in edit mode.

    :type func: function
    :rtype: function
    """

    def wrapper(*args, **kwargs):

        window = args[0]  # type: QVertexBlender

        if window.skin.isValid():

            return func(*args, **kwargs)

        else:

            return

    return wrapper


class QVertexBlender(quicwindow.QUicWindow):
    """
    Overload of QProxyWindow used to manipulate vertex weights.
    """

    skinChanged = QtCore.Signal(object)
    vertexSelectionChanged = QtCore.Signal(list)

    # region Dunderscores
    __presets__ = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)
    __sign__ = (1.0, -1.0)

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :keyword parent: QtWidgets.QWidget
        :keyword flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._currentInfluence = None
        self._softSelection = {}
        self._selection = []
        self._precision = False
        self._blendByDistance = False
        self._selectShell = False
        self._slabOption = 0
        self._search = ''
        self._mirrorAxis = 0
        self._mirrorTolerance = 1e-3
        self._clipboard = None
        self._selectionChangedId = None
        self._undoId = None
        self._redoId = None

        # Declare public variables
        #
        self.influenceItemModel = None
        self.influenceItemFilterModel = None
        self.weightItemModel = None
        self.weightItemFilterModel = None

        # Call parent method
        #
        super(QVertexBlender, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def skin(self):
        """
        Getter method used to retrieve the selected skin cluster object.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @property
    def precision(self):
        """
        Method used to check if precision mode is enabled.

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
        Getter method used to retrieve the current slab option.

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
    @classmethod
    def customWidgets(cls):
        """
        Returns a dictionary of custom widgets used by this class.

        :rtype: dict[str:type]
        """

        customWidgets = super(QVertexBlender, cls).customWidgets()
        customWidgets['QInfluenceView'] = qinfluenceview.QInfluenceView

        return customWidgets

    def preLoad(self):
        """
        Called before the user interface has been loaded.

        :rtype: None
        """

        # Create weight table context menu
        #
        self.weightTableMenu = QtWidgets.QMenu(parent=self)

        self.selectVerticesAction = self.weightTableMenu.addAction('&Select Affected Vertices')
        self.selectVerticesAction.triggered.connect(self.on_selectVerticesAction_triggered)

        # Create slab button context menu
        #
        self.slabMenu = QtWidgets.QMenu(parent=self)

        self.slabGroup = QtWidgets.QActionGroup(self.slabMenu)
        self.slabGroup.setExclusive(True)
        self.slabGroup.triggered.connect(self.on_slabGroup_triggered)

        self.closestPointAction = self.slabMenu.addAction('&Closest Point')
        self.closestPointAction.setCheckable(True)
        self.closestPointAction.setChecked(QtCore.Qt.CheckState.Checked)

        self.nearestNeighbourAction = self.slabMenu.addAction('&Nearest Neighbour')
        self.nearestNeighbourAction.setCheckable(True)

        self.alongNormalAction = self.slabMenu.addAction('&Along Normal')
        self.alongNormalAction.setCheckable(True)

        self.slabGroup.addAction(self.closestPointAction)
        self.slabGroup.addAction(self.nearestNeighbourAction)
        self.slabGroup.addAction(self.alongNormalAction)

    def postLoad(self):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Initialize influence item model
        #
        self.influenceItemModel = qinfluenceitemmodel.QInfluenceItemModel(parent=self.influenceTable)
        self.skinChanged.connect(self.influenceItemModel.setSkin)

        self.influenceItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.influenceTable)
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)
        self.influenceTable.setModel(self.influenceItemFilterModel)

        # Initialize weight item model
        #
        self.weightItemModel = qweightitemmodel.QWeightItemModel(parent=self.weightTable)
        self.skinChanged.connect(self.weightItemModel.setSkin)
        self.vertexSelectionChanged.connect(self.weightItemModel.setVertexSelection)

        self.weightItemFilterModel = qweightitemfiltermodel.QWeightItemFilterModel(parent=self.weightTable)
        self.weightItemFilterModel.setSourceModel(self.weightItemModel)
        self.weightTable.setModel(self.weightItemFilterModel)

        # Set table buddies
        #
        self.influenceTable.setBuddy(self.weightTable)
        self.influenceTable.horizontalHeader().setStretchLastSection(True)

        self.weightTable.setBuddy(self.influenceTable)
        self.weightTable.horizontalHeader().setStretchLastSection(True)

        self.slabToolButton.setMenu(self.slabMenu)

        # Assign button group ids
        #
        self.mirrorWeightButtonGroup.setId(self.mirrorPushButton, 0)
        self.mirrorWeightButtonGroup.setId(self.pullPushButton, 1)

        self.weightPresetButtonGroup.setId(self.weightPresetPushButton1, 0)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton2, 1)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton3, 2)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton4, 3)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton5, 4)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton6, 5)
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton7, 6)

        self.incrementWeightButtonGroup.setId(self.incrementWeightPushButton1, 0)  # +
        self.incrementWeightButtonGroup.setId(self.incrementWeightPushButton2, 1)  # -

        self.scaleWeightButtonGroup.setId(self.scaleWeightPushButton1, 0)  # +
        self.scaleWeightButtonGroup.setId(self.scaleWeightPushButton2, 1)  # -

    def saveSettings(self):
        """
        Saves the user settings.

        :rtype: None
        """

        self.settings.setValue('editor/mirrorAxis', self.mirrorAxis)
        self.settings.setValue('editor/mirrorTolerance', self.mirrorTolerance)
        self.settings.setValue('editor/blendByDistance', self.blendByDistance)

    def loadSettings(self):
        """
        Loads the user settings.

        :rtype: None
        """

        mirrorAxis = self.settings.value('editor/mirrorAxis', defaultValue='0', type=int)
        self.mirrorAxisActionGroup.actions()[mirrorAxis].setChecked(True)

        blendByDistance = self.settings.value('editor/blendByDistance', defaultValue='False', type=bool)
        self.blendByDistanceAction.setChecked(blendByDistance)

        self.mirrorTolerance = self.settings.value('editor/mirrorTolerance', defaultValue='1e-3', type=float)

    def selection(self):
        """
        Returns the vertex indices from the active selection.

        :rtype: list[int]
        """

        return list(self._softSelection.keys())

    def softSelection(self):
        """
        Returns the soft values from the active selection.

        :rtype: dict[int:float]
        """

        return self._softSelection

    def vertexWeights(self):
        """
        Returns the vertex weights from the active selection.

        :rtype: dict[int:dict[int:float]]
        """

        return self.weightItemModel.vertexWeights()

    def weights(self):
        """
        Returns the averaged vertex weights from the active selection.

        :rtype: dict[int:float]
        """

        return self.weightItemModel.weights()

    def currentInfluence(self):
        """
        Returns the current influence ID.

        :rtype: int
        """

        return self._currentInfluence

    def sourceInfluences(self):
        """
        Gets all of the source influences to redistribute from using the selection model.

        :rtype: list[int]
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

            influenceIds = [x for x in self.weightFilterModel.activeInfluences if x not in selectedRows]

        # Return influence ids
        #
        log.debug('Source Influences: %s' % influenceIds)
        return influenceIds

    @validate
    def invalidateInfluences(self):
        """
        Invalidation method used to reset the influence list.

        :rtype: None
        """

        self.influenceItemModel.invalidateInfluences()

    @validate
    def invalidateWeights(self, *args, **kwargs):
        """
        Invalidation method used to reset the selection list.
        :rtype: None
        """

        self.weightItemModel.invalidateWeights()

    @validate
    def invalidateColors(self, *args, **kwargs):
        """
        Invalidation method used to re-transfer paint weights onto color set.

        :rtype: None
        """

        self.skin.invalidateColors()
    # endregion

    # region Callbacks
    @validate
    def activeSelectionChanged(self):
        """
        Callback method used to invalidate the active selection.

        :rtype: None
        """

        # Check if skin is selected
        # If not then we don't need to invalidate
        #
        if self.skin.isPartiallySelected():

            self._softSelection = self.skin.softSelection()
            self._selection = list(self._softSelection.keys())

            self.vertexSelectionChanged.emit(self._selection)
            self.invalidateColors()
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
        self.editEnvelopePushButton.setChecked(False)

        # Call parent method
        #
        return super(QVertexBlender, self).closeEvent(event)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_saveWeightsAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for prompting the save weights dialog.

        :type checked: bool
        :rtype: None
        """

        # Evaluate active selection
        #
        selection = fnskin.FnSkin.getActiveSelection()
        selectionCount = len(selection)

        fnScene = fnscene.FnScene()
        fnSkin = fnskin.FnSkin()

        if selectionCount == 0:

            log.warning('Invalid selection!')
            return

        elif selectionCount == 1:

            # Initialize skin function set
            #
            success = fnSkin.trySetObject(selection[0])

            if not success:

                log.warning('Invalid selection...')
                return

            # Concatenate default file path
            #
            directory = fnScene.currentDirectory()
            shapeName = fnnode.FnNode(fnSkin.shape()).name()

            defaultFilePath = os.path.join(directory, '{name}.json'.format(name=shapeName))

            # Prompt user for save path
            #
            filePath, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
                self,
                'Save Skin Weights',
                defaultFilePath,
                'All JSON Files (*.json)'
            )

            if len(filePath) > 0:

                log.info('Saving weights to: %s' % filePath)
                fnSkin.saveWeights(filePath)

            else:

                log.info('Operation aborted...')
                return

        else:

            # Prompt user for save path
            #
            defaultDirectory = fnScene.currentDirectory()

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

                # Try and initialize function set
                #
                success = fnSkin.trySetObject(obj)

                if not success:

                    continue

                # Save weights to directory
                #
                shapeName = fnnode.FnNode(fnSkin.shape()).name()
                filePath = os.path.join(directory, '{name}.json'.format(name=shapeName))

                log.info('Saving weights to: %s' % filePath)
                fnSkin.saveWeights(filePath)

    @QtCore.Slot(bool)
    def on_loadWeightsAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for prompting the load weights dialog.

        :type checked: bool
        :rtype: None
        """

        # Evaluate active selection
        #
        selection = fnskin.FnSkin.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount != 1:

            log.warning('Invalid selection!')
            return

        # Prompt user for file path
        #
        fnScene = fnscene.FnScene()
        defaultDirectory = fnScene.currentDirectory()

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
            qeditweightsdialog.loadSkinWeights(selection[0], filePath)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_resetIntermediateObjectAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for prompting the reset intermediate object dialog.

        :type checked: bool
        :rtype: bool
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

        if reply == QtWidgets.QMessageBox.Yes:

            self.on_resetIntermediateObjectAction_triggered()

    @QtCore.Slot(bool)
    def on_resetBindPreMatricesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for prompting the reset bind-pre matrices dialog.

        :type checked: bool
        :rtype: bool
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

        if reply == QtWidgets.QMessageBox.Yes:

            self.skin.resetPreBindMatrices()

    @QtCore.Slot(bool)
    def on_blendByDistanceAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for updating the internal blend by distance flag.

        :type checked: bool
        :rtype: None
        """

        self._blendByDistance = checked

    @QtCore.Slot(bool)
    def on_setMirrorToleranceAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for updating the internal mirror tolerance.

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
        Triggered slot method responsible for copying skin weights from the active selection.

        :type checked: bool
        :rtype: None
        """

        self.skin.copyWeights()

    @QtCore.Slot(bool)
    def on_pasteWeightsAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for pasting skin weights to the active selection.

        :type checked: bool
        :rtype: None
        """

        if self.skin.isValid():

            self.skin.pasteWeights()
            self.invalidateWeights()
            self.invalidateColors()

    @QtCore.Slot(bool)
    def on_pasteAveragedWeightsAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for pasting averaged skin weights to the active selection.

        :type checked: bool
        :rtype: None
        """

        if self.skin.isValid():

            self.skin.pasteAveragedWeights()
            self.invalidateWeights()
            self.invalidateColors()

    @QtCore.Slot(bool)
    def on_blendVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for blending the active selection.

        :type checked: bool
        :rtype: None
        """

        self.skin.blendVertices(self.selection())

        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(bool)
    def on_blendBetweenVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for blending between vertex pairs.

        :type checked: bool
        :rtype: None
        """

        self.skin.blendBetweenVertices(self.selection(), blendByDistance=self.blendByDistance)

        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(bool)
    def on_editEnvelopePushButton_toggled(self, checked):
        """
        Toggled slot method called whenever the user enters edit envelope mode.

        :type checked: bool
        :rtype: None
        """

        # Check if envelope is checked
        #
        sender = self.sender()
        fnNotify = fnnotify.FnNotify()

        if checked:

            # Evaluate active selection
            # If nothing is selected then uncheck button
            #
            selection = fnskin.FnSkin.getActiveSelection()
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

            # Add callbacks
            #
            self._selectionChangedId = fnNotify.addSelectionChangedNotify(self.activeSelectionChanged)
            self._undoId = fnNotify.addUndoNotify(self.invalidateColors)
            self._redoId = fnNotify.addRedoNotify(self.invalidateColors)

            # Enable vertex colour display
            #
            self.skinChanged.emit(self.skin.object())
            self.skin.showColors()

            self.invalidateWeights()
            self.invalidateColors()

            # Select first influence
            #
            self.influenceTable.selectFirstRow()

        else:

            # Check if function set still has an object attached
            # If so then we need to reset it and remove the previous callbacks
            #
            if self.skin.isValid():

                # Remove callbacks
                #
                self._selectionChangedId = fnNotify.removeNotify(self._selectionChangedId)
                self._undoId = fnNotify.removeNotify(self._undoId)
                self._redoId = fnNotify.removeNotify(self._redoId)

                # Reset object
                #
                self.skin.hideColors()
                self.skin.resetObject()

            # Signal skin has changed
            #
            self.skinChanged.emit(None)

    @QtCore.Slot()
    def on_searchLineEdit_editingFinished(self):
        """
        Editing finished slot method called whenever the user is done editing the search field.
        This search value will be passed to the filter model.

        :rtype: None
        """

        text = self.sender().text()
        filterWildcard = '*{text}*'.format(text=text)

        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

    @QtCore.Slot(bool)
    def on_addInfluencePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for showing the add influence dialog.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.addInfluences(self.skin.object())
        self.invalidateInfluences()

    @QtCore.Slot(bool)
    def on_removeInfluencePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for showing the remove influence dialog.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.removeInfluences(self.skin.object())
        self.invalidateInfluences()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTable_clicked(self, index):
        """
        Selection changed slot method responsible for updating the internal tracker.

        :type index: QtCore.QModelIndex
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
        Trigger function used to display a context menu under certain conditions.
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

        # Map index to filter model
        #
        index = self.weightItemFilterModel.mapToSource(index)

        # Get row from remapped index
        #
        row = index.row()
        column = index.column()

        text = self.weightItemModel.item(row, column).text()
        log.debug('User has double clicked %s influence.' % text)

        # Select row with text
        #
        self.influenceTable.selectRow(row)

    @QtCore.Slot(int)
    def on_mirrorWeightButtonGroup_idClicked(self, index):
        """
        Mirrors the selected vertex weights across the mesh.

        :type index: int
        :rtype: None
        """

        # Mirror vertex weights
        #
        vertexWeights = self.skin.mirrorVertexWeights(
            self.selection(),
            pull=bool(index),
            axis=self.mirrorAxis,
            tolerance=self.mirrorTolerance
        )

        self.skin.applyVertexWeights(vertexWeights)

        # Check if active selection should be reset
        #
        resetActiveSelection = self.resetPreBindMatricesAction.isChecked()

        if resetActiveSelection:

            self.skin.setSelection(list(vertexWeights.keys()))

        # Invalidate user interface
        #
        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(bool)
    def on_slabToolButton_clicked(self, checked=False):
        """
        Trigger method used to copy the selected vertex influences to the nearest neighbour.
        See "getSlabMethod" for details.

        :rtype: bool
        """

        # Get slab option before pasting
        #
        self.skin.slabPasteWeights(self.selection(), mode=self.slabOption)

        self.invalidateWeights()
        self.invalidateColors()

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

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.setWeights(
                self._vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                self.__presets__[index],
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(bool)
    def on_setWeightPushButton_clicked(self, checked=False):
        """
        ID clicked slot method responsible for setting the selected vertex weights.

        :type checked: bool
        :rtype: None
        """

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        amount = self.setterSpinBox.value()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.setWeights(
                self._vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)

        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(int)
    def on_incrementWeightButtonGroup_idClicked(self, index):
        """
        ID clicked slot method responsible for incrementing the selected vertex weights.

        :type index: int
        :rtype: None
        """

        # Get increment arguments
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        amount = self.incrementSpinBox.value() * self.__sign__[index]

        # Iterate through selection
        #
        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = self.skin.incrementWeights(
                self._vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)

        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(int)
    def on_scaleWeightButtonGroup_idClicked(self, index):
        """
        ID clicked slot method responsible for scaling the selected vertex weights.

        :type index: bool
        :rtype: None
        """

        # Get scale arguments
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        percent = self.scaleSpinBox.value() * self.__sign__[index]

        # Iterate through selection
        #
        vertexWeights = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            vertexWeights[vertexIndex] = self.skin.scaleWeights(
                self._vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                percent,
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(vertexWeights)

        self.invalidateWeights()
        self.invalidateColors()

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

    @QtCore.Slot(QtWidgets.QAction)
    def on_mirrorAxisActionGroup_triggered(self, action):
        """
        Triggered slot method responsible for updating the internal mirror axis.

        :type action: QtWidgets.QAction
        :rtype: None
        """

        self._mirrorAxis = self.sender().actions().index(action)

    @QtCore.Slot(QtWidgets.QAction)
    def on_slabGroup_triggered(self, action):
        """
        Triggered slot method responsible for updating the internal slab option.

        :type action: QtWidgets.QAction
        :rtype: None
        """

        self._slabOption = self.sender().actions().index(action)

    @QtCore.Slot(bool)
    def on_selectVerticesAction_triggered(self, checked=False):
        """
        Triggered slot method responsible for selecting vertices with the associated influence.

        :type checked: bool
        :rtype: None
        """

        # Get selected rows
        #
        selectedRows = self.weightTable.selectedRows()

        # Update active selection
        #
        selection = self.skin.getVerticesByInfluenceId(*selectedRows)

        self.skin.setSelection(selection)
        self.invalidateWeights()
        self.invalidateColors()

    @QtCore.Slot(bool)
    def on_helpAction_triggered(self):
        """
        Triggered slot method responsible for opening the github documentation.

        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/vertexblender')
    # endregion
