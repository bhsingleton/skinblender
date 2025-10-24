import os
import webbrowser

from Qt import QtCore, QtWidgets, QtGui, QtCompat
from dcc import fnscene, fnnode, fnmesh, fnskin, fnnotify
from dcc.ui import qsingletonwindow, qdropdownbutton, qpersistentmenu
from dcc.math import skinmath
from .dialogs import qeditinfluencesdialog, qloadweightsdialog
from .models import qinfluenceitemfiltermodel
from .views import qinfluenceview
from ..libs import skinutils
from ..decorators.contextguard import contextGuard

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
    instance = QSkinBlender.getInstance()

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
    instance = QSkinBlender.getInstance()

    if instance is None:

        return

    # Evaluate if instance is still valid
    #
    if QtCompat.isValid(instance):

        instance.undoBufferChanged(*args, **kwargs)

    else:

        log.warning('Unable to process undo callback!')


class QSkinBlender(qsingletonwindow.QSingletonWindow):
    """
    Overload of `QSingletonWindow` that manipulates skin weights.
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
        super(QSkinBlender, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._scene = fnscene.FnScene()
        self._skin = fnskin.FnSkin()
        self._mesh = fnmesh.FnMesh()
        self._currentInfluence = None
        self._softSelection = {}
        self._selection = []
        self._vertexWeights = {}
        self._weights = {}
        self._search = ''
        self._mirrorTolerance = 1e-3
        self._clipboard = None
        self._notifies = fnnotify.FnNotify()

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QSkinBlender, self).__setup_ui__(*args, **kwargs)

        # Initialize main window
        #
        self.setWindowTitle("|| Skin-Blender")
        self.setMinimumSize(QtCore.QSize(450, 450))

        # Initialize main menu-bar
        #
        mainMenuBar = QtWidgets.QMenuBar()
        mainMenuBar.setObjectName('mainMenuBar')

        self.setMenuBar(mainMenuBar)

        # Initialize file menu
        #
        self.fileMenu = mainMenuBar.addMenu('&File')
        self.fileMenu.setObjectName('fileMenu')
        self.fileMenu.setTearOffEnabled(True)

        self.saveWeightsAction = QtWidgets.QAction('Save Weights', parent=self.fileMenu)
        self.saveWeightsAction.setObjectName('saveWeightsAction')
        self.saveWeightsAction.triggered.connect(self.on_saveWeightsAction_triggered)

        self.loadWeightsAction = QtWidgets.QAction('Load Weights', parent=self.fileMenu)
        self.loadWeightsAction.setObjectName('loadWeightsAction')
        self.loadWeightsAction.triggered.connect(self.on_loadWeightsAction_triggered)

        self.fileMenu.addActions([self.saveWeightsAction, self.loadWeightsAction])

        # Initialize edit menu
        #
        self.editMenu = mainMenuBar.addMenu('&Edit')
        self.editMenu.setObjectName('editMenu')
        self.editMenu.setTearOffEnabled(True)

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

        # Initialize settings menu
        #
        self.settingsMenu = mainMenuBar.addMenu('&Settings')
        self.settingsMenu.setObjectName('settingsMenu')
        self.settingsMenu.setTearOffEnabled(True)

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
        self.debugMenu = mainMenuBar.addMenu('&Debug')
        self.debugMenu.setObjectName('debugMenu')
        self.debugMenu.setTearOffEnabled(True)

        self.resetActiveSelectionAction = QtWidgets.QAction('Reset Active Selection', parent=self.debugMenu)
        self.resetActiveSelectionAction.setObjectName('resetActiveSelectionAction')
        self.resetActiveSelectionAction.setCheckable(True)

        self.debugMenu.addAction(self.resetActiveSelectionAction)

        # Initialize help menu
        #
        self.helpMenu = mainMenuBar.addMenu('&Help')
        self.helpMenu.setObjectName('helpMenu')
        self.helpMenu.setTearOffEnabled(True)

        self.usingEzSkinBlenderAction = QtWidgets.QAction("Using Ez'Skin-Blender", parent=self.helpMenu)
        self.usingEzSkinBlenderAction.setObjectName('usingEzSkinBlenderAction')
        self.usingEzSkinBlenderAction.triggered.connect(self.on_usingEzSkinBlenderAction_triggered)

        self.helpMenu.addAction(self.usingEzSkinBlenderAction)

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        centralWidget = QtWidgets.QWidget()
        centralWidget.setObjectName('centralWidget')
        centralWidget.setLayout(centralLayout)

        self.setCentralWidget(centralWidget)

        # Initialize envelope group-box
        #
        self.envelopeLayout = QtWidgets.QVBoxLayout()
        self.envelopeLayout.setObjectName('envelopeLayout')

        self.envelopeGroupBox = QtWidgets.QGroupBox('')
        self.envelopeGroupBox.setObjectName('envelopeGroupBox')
        self.envelopeGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.envelopeGroupBox.setLayout(self.envelopeLayout)

        self.envelopePushButton = QtWidgets.QPushButton('Edit Envelope')
        self.envelopePushButton.setObjectName('envelopePushButton')
        self.envelopePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.envelopePushButton.setMinimumHeight(20)
        self.envelopePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.envelopePushButton.setStyleSheet('QPushButton:hover:checked { background-color: crimson; }\nQPushButton:checked { background-color: firebrick; border: none; }')
        self.envelopePushButton.setCheckable(True)
        self.envelopePushButton.toggled.connect(self.on_envelopePushButton_toggled)

        self.envelopeLayout.addWidget(self.envelopePushButton)

        centralLayout.addWidget(self.envelopeGroupBox)

        # Initialize influence widget
        #
        self.influenceLayout = QtWidgets.QVBoxLayout()
        self.influenceLayout.setObjectName('influenceLayout')
        self.influenceLayout.setContentsMargins(0, 0, 0, 0)

        self.influenceWidget = QtWidgets.QWidget()
        self.influenceWidget.setObjectName('influenceWidget')
        self.influenceWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.influenceWidget.setMinimumWidth(100)
        self.influenceWidget.setLayout(self.influenceLayout)
        self.influenceWidget.setEnabled(False)

        self.influenceHeader = QtWidgets.QGroupBox('Influences')
        self.influenceHeader.setObjectName('influenceHeader')
        self.influenceHeader.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.influenceHeader.setFlat(True)
        self.influenceHeader.setAlignment(QtCore.Qt.AlignCenter)

        self.searchLineEdit = QtWidgets.QLineEdit('')
        self.searchLineEdit.setObjectName('searchLineEdit')
        self.searchLineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.searchLineEdit.setFixedHeight(24)
        self.searchLineEdit.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.searchLineEdit.setPlaceholderText('Filter Influences...')
        self.searchLineEdit.setClearButtonEnabled(True)
        self.searchLineEdit.textChanged.connect(self.on_searchLineEdit_textChanged)

        self.influenceTable = qinfluenceview.QInfluenceView()
        self.influenceTable.setObjectName('influenceTable')
        self.influenceTable.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.influenceTable.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.influenceTable.setStyleSheet('QTableView::item { height: 24; text-align: center; }')
        self.influenceTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.influenceTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.influenceTable.setAlternatingRowColors(True)
        self.influenceTable.setShowGrid(True)
        self.influenceTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.influenceTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.influenceTable.clicked.connect(self.on_influenceTable_clicked)
        self.influenceTable.highlighted.connect(self.on_influenceTable_highlighted)

        itemPrototype = QtGui.QStandardItem('')
        itemPrototype.setSizeHint(QtCore.QSize(72, 24))
        itemPrototype.setTextAlignment(QtCore.Qt.AlignCenter)

        self.influenceItemModel = QtGui.QStandardItemModel(parent=self.influenceTable)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Name'])
        self.influenceItemModel.setItemPrototype(itemPrototype)

        self.influenceItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.influenceTable)
        self.influenceItemFilterModel.setObjectName('influenceItemFilterModel')
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)

        self.influenceTable.setModel(self.influenceItemFilterModel)

        horizontalHeader = self.influenceTable.horizontalHeader()  # type: QtWidgets.QHeaderView
        horizontalHeader.setStretchLastSection(True)
        horizontalHeader.setVisible(False)

        verticalHeader = self.influenceTable.verticalHeader()  # type: QtWidgets.QHeaderView
        verticalHeader.setDefaultSectionSize(24)
        verticalHeader.setMinimumSectionSize(24)
        verticalHeader.setStretchLastSection(False)
        verticalHeader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        verticalHeader.setFixedWidth(24)
        verticalHeader.setVisible(True)

        self.addInfluencePushButton = QtWidgets.QPushButton('Add')
        self.addInfluencePushButton.setObjectName('addInfluencePushButton')
        self.addInfluencePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.addInfluencePushButton.setFixedHeight(20)
        self.addInfluencePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.addInfluencePushButton.clicked.connect(self.on_addInfluencePushButton_clicked)

        self.removeInfluencePushButton = QtWidgets.QPushButton('Remove')
        self.removeInfluencePushButton.setObjectName('removeInfluencePushButton')
        self.removeInfluencePushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.removeInfluencePushButton.setFixedHeight(20)
        self.removeInfluencePushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.removeInfluencePushButton.clicked.connect(self.on_removeInfluencePushButton_clicked)

        self.influenceButtonLayout = QtWidgets.QGridLayout()
        self.influenceButtonLayout.setObjectName('influenceButtonLayout')
        self.influenceButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.influenceButtonLayout.addWidget(self.addInfluencePushButton, 0, 0)
        self.influenceButtonLayout.addWidget(self.removeInfluencePushButton, 0, 1)

        self.influenceLayout.addWidget(self.influenceHeader)
        self.influenceLayout.addWidget(self.searchLineEdit)
        self.influenceLayout.addWidget(self.influenceTable)
        self.influenceLayout.addLayout(self.influenceButtonLayout)

        # Initialize weight widget
        #
        self.weightLayout = QtWidgets.QVBoxLayout()
        self.weightLayout.setObjectName('weightLayout')
        self.weightLayout.setContentsMargins(0, 0, 0, 0)

        self.weightWidget = QtWidgets.QWidget()
        self.weightWidget.setObjectName('weightWidget')
        self.weightWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.weightWidget.setMinimumWidth(100)
        self.weightWidget.setLayout(self.weightLayout)
        self.weightWidget.setEnabled(False)

        self.weightHeader = QtWidgets.QGroupBox('Weights')
        self.weightHeader.setObjectName('weightHeader')
        self.weightHeader.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightHeader.setFlat(True)
        self.weightHeader.setAlignment(QtCore.Qt.AlignCenter)
        
        self.weightTable = qinfluenceview.QInfluenceView()
        self.weightTable.setObjectName('weightTable')
        self.weightTable.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.weightTable.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.weightTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.weightTable.setStyleSheet('QTableView::item { height: 24; text-align: center; }')
        self.weightTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.weightTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.weightTable.setAlternatingRowColors(True)
        self.weightTable.setShowGrid(True)
        self.weightTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.weightTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.weightTable.clicked.connect(self.on_weightTable_clicked)
        self.weightTable.doubleClicked.connect(self.on_weightTable_doubleClicked)
        self.weightTable.customContextMenuRequested.connect(self.on_weightTable_customContextMenuRequested)

        itemPrototype = QtGui.QStandardItem('')
        itemPrototype.setSizeHint(QtCore.QSize(72, 24))
        itemPrototype.setTextAlignment(QtCore.Qt.AlignCenter)

        self.weightItemModel = QtGui.QStandardItemModel(parent=self.weightTable)
        self.weightItemModel.setObjectName('weightItemModel')
        self.weightItemModel.setHorizontalHeaderLabels(['Name', 'Weight'])
        self.weightItemModel.setItemPrototype(itemPrototype)

        self.weightItemFilterModel = qinfluenceitemfiltermodel.QInfluenceItemFilterModel(parent=self.weightTable)
        self.weightItemFilterModel.setObjectName('weightItemFilterModel')
        self.weightItemFilterModel.setSourceModel(self.weightItemModel)

        self.weightTable.setModel(self.weightItemFilterModel)

        horizontalHeader = self.weightTable.horizontalHeader()  # type: QtWidgets.QHeaderView
        horizontalHeader.setStretchLastSection(False)
        horizontalHeader.resizeSection(1, 80)
        horizontalHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        horizontalHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        horizontalHeader.setVisible(True)

        verticalHeader = self.weightTable.verticalHeader()  # type: QtWidgets.QHeaderView
        verticalHeader.setDefaultSectionSize(24)
        verticalHeader.setMinimumSectionSize(24)
        verticalHeader.setStretchLastSection(False)
        verticalHeader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        verticalHeader.setFixedWidth(24)
        verticalHeader.setVisible(True)

        self.precisionPushButton = QtWidgets.QPushButton('Precision')
        self.precisionPushButton.setObjectName('precisionPushButton')
        self.precisionPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.precisionPushButton.setFixedHeight(20)
        self.precisionPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.precisionPushButton.setStyleSheet('QPushButton:checked { background-color: firebrick; border: none; }\nQPushButton:hover:checked { background-color: crimson; }')
        self.precisionPushButton.setCheckable(True)
        self.precisionPushButton.toggled.connect(self.on_precisionPushButton_toggled)

        self.weightLayout.addWidget(self.weightHeader)
        self.weightLayout.addWidget(self.weightTable)
        self.weightLayout.addWidget(self.precisionPushButton)

        # Initialize options widget
        #
        self.optionsLayout = QtWidgets.QVBoxLayout()
        self.optionsLayout.setObjectName('optionsLayout')
        self.optionsLayout.setContentsMargins(0, 0, 0, 0)

        self.optionsWidget = QtWidgets.QWidget()
        self.optionsWidget.setObjectName('optionsWidget')
        self.optionsWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.optionsWidget.setLayout(self.optionsLayout)

        self.optionsHeader = QtWidgets.QGroupBox('Options')
        self.optionsHeader.setObjectName('optionsHeader')
        self.optionsHeader.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.optionsHeader.setFlat(True)
        self.optionsHeader.setAlignment(QtCore.Qt.AlignCenter)

        self.mirrorPushButton = QtWidgets.QPushButton('Mirror')
        self.mirrorPushButton.setObjectName('mirrorPushButton')
        self.mirrorPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.mirrorPushButton.setFixedHeight(20)
        self.mirrorPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.mirrorPushButton.setToolTip('Mirrors the selected vertices. [Shift] Pulls the opposite vertices. [Alt] Swaps mirrors the selected influences. [Ctrl] Transfers between two selected vertices.')
        self.mirrorPushButton.clicked.connect(self.on_mirrorPushButton_clicked)

        self.pruneDropDownButton = qdropdownbutton.QDropDownButton('Prune')
        self.pruneDropDownButton.setObjectName('pruneDropDownButton')
        self.pruneDropDownButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.pruneDropDownButton.setFixedHeight(20)
        self.pruneDropDownButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.pruneDropDownButton.setToolTip('Removes any influences weights within the specified threshold.')
        self.pruneDropDownButton.clicked.connect(self.on_pruneDropDownButton_clicked)

        self.slabDropDownButton = qdropdownbutton.QDropDownButton('Slab')
        self.slabDropDownButton.setObjectName('slabDropDownButton')
        self.slabDropDownButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.slabDropDownButton.setFixedHeight(20)
        self.slabDropDownButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.slabDropDownButton.setToolTip('Copies the selected weights to the nearest vertex.')
        self.slabDropDownButton.clicked.connect(self.on_slabDropDownButton_clicked)

        self.mirrorButtonLayout = QtWidgets.QHBoxLayout()
        self.mirrorButtonLayout.setObjectName('mirrorButtonLayout')
        self.mirrorButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.mirrorButtonLayout.addWidget(self.mirrorPushButton)
        self.mirrorButtonLayout.addWidget(self.pruneDropDownButton)
        self.mirrorButtonLayout.addWidget(self.slabDropDownButton)

        self.weightPresetPushButton1 = QtWidgets.QPushButton('0')
        self.weightPresetPushButton1.setObjectName('weightPresetPushButton1')
        self.weightPresetPushButton1.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton1.setFixedHeight(20)
        self.weightPresetPushButton1.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton2 = QtWidgets.QPushButton('.1')
        self.weightPresetPushButton2.setObjectName('weightPresetPushButton2')
        self.weightPresetPushButton2.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton2.setFixedHeight(20)
        self.weightPresetPushButton2.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton3 = QtWidgets.QPushButton('.25')
        self.weightPresetPushButton3.setObjectName('weightPresetPushButton3')
        self.weightPresetPushButton3.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton3.setFixedHeight(20)
        self.weightPresetPushButton3.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton4 = QtWidgets.QPushButton('.5')
        self.weightPresetPushButton4.setObjectName('weightPresetPushButton4')
        self.weightPresetPushButton4.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton4.setFixedHeight(20)
        self.weightPresetPushButton4.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton5 = QtWidgets.QPushButton('.75')
        self.weightPresetPushButton5.setObjectName('weightPresetPushButton5')
        self.weightPresetPushButton5.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton5.setFixedHeight(20)
        self.weightPresetPushButton5.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton6 = QtWidgets.QPushButton('.9')
        self.weightPresetPushButton6.setObjectName('weightPresetPushButton6')
        self.weightPresetPushButton6.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton6.setFixedHeight(20)
        self.weightPresetPushButton6.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetPushButton7 = QtWidgets.QPushButton('1')
        self.weightPresetPushButton7.setObjectName('weightPresetPushButton7')
        self.weightPresetPushButton7.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.weightPresetPushButton7.setFixedHeight(20)
        self.weightPresetPushButton7.setFocusPolicy(QtCore.Qt.NoFocus)

        self.weightPresetButtonGroup = QtWidgets.QButtonGroup(self.optionsWidget)
        self.weightPresetButtonGroup.setObjectName('weightPresetButtonGroup')
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton1, id=0)  # 0.0
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton2, id=1)  # 0.1
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton3, id=2)  # 0.25
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton4, id=3)  # 0.5
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton5, id=4)  # 0.75
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton6, id=5)  # 0.9
        self.weightPresetButtonGroup.addButton(self.weightPresetPushButton7, id=6)  # 1.0
        self.weightPresetButtonGroup.idClicked.connect(self.on_weightPresetButtonGroup_idClicked)

        self.weightPresetButtonLayout = QtWidgets.QHBoxLayout()
        self.weightPresetButtonLayout.setObjectName('weightPresetButtonLayout')
        self.weightPresetButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.weightPresetButtonLayout.setSpacing(1)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton1)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton2)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton3)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton4)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton5)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton6)
        self.weightPresetButtonLayout.addWidget(self.weightPresetPushButton7)

        self.percentPresetPushButton1 = QtWidgets.QPushButton('10%')
        self.percentPresetPushButton1.setObjectName('percentPresetPushButton1')
        self.percentPresetPushButton1.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.percentPresetPushButton1.setFixedHeight(20)
        self.percentPresetPushButton1.setFocusPolicy(QtCore.Qt.NoFocus)

        self.percentPresetPushButton2 = QtWidgets.QPushButton('25%')
        self.percentPresetPushButton2.setObjectName('percentPresetPushButton2')
        self.percentPresetPushButton2.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.percentPresetPushButton2.setFixedHeight(20)
        self.percentPresetPushButton2.setFocusPolicy(QtCore.Qt.NoFocus)

        self.percentPresetPushButton3 = QtWidgets.QPushButton('50%')
        self.percentPresetPushButton3.setObjectName('percentPresetPushButton3')
        self.percentPresetPushButton3.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.percentPresetPushButton3.setFixedHeight(20)
        self.percentPresetPushButton3.setFocusPolicy(QtCore.Qt.NoFocus)

        self.percentPresetPushButton4 = QtWidgets.QPushButton('75%')
        self.percentPresetPushButton4.setObjectName('percentPresetPushButton4')
        self.percentPresetPushButton4.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.percentPresetPushButton4.setFixedHeight(20)
        self.percentPresetPushButton4.setFocusPolicy(QtCore.Qt.NoFocus)

        self.percentPresetPushButton5 = QtWidgets.QPushButton('100%')
        self.percentPresetPushButton5.setObjectName('percentPresetPushButton5')
        self.percentPresetPushButton5.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.percentPresetPushButton5.setFixedHeight(20)
        self.percentPresetPushButton5.setFocusPolicy(QtCore.Qt.NoFocus)

        self.percentPresetButtonGroup = QtWidgets.QButtonGroup(self.optionsWidget)
        self.percentPresetButtonGroup.setObjectName('percentPresetButtonGroup')
        self.percentPresetButtonGroup.addButton(self.percentPresetPushButton1, id=0)  # 0.1
        self.percentPresetButtonGroup.addButton(self.percentPresetPushButton2, id=1)  # 0.25
        self.percentPresetButtonGroup.addButton(self.percentPresetPushButton3, id=2)  # 0.5
        self.percentPresetButtonGroup.addButton(self.percentPresetPushButton4, id=3)  # 0.75
        self.percentPresetButtonGroup.addButton(self.percentPresetPushButton5, id=4)  # 1.0
        self.percentPresetButtonGroup.idClicked.connect(self.on_percentPresetButtonGroup_idClicked)

        self.percentPresetButtonLayout = QtWidgets.QHBoxLayout()
        self.percentPresetButtonLayout.setObjectName('percentButtonLayout')
        self.percentPresetButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.percentPresetButtonLayout.setSpacing(1)
        self.percentPresetButtonLayout.addWidget(self.percentPresetPushButton1)
        self.percentPresetButtonLayout.addWidget(self.percentPresetPushButton2)
        self.percentPresetButtonLayout.addWidget(self.percentPresetPushButton3)
        self.percentPresetButtonLayout.addWidget(self.percentPresetPushButton4)
        self.percentPresetButtonLayout.addWidget(self.percentPresetPushButton5)

        self.setWeightLabel = QtWidgets.QLabel('Set:')
        self.setWeightLabel.setObjectName('setWeightLabel')
        self.setWeightLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.setWeightLabel.setFixedSize(QtCore.QSize(60, 20))
        self.setWeightLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.setWeightSpinBox = QtWidgets.QDoubleSpinBox()
        self.setWeightSpinBox.setObjectName('setWeightSpinBox')
        self.setWeightSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.setWeightSpinBox.setFixedHeight(20)
        self.setWeightSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setWeightSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.setWeightSpinBox.setMinimum(0.0)
        self.setWeightSpinBox.setMaximum(1.0)
        self.setWeightSpinBox.setSingleStep(0.01)
        self.setWeightSpinBox.setValue(0.05)

        self.setWeightPushButton = QtWidgets.QPushButton('Apply')
        self.setWeightPushButton.setObjectName('setWeightPushButton')
        self.setWeightPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed))
        self.setWeightPushButton.setFixedHeight(20)
        self.setWeightPushButton.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setWeightPushButton.clicked.connect(self.on_setWeightPushButton_clicked)

        self.incrementWeightLabel = QtWidgets.QLabel('Increment:')
        self.incrementWeightLabel.setObjectName('incrementWeightLabel')
        self.incrementWeightLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.incrementWeightLabel.setFixedSize(QtCore.QSize(60, 20))
        self.incrementWeightLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.incrementWeightSpinBox = QtWidgets.QDoubleSpinBox()
        self.incrementWeightSpinBox.setObjectName('incrementWeightSpinBox')
        self.incrementWeightSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.incrementWeightSpinBox.setFixedHeight(20)
        self.incrementWeightSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.incrementWeightSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.incrementWeightSpinBox.setMinimum(0.0)
        self.incrementWeightSpinBox.setMaximum(1.0)
        self.incrementWeightSpinBox.setSingleStep(0.01)
        self.incrementWeightSpinBox.setValue(0.05)

        self.incrementWeightPushButton1 = QtWidgets.QPushButton('+')
        self.incrementWeightPushButton1.setObjectName('incrementWeightPushButton1')
        self.incrementWeightPushButton1.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.incrementWeightPushButton1.setFixedSize(QtCore.QSize(20, 20))
        self.incrementWeightPushButton1.setFocusPolicy(QtCore.Qt.NoFocus)

        self.incrementWeightPushButton2 = QtWidgets.QPushButton('-')
        self.incrementWeightPushButton2.setObjectName('incrementWeightPushButton2')
        self.incrementWeightPushButton2.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.incrementWeightPushButton2.setFixedSize(QtCore.QSize(20, 20))
        self.incrementWeightPushButton2.setFocusPolicy(QtCore.Qt.NoFocus)

        self.incrementWeightButtonGroup = QtWidgets.QButtonGroup(self.optionsWidget)
        self.incrementWeightButtonGroup.setObjectName('incrementWeightButtonGroup')
        self.incrementWeightButtonGroup.addButton(self.incrementWeightPushButton1, id=0)  # +
        self.incrementWeightButtonGroup.addButton(self.incrementWeightPushButton2, id=1)  # -
        self.incrementWeightButtonGroup.idClicked.connect(self.on_incrementWeightButtonGroup_idClicked)

        self.incrementWeightButtonLayout = QtWidgets.QHBoxLayout()
        self.incrementWeightButtonLayout.setObjectName('incrementWeightButtonLayout')
        self.incrementWeightButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.incrementWeightButtonLayout.setSpacing(1)
        self.incrementWeightButtonLayout.addWidget(self.incrementWeightPushButton1)
        self.incrementWeightButtonLayout.addWidget(self.incrementWeightPushButton2)

        self.scaleWeightLabel = QtWidgets.QLabel('Scale:')
        self.scaleWeightLabel.setObjectName('scaleWeightLabel')
        self.scaleWeightLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.scaleWeightLabel.setFixedSize(QtCore.QSize(60, 20))
        self.scaleWeightLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.scaleWeightSpinBox = QtWidgets.QDoubleSpinBox()
        self.scaleWeightSpinBox.setObjectName('scaleWeightSpinBox')
        self.scaleWeightSpinBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.scaleWeightSpinBox.setFixedHeight(20)
        self.scaleWeightSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.scaleWeightSpinBox.setAlignment(QtCore.Qt.AlignCenter)
        self.scaleWeightSpinBox.setMinimum(0.0)
        self.scaleWeightSpinBox.setMaximum(1.0)
        self.scaleWeightSpinBox.setSingleStep(0.01)
        self.scaleWeightSpinBox.setValue(0.1)

        self.scaleWeightPushButton1 = QtWidgets.QPushButton('+')
        self.scaleWeightPushButton1.setObjectName('scaleWeightPushButton1')
        self.scaleWeightPushButton1.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.scaleWeightPushButton1.setFixedSize(QtCore.QSize(20, 20))
        self.scaleWeightPushButton1.setFocusPolicy(QtCore.Qt.NoFocus)

        self.scaleWeightPushButton2 = QtWidgets.QPushButton('-')
        self.scaleWeightPushButton2.setObjectName('scaleWeightPushButton2')
        self.scaleWeightPushButton2.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.scaleWeightPushButton2.setFixedSize(QtCore.QSize(20, 20))
        self.scaleWeightPushButton2.setFocusPolicy(QtCore.Qt.NoFocus)

        self.scaleWeightButtonGroup = QtWidgets.QButtonGroup(self.optionsWidget)
        self.scaleWeightButtonGroup.setObjectName('scaleWeightButtonGroup')
        self.scaleWeightButtonGroup.addButton(self.scaleWeightPushButton1, id=0)  # +
        self.scaleWeightButtonGroup.addButton(self.scaleWeightPushButton2, id=1)  # -
        self.scaleWeightButtonGroup.idClicked.connect(self.on_scaleWeightButtonGroup_idClicked)

        self.scaleWeightButtonLayout = QtWidgets.QHBoxLayout()
        self.scaleWeightButtonLayout.setObjectName('scaleWeightButtonLayout')
        self.scaleWeightButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.scaleWeightButtonLayout.setSpacing(1)
        self.scaleWeightButtonLayout.addWidget(self.scaleWeightPushButton1)
        self.scaleWeightButtonLayout.addWidget(self.scaleWeightPushButton2)

        self.editWeightButtonLayout = QtWidgets.QGridLayout()
        self.editWeightButtonLayout.setObjectName('editWeightButtonLayout')
        self.editWeightButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.editWeightButtonLayout.addWidget(self.setWeightLabel, 0, 0)
        self.editWeightButtonLayout.addWidget(self.setWeightSpinBox, 0, 1)
        self.editWeightButtonLayout.addWidget(self.setWeightPushButton, 0, 2)
        self.editWeightButtonLayout.addWidget(self.incrementWeightLabel, 1, 0)
        self.editWeightButtonLayout.addWidget(self.incrementWeightSpinBox, 1, 1)
        self.editWeightButtonLayout.addLayout(self.incrementWeightButtonLayout, 1, 2)
        self.editWeightButtonLayout.addWidget(self.scaleWeightLabel, 2, 0)
        self.editWeightButtonLayout.addWidget(self.scaleWeightSpinBox, 2, 1)
        self.editWeightButtonLayout.addLayout(self.scaleWeightButtonLayout, 2, 2)

        self.optionsLayout.addWidget(self.optionsHeader)
        self.optionsLayout.addLayout(self.mirrorButtonLayout)
        self.optionsLayout.addLayout(self.weightPresetButtonLayout)
        self.optionsLayout.addLayout(self.percentPresetButtonLayout)
        self.optionsLayout.addLayout(self.editWeightButtonLayout)
        
        self.weightLayout.addWidget(self.optionsWidget)

        # Initialize weight table context menu
        #
        self.weightTableMenu = QtWidgets.QMenu(parent=self.weightTable)
        self.weightTableMenu.setObjectName('weightTableMenu')

        self.selectAffectedVerticesAction = QtWidgets.QAction('&Select Affected Vertices', self.weightTableMenu)
        self.selectAffectedVerticesAction.setObjectName('selectAffectedVerticesAction')
        self.selectAffectedVerticesAction.triggered.connect(self.on_selectAffectedVerticesAction_triggered)

        self.weightTableMenu.addActions([self.selectAffectedVerticesAction])

        # Initialize prune drop-down menu
        #
        self.pruneMenu = QtWidgets.QMenu(parent=self.pruneDropDownButton)
        self.pruneMenu.setObjectName('pruneMenu')

        self.pruneSpinBox = QtWidgets.QDoubleSpinBox(parent=self.pruneMenu)
        self.pruneSpinBox.setObjectName('pruneSpinBox')
        self.pruneSpinBox.setFocusPolicy(QtCore.Qt.ClickFocus)
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

        # Initialize slab drop-down menu
        #
        self.slabMenu = qpersistentmenu.QPersistentMenu(parent=self.slabDropDownButton)
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

        # Initialize splitter widget
        #
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setObjectName('splitter')
        self.splitter.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.splitter.addWidget(self.influenceWidget)
        self.splitter.addWidget(self.weightWidget)

        centralLayout.addWidget(self.splitter)

        # Establish table buddies
        #
        self.weightTable.setBuddy(self.influenceTable)
        self.influenceTable.setBuddy(self.weightTable)

        # Connect enabled slots
        #
        self.envelopePushButton.toggled.connect(self.influenceWidget.setEnabled)
        self.envelopePushButton.toggled.connect(self.weightWidget.setEnabled)
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
    def mesh(self):
        """
        Getter method that returns the mesh function set.

        :rtype: fnmesh.FnMesh
        """

        return self._mesh

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

        if isinstance(axis, int):

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

        if isinstance(tolerance, (int, float)):

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

        if isinstance(option, int):

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

        if isinstance(blendByDistance, bool):

            self.blendByDistanceAction.setChecked(blendByDistance)

    @property
    def mirrorTolerance(self):
        """
        Getter method that returns the mirror tolerance.

        :rtype: float
        """

        return self._mirrorTolerance

    @mirrorTolerance.setter
    def mirrorTolerance(self, tolerance):
        """
        Setter method that updates the mirror tolerance.

        :type tolerance: float
        :rtype: None
        """

        if isinstance(tolerance, (int, float)):

            self._mirrorTolerance = tolerance

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

    # region Methods
    def addCallbacks(self):
        """
        Adds any callbacks required by this window.

        :rtype: None
        """

        # Check if notifies already exist
        #
        hasNotifies = len(self._notifies) > 0

        if not hasNotifies:

            self._notifies.addSelectionChangedNotify(onActiveSelectionChanged)
            self._notifies.addUndoNotify(onUndoBufferChanged)
            self._notifies.addRedoNotify(onUndoBufferChanged)

    def removeCallbacks(self):
        """
        Removes any callbacks created by this window.

        :rtype: None
        """

        # Check if notifies exist
        #
        hasNotifies = len(self._notifies) > 0

        if hasNotifies:

            self._notifies.clear()

        # Exit envelope mode
        #
        if self.envelopePushButton.isChecked():

            self.envelopePushButton.setChecked(False)

    def saveSettings(self, settings):
        """
        Saves the user settings.

        :type settings: QtCore.QSettings
        :rtype: None
        """

        # Call parent method
        #
        super(QSkinBlender, self).saveSettings(settings)

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
        super(QSkinBlender, self).loadSettings(settings)

        # Load user settings
        #
        self.mirrorAxis = settings.value('editor/mirrorAxis', defaultValue=0, type=int)
        self.mirrorTolerance = settings.value('editor/mirrorTolerance', defaultValue='1e-3', type=float)
        self.blendByDistance = bool(settings.value('editor/blendByDistance', defaultValue=0, type=int))
        self.pruneTolerance = settings.value('editor/pruneTolerance', defaultValue='1e-2', type=float)
        self.slabOption = settings.value('editor/slabOption', defaultValue=0, type=int)

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

    @contextGuard
    def copyWeights(self):
        """
        Copies the skin weights from the current skin.

        :rtype: None
        """

        self.skin.copyWeights()

    @contextGuard
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

    @contextGuard
    def slabPasteWeights(self):
        """
        Slab pastes the active component selection.

        :rtype: None
        """

        self.skin.slabPasteWeights(self.selection(), mode=self.slabOption)
        self.invalidateWeights()

    @contextGuard
    def setWeights(self, amount):
        """
        Sets the selected vertex weights.

        :type amount: float
        :rtype: None
        """

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        vertexWeights = self.vertexWeights()
        maxInfluences = self.skin.maxInfluences()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = skinmath.setWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff,
                maxInfluences=maxInfluences
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @contextGuard
    def incrementWeights(self, amount):
        """
        Increments the selected vertex weights.

        :type amount: float
        :rtype: None
        """

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        vertexWeights = self.vertexWeights()
        maxInfluences = self.skin.maxInfluences()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = skinmath.incrementWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff,
                maxInfluences=maxInfluences
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
        self.invalidateWeights()

    @contextGuard
    def scaleWeights(self, amount):
        """
        Scales the selected vertex weights.

        :type amount: float
        :rtype: None
        """

        # Iterate through selection
        #
        currentInfluence = self.currentInfluence()
        sourceInfluences = self.sourceInfluences()
        vertexWeights = self.vertexWeights()
        maxInfluences = self.skin.maxInfluences()

        updates = {}

        for (vertexIndex, falloff) in self._softSelection.items():

            updates[vertexIndex] = skinmath.scaleWeights(
                vertexWeights[vertexIndex],
                currentInfluence,
                sourceInfluences,
                amount,
                falloff=falloff,
                maxInfluences=maxInfluences
            )

        # Assign updates to skin
        #
        self.skin.applyVertexWeights(updates)
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

    @contextGuard
    def relaxVertices(self):
        """
        Relaxes the selected vertex weights.

        :rtype: None
        """

        self.skin.relaxVertices(self.selection())
        self.invalidateWeights()

    @contextGuard
    def blendVertices(self):
        """
        Blends the selected vertex weights.

        :rtype: None
        """

        self.skin.blendVertices(self.selection())
        self.invalidateWeights()

    @contextGuard
    def blendBetweenVertices(self):
        """
        Blends between the selected vertex pairs.

        :rtype: None
        """

        self.skin.blendBetweenVertices(self.selection(), blendByDistance=self.blendByDistance)
        self.invalidateWeights()

    @contextGuard
    def pruneWeights(self, tolerance=1e-3):
        """
        Prunes any influences below the specified tolerance.

        :type tolerance: float
        :rtype: None
        """

        self.skin.pruneVertices(self.selection(), tolerance=tolerance)
        self.invalidateWeights()

    @contextGuard
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

    @contextGuard
    def swapWeights(self):
        """
        Swaps the active component selection.

        :rtype: None
        """

        # Swap vertex weights
        #
        vertexWeights = self.skin.vertexWeights(*self.selection())
        swappedWeights = {vertexIndex: self.skin.mirrorWeights(influenceWeights) for (vertexIndex, influenceWeights) in vertexWeights.items()}

        # Apply swapped weights
        #
        self.skin.applyVertexWeights(swappedWeights)
        self.invalidateWeights()

    @contextGuard
    def transferWeights(self):
        """
        Transfer the vertex weights the active component selection.

        :rtype: None
        """

        # Evaluate selection
        #
        selection = self.selection()
        selectionCount = len(selection)

        if selectionCount != 2:

            return

        # Transfer vertex weight to other vertex
        #
        vertexIndex, otherVertexIndex = selection
        vertexWeights = self.skin.vertexWeights(vertexIndex)

        transferredWeights = {otherVertexIndex: self.skin.mirrorWeights(vertexWeights[vertexIndex])}

        # Apply transferred weights
        #
        self.skin.applyVertexWeights(transferredWeights)
        self.invalidateWeights()

    @contextGuard
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

    @contextGuard
    def invalidateInfluences(self):
        """
        Invalidates the influence item model.

        :rtype: None
        """

        # Resize item model
        #
        influences = self.skin.influences()
        maxInfluenceId = influences.lastIndex()
        rowCount = maxInfluenceId + 1

        self.influenceItemModel.setVerticalHeaderLabels(list(map(str, range(rowCount))))

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
            index = self.influenceItemModel.index(i, 0)
            self.influenceItemModel.setData(index, influenceName, role=QtCore.Qt.DisplayRole)

        # Invalidate filter model
        #
        self.influenceItemFilterModel.invalidateFilter()

    @contextGuard
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

    @contextGuard
    def invalidateWeights(self, *args, **kwargs):
        """
        Invalidates the weight item model.

        :rtype: None
        """

        # Resize item model
        #
        influences = self.skin.influences()
        maxInfluenceId = influences.lastIndex()
        rowCount = maxInfluenceId + 1

        self.weightItemModel.setVerticalHeaderLabels(list(map(str, range(rowCount))))

        # Get vertex weights
        #
        self._vertexWeights = self.skin.vertexWeights(*self._selection)

        if len(self._vertexWeights) > 0:

            self._weights = skinmath.averageWeights(*list(self._vertexWeights.values()))

        else:

            self._weights = {}

        # Iterate through influences
        #
        for i in range(maxInfluenceId + 1):

            # Get influence name and weight
            #
            influence = influences[i]
            influenceName = ''

            if influence is not None:

                influenceName = influence.name()

            weight = self._weights.get(i, None)
            influenceWeight = ''

            if isinstance(weight, (int, float)):

                influenceWeight = str(round(weight, 2))

            # Update item data
            #
            index = self.weightItemModel.index(i, 0)
            self.weightItemModel.setData(index, influenceName, role=QtCore.Qt.DisplayRole)

            index = self.weightItemModel.index(i, 1)
            self.weightItemModel.setData(index, influenceWeight, role=QtCore.Qt.DisplayRole)

        # Invalidate filter model
        #
        self.weightItemFilterModel.invalidateFilter()
        self.invalidateColors()

    @contextGuard
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
        Slot method for the `envelopePushButton` widget's `toggled` signal.

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

            # Edit button text
            #
            self.mesh.setObject(self.skin.shape())
            sender.setText(f'Editing {self.mesh.name()}')

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

            # Reset button text
            #
            self.mesh.resetObject()
            sender.setText('Edit Envelope')

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
        Slot method for the `saveWeightsAction` widget's `triggered` signal.

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
        Slot method for the `loadWeightsAction` widget's `triggered` signal.

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
            qloadweightsdialog.loadWeights(selection[0], filePath, parent=self)

        else:

            log.info('Operation aborted...')

    @QtCore.Slot(bool)
    def on_resetIntermediateObjectAction_triggered(self, checked=False):
        """
        Slot method for the `resetIntermediateObjectAction` widget's `triggered` signal.

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
        Slot method for the `resetPreBindMatricesAction` widget's `triggered` signal.

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
        Slot method for the `setMirrorToleranceAction` widget's `triggered` signal.

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
        Slot method for the `copyWeightsAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.copyWeights()

    @QtCore.Slot(bool)
    def on_pasteWeightsAction_triggered(self, checked=False):
        """
        Slot method for the `pasteWeightsAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteWeights()

    @QtCore.Slot(bool)
    def on_pasteAverageWeightsAction_triggered(self, checked=False):
        """
        Slot method for the `pasteAverageWeightsAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteWeights(average=True)

    @QtCore.Slot(bool)
    def on_copySkinAction_triggered(self, checked=False):
        """
        Slot method for the `copySkinAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.copySkin()

    @QtCore.Slot(bool)
    def on_pasteSkinAction_triggered(self, checked=False):
        """
        Slot method for the `pasteSkinAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.pasteSkin()

    @QtCore.Slot(bool)
    def on_relaxVerticesAction_triggered(self, checked=False):
        """
        Slot method for the `relaxVerticesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.relaxVertices()

    @QtCore.Slot(bool)
    def on_blendVerticesAction_triggered(self, checked=False):
        """
        Slot method for the `blendVerticesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.blendVertices()

    @QtCore.Slot(bool)
    def on_blendBetweenVerticesAction_triggered(self, checked=False):
        """
        Slot method for the `blendBetweenVerticesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.blendBetweenVertices()

    @QtCore.Slot()
    def on_searchLineEdit_textChanged(self):
        """
        Slot method for the `searchLineEdit` widget's `textChanged` signal.

        :rtype: None
        """

        text = self.sender().text()
        filterWildcard = '*{text}*'.format(text=text)

        log.info(f'Searching for: {filterWildcard}')
        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

    @QtCore.Slot(bool)
    def on_addInfluencePushButton_clicked(self, checked=False):
        """
        Slot method for the `addInfluencePushButton` widget's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.addInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(bool)
    def on_removeInfluencePushButton_clicked(self, checked=False):
        """
        Slot method for the `removeInfluencePushButton` widget's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        qeditinfluencesdialog.removeInfluences(self.skin.object(), parent=self)
        self.invalidateInfluences()
        self.invalidateWeights()

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTable_clicked(self, index):
        """
        Slot method for the `influenceTable` widget's `clicked` signal.

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
        Slot method for the `influenceTable` widget's `synchronized` signal.

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
        Slot method for the `weightTable` widget's `clicked` signal.

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
        Slot method for the `weightTable` widget's `doubleClicked` signal.

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
        Slot method for the `weightTable` widget's `customContextMenuRequested` signal.

        :type point: QtCore.QPoint
        :rtype: None
        """

        numRows = self.weightItemModel.rowCount()
        hasSelection = self.weightTable.selectionModel().hasSelection()

        if numRows > 1 and hasSelection:

            return self.weightTableMenu.exec_(self.weightTable.mapToGlobal(point))

    @QtCore.Slot()
    def on_mirrorPushButton_clicked(self):
        """
        Slot method for the `mirrorPushButton` widget's `clicked` signal.

        :rtype: None
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.ControlModifier:

            self.transferWeights()

        elif modifiers == QtCore.Qt.AltModifier:

            self.swapWeights()

        else:

            pull = modifiers == QtCore.Qt.ShiftModifier
            self.mirrorWeights(pull=pull)

    @QtCore.Slot()
    def on_pruneDropDownButton_clicked(self):
        """
        Slot method for the `prunePushButton` widget's `clicked` signal.

        :rtype: None
        """

        tolerance = self.pruneSpinBox.value()
        self.pruneWeights(tolerance=tolerance)

    @QtCore.Slot()
    def on_slabDropDownButton_clicked(self):
        """
        Slot method for the `slabDropDownButton` widget's `clicked` signal.

        :rtype: None
        """

        self.slabPasteWeights()

    @QtCore.Slot(int)
    def on_weightPresetButtonGroup_idClicked(self, index):
        """
        Slot method for the `weightPresetButtonGroup` widget's `idClicked` signal.

        :type index: int
        :rtype: None
        """

        amount = self.__weight_presets__[index]
        self.setWeights(amount)

    @QtCore.Slot(int)
    def on_percentPresetButtonGroup_idClicked(self, index):
        """
        Slot method for the `weightPresetButtonGroup` widget's `idClicked` signal.

        :type index: int
        :rtype: None
        """

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        sign = -1.0 if (modifiers == QtCore.Qt.ShiftModifier) else 1.0
        percent = self.__percent_presets__[index] * sign

        self.scaleWeights(percent)

    @QtCore.Slot()
    def on_setWeightPushButton_clicked(self):
        """
        Slot method for the `setWeightPushButton` widget's `clicked` signal.

        :rtype: None
        """

        amount = self.setWeightSpinBox.value()
        self.setWeights(amount)

    @QtCore.Slot(int)
    def on_incrementWeightButtonGroup_idClicked(self, index):
        """
        Slot method for the `incrementWeightButtonGroup` widget's `idClicked` signal.

        :type index: int
        :rtype: None
        """

        amount = self.incrementWeightSpinBox.value() * self.__sign__[index]
        self.incrementWeights(amount)

    @QtCore.Slot(int)
    def on_scaleWeightButtonGroup_idClicked(self, index):
        """
        Slot method for the `scaleWeightButtonGroup` widget's `idClicked` signal.

        :type index: bool
        :rtype: None
        """

        percent = self.scaleWeightSpinBox.value() * self.__sign__[index]
        self.scaleWeights(percent)

    @QtCore.Slot(bool)
    def on_precisionPushButton_toggled(self, checked=False):
        """
        Slot method for the `precisionPushButton` widget's `toggled` signal.

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
        Slot method for the `selectAffectedVerticesAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        self.selectAffectedVertices()

    @QtCore.Slot(bool)
    def on_usingEzSkinBlenderAction_triggered(self, checked=False):
        """
        Slot method for the `usingEzSkinBlenderAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        webbrowser.open('https://github.com/bhsingleton/ezskinblender')
    # endregion
