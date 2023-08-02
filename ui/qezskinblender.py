import os
import webbrowser

from Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc import fnscene, fnnode, fnmesh, fnskin, fnnotify
from dcc.ui import quicwindow
from .dialogs import qeditinfluencesdialog, qeditweightsdialog
from .models import qinfluenceitemfiltermodel
from ..libs import skinutils
from ..decorators.validate import validate

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def onActiveSelectionChanged(*args, **kwargs):
    """
    Callback method for any selection changes.

    :rtype: None
    """

    # Check if instance exists
    #
    instance = QEzSkinBlender.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.activeSelectionChanged(*args, **kwargs)

    else:

        log.warning('Unable to process selection changed callback!')


def onUndoBufferChanged(*args, **kwargs):
    """
    Callback method for any undo changes.

    :rtype: None
    """

    # Check if instance exists
    #
    instance = QEzSkinBlender.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.undoBufferChanged(*args, **kwargs)

    else:

        log.warning('Unable to process undo callback!')


class QEzSkinBlender(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` that manipulates skin weights.
    """

    # region Dunderscores
    __weight_presets__ = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)
    __percent_presets__ = (0.1, 0.25, 0.5, 0.75, 1.0)
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
        self._search = ''
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
        self.relaxVerticesAction = None
        self.blendVerticesAction = None
        self.blendBetweenVerticesAction = None
        self.blendByDistanceAction = None
        self.resetIntermediateObjectAction = None
        self.resetPreBindMatricesAction = None

        self.settingsMenu = None
        self.mirrorAxisSection = None
        self.mirrorXAction = None
        self.mirrorYAction = None
        self.mirrorZAction = None
        self.mirrorAxisActionGroup = None
        self.mirrorSeparator = None
        self.setMirrorToleranceAction = None

        self.debugMenu = None
        self.resetActiveSelectionAction = None

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
        self.precisionPushButton = None
        self.selectShellCheckBox = None
        self.optionsWidget = None
        self.mirrorWidget = None
        self.mirrorPushButton = None
        self.pruneDropDownButton = None
        self.slabDropDownButton = None
        self.weightPresetWidget = None
        self.weightPresetPushButton1 = None
        self.weightPresetPushButton2 = None
        self.weightPresetPushButton3 = None
        self.weightPresetPushButton4 = None
        self.weightPresetPushButton5 = None
        self.weightPresetPushButton6 = None
        self.weightPresetPushButton7 = None
        self.percentPresetWidget = None
        self.percentPresetPushButton1 = None
        self.percentPresetPushButton2 = None
        self.percentPresetPushButton3 = None
        self.percentPresetPushButton4 = None
        self.percentPresetPushButton5 = None
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

        self.pruneMenu = None
        self.pruneSpinBox = None
        self.pruneSpinBoxAction = None

        self.slabMenu = None
        self.closestPointAction = None
        self.nearestNeighbourAction = None
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
        Getter method that returns the `precision` flag.

        :rtype: bool
        """

        return self.precisionPushButton.isChecked()

    @precision.setter
    def precision(self, precision):
        """
        Setter method that updates the `precision` flag.

        :type precision: bool
        :rtype: None
        """

        self.precisionPushButton.setChecked(precision)

    @property
    def mirrorAxis(self):
        """
        Getter method used to retrieve the current mirror axis.

        :rtype: int
        """

        actions = self.mirrorAxisActionGroup.actions()
        checkedAction = self.mirrorAxisActionGroup.checkedAction()
        axis = actions.index(checkedAction)

        return axis

    @mirrorAxis.setter
    def mirrorAxis(self, axis):
        """
        Setter method that updates the current mirror axis.

        :type axis: int
        :rtype: None
        """

        actions = self.mirrorAxisActionGroup.actions()
        actions[axis].setChecked(True)

    @property
    def pruneTolerance(self):
        """
        Getter method that returns the prune tolerance.

        :rtype: float
        """

        return self.pruneSpinBox.value()

    @pruneTolerance.setter
    def pruneTolerance(self, tolerance):
        """
        Setter method that updates the prune tolerance.

        :type tolerance: float
        :rtype: None
        """

        self.pruneSpinBox.setValue(tolerance)

    @property
    def slabOption(self):
        """
        Getter method that returns the current slab option.

        :rtype: int
        """

        actions = self.slabActionGroup.actions()
        checkedOption = self.slabActionGroup.checkedAction()
        option = actions.index(checkedOption)

        return option

    @slabOption.setter
    def slabOption(self, option):
        """
        Setter method that updates the current slab option.

        :type option: int
        :rtype: None
        """

        actions = self.slabActionGroup.actions()
        actions[option].setChecked(True)

    @property
    def blendByDistance(self):
        """
        Getter method that returns the `blendByDistance` flag.

        :rtype: bool
        """

        return self.blendByDistanceAction.isChecked()

    @blendByDistance.setter
    def blendByDistance(self, blendByDistance):
        """
        Setter method that updates the `blendByDistance` flag.

        :type blendByDistance: bool
        :rtype: None
        """

        self.blendByDistanceAction.setChecked(blendByDistance)

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

    # region Callbacks
    def activeSelectionChanged(self, *args, **kwargs):
        """
        Callback method used to invalidate the active selection.

        :rtype: None
        """

        if self.skin.isValid():

            self.invalidateSelection()

    def undoBufferChanged(self, *args, **kwargs):
        """
        Callback method used to invalidate the display colors.

        :rtype: None
        """

        if self.skin.isValid():

            self.invalidateWeights()
    # endregion

    # region Events
    def showEvent(self, event):
        """
        Event method called after the window has been shown.

        :type event: QtGui.QShowEvent
        :rtype: None
        """

        # Call parent method
        #
        super(QEzSkinBlender, self).showEvent(event)

        # Add scene notifies
        #
        self._notifies.addSelectionChangedNotify(onActiveSelectionChanged)
        self._notifies.addUndoNotify(onUndoBufferChanged)
        self._notifies.addRedoNotify(onUndoBufferChanged)

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

        # Clear notifies
        #
        self._notifies.clear()

        # Call parent method
        #
        super(QEzSkinBlender, self).closeEvent(event)
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

        # Add file menu actions
        #
        self.saveWeightsAction = QtWidgets.QAction('Save Weights', parent=self.fileMenu)
        self.saveWeightsAction.setObjectName('saveWeightsAction')
        self.saveWeightsAction.triggered.connect(self.on_saveWeightsAction_triggered)

        self.loadWeightsAction = QtWidgets.QAction('Load Weights', parent=self.fileMenu)
        self.loadWeightsAction.setObjectName('loadWeightsAction')
        self.loadWeightsAction.triggered.connect(self.on_loadWeightsAction_triggered)

        self.fileMenu.addActions([self.saveWeightsAction, self.loadWeightsAction])

        # Add edit menu actions
        #
        self.copyWeightsAction = QtWidgets.QAction('Copy Weights', parent=self.editMenu)
        self.copyWeightsAction.setObjectName('copyWeightsAction')
        self.copyWeightsAction.triggered.connect(self.on_copyWeightsAction_triggered)

        self.pasteWeightsAction = QtWidgets.QAction('Paste Weights', parent=self.editMenu)
        self.pasteWeightsAction.setObjectName('pasteWeightsAction')
        self.pasteWeightsAction.triggered.connect(self.on_pasteWeightsAction_triggered)

        self.pasteAverageWeightsAction = QtWidgets.QAction('Paste Average Weights', parent=self.editMenu)
        self.pasteAverageWeightsAction.setObjectName('pasteAverageWeightsAction')
        self.pasteAverageWeightsAction.triggered.connect(self.on_pasteAverageWeightsAction_triggered)

        self.copySkinAction = QtWidgets.QAction('Copy Skin', parent=self.editMenu)
        self.copySkinAction.setObjectName('copySkinAction')
        self.copySkinAction.triggered.connect(self.on_copySkinAction_triggered)

        self.pasteSkinAction = QtWidgets.QAction('Paste Skin', parent=self.editMenu)
        self.pasteSkinAction.setObjectName('pasteSkinAction')
        self.pasteSkinAction.triggered.connect(self.on_pasteSkinAction_triggered)

        self.relaxVerticesAction = QtWidgets.QAction('Relax Vertices', parent=self.editMenu)
        self.relaxVerticesAction.setObjectName('relaxVerticesAction')
        self.relaxVerticesAction.triggered.connect(self.on_relaxVerticesAction_triggered)

        self.blendVerticesAction = QtWidgets.QAction('Blend Vertices', parent=self.editMenu)
        self.blendVerticesAction.setObjectName('blendVerticesAction')
        self.blendVerticesAction.triggered.connect(self.on_blendVerticesAction_triggered)

        self.blendBetweenVerticesAction = QtWidgets.QAction('Blend Between Vertices', parent=self.editMenu)
        self.blendBetweenVerticesAction.setObjectName('blendBetweenVerticesAction')
        self.blendBetweenVerticesAction.triggered.connect(self.on_blendBetweenVerticesAction_triggered)

        self.blendByDistanceAction = QtWidgets.QAction('Blend By Distance', parent=self.editMenu)
        self.blendByDistanceAction.setObjectName('blendByDistanceAction')
        self.blendByDistanceAction.setCheckable(True)

        self.resetIntermediateObjectAction = QtWidgets.QAction('Reset Intermediate Object', parent=self.editMenu)
        self.resetIntermediateObjectAction.setObjectName('resetIntermediateObjectAction')
        self.resetIntermediateObjectAction.triggered.connect(self.on_resetIntermediateObjectAction_triggered)

        self.resetPreBindMatricesAction = QtWidgets.QAction('Reset Pre-Bind Matrices', parent=self.editMenu)
        self.resetPreBindMatricesAction.setObjectName('resetPreBindMatricesAction')
        self.resetPreBindMatricesAction.triggered.connect(self.on_resetPreBindMatricesAction_triggered)

        self.editMenu.addActions([self.copyWeightsAction, self.pasteWeightsAction, self.pasteAverageWeightsAction])
        self.editMenu.addSeparator()
        self.editMenu.addActions([self.copySkinAction, self.pasteSkinAction])
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.relaxVerticesAction)
        self.editMenu.addSeparator()
        self.editMenu.addActions([self.blendVerticesAction, self.blendBetweenVerticesAction, self.blendByDistanceAction])
        self.editMenu.addSeparator()
        self.editMenu.addActions([self.resetIntermediateObjectAction, self.resetPreBindMatricesAction])

        # Add settings menu actions
        #
        self.mirrorAxisSection = QtWidgets.QAction('Mirror Axis:', parent=self.settingsMenu)
        self.mirrorAxisSection.setObjectName('mirrorAxisSection')
        self.mirrorAxisSection.setSeparator(True)

        self.mirrorXAction = QtWidgets.QAction('X', parent=self.settingsMenu)
        self.mirrorXAction.setObjectName('mirrorXAction')
        self.mirrorXAction.setCheckable(True)
        self.mirrorXAction.setChecked(True)

        self.mirrorYAction = QtWidgets.QAction('Y', parent=self.settingsMenu)
        self.mirrorYAction.setObjectName('mirrorYAction')
        self.mirrorYAction.setCheckable(True)

        self.mirrorZAction = QtWidgets.QAction('Z', parent=self.settingsMenu)
        self.mirrorZAction.setObjectName('mirrorZAction')
        self.mirrorZAction.setCheckable(True)

        self.mirrorAxisActionGroup = QtWidgets.QActionGroup(self.settingsMenu)
        self.mirrorAxisActionGroup.addAction(self.mirrorXAction)
        self.mirrorAxisActionGroup.addAction(self.mirrorYAction)
        self.mirrorAxisActionGroup.addAction(self.mirrorZAction)

        self.mirrorSeparator = QtWidgets.QAction('', parent=self.settingsMenu)
        self.mirrorSeparator.setObjectName('mirrorSeparator')
        self.mirrorSeparator.setSeparator(True)

        self.setMirrorToleranceAction = QtWidgets.QAction('Set Mirror Tolerance', parent=self.settingsMenu)
        self.setMirrorToleranceAction.setObjectName('setMirrorToleranceAction')
        self.setMirrorToleranceAction.triggered.connect(self.on_setMirrorToleranceAction_triggered)

        self.settingsMenu.addActions([self.mirrorAxisSection, self.mirrorXAction, self.mirrorYAction, self.mirrorZAction])
        self.settingsMenu.addSeparator()
        self.settingsMenu.addAction(self.setMirrorToleranceAction)

        # Add debug menu actions
        #
        self.resetActiveSelectionAction = QtWidgets.QAction('Reset Active Selection', parent=self.debugMenu)
        self.resetActiveSelectionAction.setObjectName('resetActiveSelectionAction')
        self.resetActiveSelectionAction.setCheckable(True)

        self.debugMenu.addAction(self.resetActiveSelectionAction)

        # Add help menu actions
        #
        self.usingEzSkinBlenderAction = QtWidgets.QAction("Using Ez Skin Blender", parent=self.helpMenu)
        self.usingEzSkinBlenderAction.setObjectName('usingEzSkinBlenderAction')
        self.usingEzSkinBlenderAction.triggered.connect(self.on_usingEzSkinBlenderAction_triggered)

        self.helpMenu.addAction(self.usingEzSkinBlenderAction)

        # Initialize influence item model
        #
        self.influenceItemModel = QtGui.QStandardItemModel(parent=self.influenceTable)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Name'])

        self.influenceItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.influenceTable)
        self.influenceItemFilterModel.setObjectName('influenceItemFilterModel')
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)

        self.influenceTable.setModel(self.influenceItemFilterModel)
        
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

        # Create prune button context menu
        #
        self.pruneMenu = QtWidgets.QMenu(parent=self.pruneDropDownButton)
        self.pruneMenu.setObjectName('pruneMenu')

        self.pruneSpinBox = QtWidgets.QDoubleSpinBox(parent=self.pruneMenu)
        self.pruneSpinBox.setObjectName('pruneSpinBox')
        self.pruneSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.pruneSpinBox.setDecimals(3)
        self.pruneSpinBox.setMinimum(0.0)
        self.pruneSpinBox.setMaximum(1.0)
        self.pruneSpinBox.setValue(0.001)
        self.pruneSpinBox.setSingleStep(0.001)

        self.pruneSpinBoxAction = QtWidgets.QWidgetAction(self.pruneMenu)
        self.pruneSpinBoxAction.setObjectName('pruneSpinBoxAction')
        self.pruneSpinBoxAction.setDefaultWidget(self.pruneSpinBox)

        self.pruneMenu.addAction(self.pruneSpinBoxAction)

        self.pruneDropDownButton.setMenu(self.pruneMenu)

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

        self.slabActionGroup = QtWidgets.QActionGroup(self.slabMenu)
        self.slabActionGroup.setObjectName('slabActionGroup')
        self.slabActionGroup.setExclusive(True)
        self.slabActionGroup.addAction(self.closestPointAction)
        self.slabActionGroup.addAction(self.nearestNeighbourAction)

        self.slabMenu.addActions([self.closestPointAction, self.nearestNeighbourAction])

        self.slabDropDownButton.setMenu(self.slabMenu)

        # Assign button group ids
        #
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton1, 0)  # 0.0
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton2, 1)  # 0.1
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton3, 2)  # 0.25
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton4, 3)  # 0.5
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton5, 4)  # 0.75
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton6, 5)  # 0.9
        self.weightPresetButtonGroup.setId(self.weightPresetPushButton7, 6)  # 1.0

        self.percentPresetButtonGroup.setId(self.percentPresetPushButton1, 0)  # 0.1
        self.percentPresetButtonGroup.setId(self.percentPresetPushButton2, 1)  # 0.25
        self.percentPresetButtonGroup.setId(self.percentPresetPushButton3, 2)  # 0.5
        self.percentPresetButtonGroup.setId(self.percentPresetPushButton4, 3)  # 0.75
        self.percentPresetButtonGroup.setId(self.percentPresetPushButton5, 4)  # 1.0

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
        settings.setValue('editor/blendByDistance', int(self.blendByDistance))
        settings.setValue('editor/mirrorAxis', self.mirrorAxis)
        settings.setValue('editor/mirrorTolerance', self.mirrorTolerance)
        settings.setValue('editor/pruneTolerance', self.pruneTolerance)
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
        self.mirrorAxis = int(settings.value('editor/mirrorAxis', defaultValue=0))
        self.mirrorTolerance = float(settings.value('editor/mirrorTolerance', defaultValue='1e-3'))
        self.blendByDistance = bool(settings.value('editor/blendByDistance', defaultValue=0))
        self.pruneTolerance = float(settings.value('editor/pruneTolerance', defaultValue='1e-2'))
        self.slabOption = int(settings.value('editor/slabOption', defaultValue=0))

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

        # Check if precision mode is active
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

            self._clipboard.applySkin(mesh.object())

        else:

            log.warning('Invalid mesh selected!')

    @validate
    def relaxVertices(self):
        """
        Relaxes the selected vertex weights.

        :rtype: None
        """

        self.skin.relaxVertices(self.selection())
        self.invalidateWeights()

    @validate
    def blendVertices(self):
        """
        Blends the selected vertex weights.

        :rtype: None
        """

        self.skin.blendVertices(self.selection())
        self.invalidateWeights()

    @validate
    def blendBetweenVertices(self):
        """
        Blends between the selected vertex pairs.

        :rtype: None
        """

        self.skin.blendBetweenVertices(self.selection(), blendByDistance=self.blendByDistance)
        self.invalidateWeights()

    @validate
    def pruneWeights(self, tolerance=1e-3):
        """
        Prunes any influences below the specified tolerance.

        :type tolerance: float
        :rtype: None
        """

        self.skin.pruneVertices(self.selection(), tolerance=tolerance)
        self.invalidateWeights()

    @validate
    def mirrorWeights(self, pull=False, swap=False):
        """
        Mirrors the active component selection.

        :type pull: bool
        :type swap: bool
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

    @staticmethod
    def fillItemModel(model, rowCount, columnCount):
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
            influenceName = ''

            if influence is not None:

                influenceName = influence.name()

            # Update item data
            #
            item = self.influenceItemModel.item(i)
            item.setText(influenceName)
            item.setTextAlignment(QtCore.Qt.AlignCenter)

        # Invalidate filter model
        #
        self.influenceItemFilterModel.invalidateFilter()

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

            influenceName = ''
            influenceWeight = self._weights.get(i, None)

            if influence is not None:

                influenceName = influence.name()

            # Update item data
            #
            item1 = self.weightItemModel.item(i)
            item1.setText(influenceName)
            item1.setTextAlignment(QtCore.Qt.AlignCenter)

            item2 = self.weightItemModel.item(i, column=1)
            item2.setText(str(round(influenceWeight, 2)) if influenceWeight is not None else '')
            item2.setTextAlignment(QtCore.Qt.AlignCenter)

        # Invalidate filter model
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

    # region Slots
    @QtCore.Slot(bool)
    def on_envelopePushButton_toggled(self, checked):
        """
        Slot method for the envelopePushButton's `toggled` signal.

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

            # Display vertex colors
            #
            self.skin.showColors()

            # Invalidate item models
            #
            self.invalidateInfluences()
            self.invalidateSelection()
            self.influenceTable.selectFirstRow()

        else:

            # Reset skin function set
            #
            if self.skin.isValid():

                self.skin.hideColors()
                self.skin.resetObject()

            # Reset item models
            #
            self.influenceItemModel.setRowCount(0)
            self.weightItemModel.setRowCount(0)

            # Disable precision mode
            #
            self.precisionPushButton.setChecked(False)

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
    def on_resetPreBindMatricesAction_triggered(self, checked=False):
        """
        Slot method for the resetPreBindMatricesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        # Prompt user
        #
        reply = QtWidgets.QMessageBox.question(
            self,
            'Reset Influences',
            'Are you sure you want to reset the pre-bind matrices?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes and self.skin.isValid():

            self.skin.resetPreBindMatrices()

        else:

            log.info('Operation aborted...')

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
    def on_pasteAverageWeightsAction_triggered(self, checked=False):
        """
        Slot method for the pasteAverageWeightsAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteWeights(average=True)

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
    def on_relaxVerticesAction_triggered(self, checked=False):
        """
        Slot method for the relaxVerticesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.relaxVertices()

    @QtCore.Slot(bool)
    def on_blendVerticesAction_triggered(self, checked=False):
        """
        Slot method for the blendVerticesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.blendVertices()

    @QtCore.Slot(bool)
    def on_blendBetweenVerticesAction_triggered(self, checked=False):
        """
        Slot method for the blendBetweenVerticesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.blendBetweenVertices()

    @QtCore.Slot()
    def on_searchLineEdit_editingFinished(self):
        """
        Slot method for the searchLineEdit's `editingFinished` signal.

        :rtype: None
        """

        text = self.sender().text()
        filterWildcard = '*{text}*'.format(text=text)

        log.info(f'Searching for: {filterWildcard}')
        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

    @QtCore.Slot(bool)
    def on_addInfluencePushButton_clicked(self, checked=False):
        """
        Slot method for the addInfluencePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.addInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_removeInfluencePushButton_clicked(self, checked=False):
        """
        Slot method for the removeInfluencePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.removeInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTable_clicked(self, index):
        """
        Slot method for the influenceTable's `clicked` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Synchronize tables
        #
        sender = self.sender()

        if not self.precision:

            log.debug(f'Synchronizing "{sender.objectName()}" item view!')
            sender.synchronize()

    @QtCore.Slot(QtCore.QItemSelection)
    def on_influenceTable_highlighted(self, selected):
        """
        Slot method for the influenceTable's `synchronized` signal.

        :type selected: QtCore.QItemSelection
        :rtype: None
        """

        # Evaluate selected rows
        #
        sender = self.sender()

        rows = list({index.row() for index in selected.indexes()})
        numRows = len(rows)

        if numRows == 1:

            # Update current influence
            #
            self._currentInfluence = rows[0]

            # Select influence and redraw
            #
            self.skin.selectInfluence(self._currentInfluence)
            self.invalidateColors()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_weightTable_clicked(self, index):
        """
        Slot method for the weightTable's `clicked` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Check if precision mode is enabled
        # If not, then synchronize the selected influences
        #
        sender = self.sender()

        if not self.precision:

            log.debug(f'Synchronizing "{sender.objectName()}" item view!')
            sender.synchronize()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_weightTable_doubleClicked(self, index):
        """
        Slot method for the weightTable's `doubleClicked` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Check if precision mode is enabled
        # If so, then synchronize the selected influences
        #
        if self.precision:

            index = self.weightItemFilterModel.mapToSource(index)
            row = index.row()

            self.influenceTable.selectRow(row)

    @QtCore.Slot(QtCore.QPoint)
    def on_weightTable_customContextMenuRequested(self, point):
        """
        Slot method for the weightTable's `customContextMenuRequested` signal.

        :type point: QtCore.QPoint
        :rtype: None
        """

        numRows = self.weightItemModel.rowCount()
        hasSelection = self.weightTable.selectionModel().hasSelection()

        if numRows > 1 and hasSelection:

            return self.weightTableMenu.exec_(self.weightTable.mapToGlobal(point))

    @QtCore.Slot(bool)
    def on_mirrorPushButton_clicked(self, checked=False):
        """
        Slot method for the mirrorPushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        pull = modifiers == QtCore.Qt.ShiftModifier
        swap = modifiers == QtCore.Qt.AltModifier

        self.mirrorWeights(pull=pull, swap=swap)

    @QtCore.Slot(bool)
    def on_pruneDropDownButton_clicked(self, checked=False):
        """
        Slot method for the prunePushButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        tolerance = self.pruneSpinBox.value()
        self.pruneWeights(tolerance=tolerance)

    @QtCore.Slot(bool)
    def on_slabDropDownButton_clicked(self, checked=False):
        """
        Slot method for the slabDropDownButton's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        self.slabPasteWeights()

    @QtCore.Slot(int)
    def on_weightPresetButtonGroup_idClicked(self, index):
        """
        Slot method for the weightPresetButtonGroup's `idClicked` signal.

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
                self.__weight_presets__[index],
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(int)
    def on_percentPresetButtonGroup_idClicked(self, index):
        """
        Slot method for the weightPresetButtonGroup's `idClicked` signal.

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

            updates[vertexIndex] = self.skin.scaleWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                self.__percent_presets__[index],
                falloff=falloff
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_setWeightPushButton_clicked(self, checked=False):
        """
        Slot method for the setWeightPushButton's `clicked` signal.

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
        Slot method for the incrementWeightButtonGroup's `idClicked` signal.

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
        Slot method for the scaleWeightButtonGroup's `idClicked` signal.

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
    def on_precisionPushButton_toggled(self, checked=False):
        """
        Slot method for the precisionPushButton's `toggled` signal.

        :type checked: bool
        :rtype: None
        """

        # Toggle auto select behaviour
        #
        if checked:

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
    def on_selectAffectedVerticesAction_triggered(self, checked=False):
        """
        Slot method for the selectAffectedVerticesAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectAffectedVertices()

    @QtCore.Slot(bool)
    def on_usingEzSkinBlenderAction_triggered(self, checked=False):
        """
        Slot method for the usingEzSkinBlenderAction's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezskinblender')
    # endregion
