import os

from itertools import chain
from dcc import fnskin, fnmesh
from dcc.ui.dialogs import qmaindialog
from dcc.vendor.six import string_types
from dcc.vendor.Qt import QtCore, QtWidgets, QtGui
from ...libs import skinweights, skinutils

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QLoadWeightsDialog(qmaindialog.QMainDialog):
    """
    Overload of `QMainDialog` that loads skin weights onto a skin.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QMainWindow
        :key f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QLoadWeightsDialog, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._mesh = fnmesh.FnMesh()
        self._skin = fnskin.FnSkin()
        self._skinWeights = None

        # Declare public variables
        #
        self.influenceLayout = None
        self.influenceGroupBox = None
        self.influenceTableWidget = None

        self.buttonsLayout = None
        self.buttonsWidget = None
        self.methodLabel = None
        self.indexRadioButton = None
        self.positionRadioButton = None
        self.methodButtonGroup = None
        self.horizontalSpacer = None
        self.matchPushButton = None
        self.okayPushButton = None
        self.cancelPushButton = None

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QLoadWeightsDialog, self).__setup_ui__(*args, **kwargs)

        # Initialize dialog
        #
        self.setWindowTitle("|| Load Weights")
        self.setMinimumSize(QtCore.QSize(535, 280))

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        self.setLayout(centralLayout)

        # Initialize influence group-box
        #
        self.influenceLayout = QtWidgets.QVBoxLayout()
        self.influenceLayout.setObjectName('influenceLayout')

        self.influenceGroupBox = QtWidgets.QGroupBox('Influences:')
        self.influenceGroupBox.setObjectName('influenceGroupBox')
        self.influenceGroupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.influenceGroupBox.setLayout(self.influenceLayout)

        self.influenceTableWidget = QtWidgets.QTableWidget()
        self.influenceTableWidget.setObjectName('influenceTableWidget')
        self.influenceTableWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.influenceTableWidget.setStyleSheet('QTableWidget:item { height: 24; }')
        self.influenceTableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.influenceTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.influenceTableWidget.setAlternatingRowColors(True)
        self.influenceTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.influenceTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.influenceTableWidget.setColumnCount(2)
        self.influenceTableWidget.setHorizontalHeaderLabels(['Joint', 'Current'])

        horizontalHeader = self.influenceTableWidget.horizontalHeader()  # type: QtWidgets.QHeaderView
        horizontalHeader.setStretchLastSection(True)
        horizontalHeader.setMinimumSectionSize(50)
        horizontalHeader.setDefaultSectionSize(100)

        verticalHeader = self.influenceTableWidget.verticalHeader()  # type: QtWidgets.QHeaderView
        verticalHeader.setStretchLastSection(False)
        verticalHeader.setMinimumSectionSize(24)
        verticalHeader.setDefaultSectionSize(24)

        self.influenceLayout.addWidget(self.influenceTableWidget)

        centralLayout.addWidget(self.influenceGroupBox)

        # Initialize buttons widget
        #
        self.buttonsLayout = QtWidgets.QHBoxLayout()
        self.buttonsLayout.setObjectName('buttonsLayout')
        self.buttonsLayout.setContentsMargins(0, 0, 0, 0)

        self.buttonsWidget = QtWidgets.QWidget()
        self.buttonsWidget.setObjectName('buttonsWidget')
        self.buttonsWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.buttonsWidget.setFixedHeight(24)
        self.buttonsWidget.setLayout(self.buttonsLayout)

        self.methodLabel = QtWidgets.QLabel('Load By:')
        self.methodLabel.setObjectName('methodLabel')
        self.methodLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.methodLabel.setFixedWidth(50)
        self.methodLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.indexRadioButton = QtWidgets.QRadioButton('Index')
        self.indexRadioButton.setObjectName('indexRadioButton')
        self.indexRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
        self.indexRadioButton.setChecked(True)

        self.positionRadioButton = QtWidgets.QRadioButton('Position')
        self.positionRadioButton.setObjectName('positionRadioButton')
        self.positionRadioButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))

        self.methodButtonGroup = QtWidgets.QButtonGroup(parent=self.buttonsWidget)
        self.methodButtonGroup.setObjectName('methodButtonGroup')
        self.methodButtonGroup.setExclusive(True)
        self.methodButtonGroup.addButton(self.indexRadioButton, id=0)
        self.methodButtonGroup.addButton(self.positionRadioButton, id=1)

        self.horizontalSpacer = QtWidgets.QSpacerItem(50, 24, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.matchPushButton = QtWidgets.QPushButton('Match By Name')
        self.matchPushButton.setObjectName('matchPushButton')
        self.matchPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
        self.matchPushButton.clicked.connect(self.on_matchPushButton_clicked)

        self.okayPushButton = QtWidgets.QPushButton('OK')
        self.okayPushButton.setObjectName('okayPushButton')
        self.okayPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
        self.okayPushButton.clicked.connect(self.accept)

        self.cancelPushButton = QtWidgets.QPushButton('Cancel')
        self.cancelPushButton.setObjectName('cancelPushButton')
        self.cancelPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred))
        self.cancelPushButton.clicked.connect(self.reject)

        self.buttonsLayout.addWidget(self.methodLabel)
        self.buttonsLayout.addWidget(self.indexRadioButton)
        self.buttonsLayout.addWidget(self.positionRadioButton)
        self.buttonsLayout.addItem(self.horizontalSpacer)
        self.buttonsLayout.addWidget(self.okayPushButton)
        self.buttonsLayout.addWidget(self.cancelPushButton)

        centralLayout.addWidget(self.buttonsWidget)
    # endregion

    # region Properties
    @property
    def mesh(self):
        """
        Getter method that returns the mesh.

        :rtype: fnmesh.FnMesh
        """

        return self._mesh

    @mesh.setter
    def mesh(self, mesh):
        """
        Setter method that updates the mesh.

        :type mesh: Any
        :rtype: None
        """

        self._mesh.trySetObject(mesh)
        self._skin.trySetObject(mesh)

    @property
    def skin(self):
        """
        Getter method that returns the skin.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @property
    def skinWeights(self):
        """
        Getter method that returns the skin weights.

        :rtype: skinweights.SkinWeights
        """

        return self._skinWeights

    @skinWeights.setter
    def skinWeights(self, skinWeights):
        """
        Setter method that updates the skin weights.

        :type skinWeights: skinweights.SkinWeights
        :rtype: None
        """

        self._skinWeights = skinWeights
    # endregion

    # region Events
    def eventFilter(self, watched, event):
        """
        Filters events if this object has been installed as an event filter for the watched object.
        In your reimplementation of this function, if you want to filter the event out, i.e. stop it being handled further, return true; otherwise return false.

        :type watched: QtCore.QObject
        :type event: QtCore.QEvent
        :rtype bool
        """

        if isinstance(watched, QtWidgets.QComboBox) and isinstance(event, QtGui.QWheelEvent):

            return True  # This blocks the scroll-wheel from messing up influences!

        else:

            return False
    # endregion

    # region Methods
    @classmethod
    def loadWeights(cls, mesh, filePath, parent=None):
        """
        Loads the skin weights from the specified file onto the supplied skin.

        :type mesh: Union[om.MObject, pymxs.runtime.MXSWrapperBase]
        :type filePath: str
        :type parent: QtWidgets.QWidget
        :rtype: bool
        """

        # Check if file exists
        #
        exists = os.path.exists(filePath) if isinstance(filePath, string_types) else False

        if not exists:

            log.warning(f'Unable to locate file: {filePath}')
            return False

        # Initialize dialog and evaluate mesh
        #
        skinWeights = skinutils.importSkin(filePath)
        dialog = cls(mesh=mesh, skinWeights=skinWeights, parent=parent)

        meshExists = dialog.mesh.isValid()

        if not meshExists:

            log.warning(f'Unable to load weights onto supplied mesh!')
            return False

        # Check if mesh has a skin
        #
        skinExists = dialog.ensureSkin()

        if skinExists:

            return bool(dialog.exec_())

        else:

            log.warning('Unable to load weights onto supplied mesh!')
            return False

    def ensureSkin(self):
        """
        Ensures the current mesh has a skin deformer.

        :rtype: bool
        """

        # Check if skin is already valid
        #
        if self._skin.isValid():

            return True

        # Check if skin weights exist
        #
        if not isinstance(self.skinWeights, skinweights.SkinWeights):

            return False

        # Check if all influences exist
        #
        influenceNames = list(self.skinWeights.influences.values())
        influenceCount = len(influenceNames)

        exist = all(self.mesh.doesNodeExist(influenceName) for influenceName in influenceNames) and influenceCount > 0

        if not exist:

            return False

        # Create new skin and add influences
        #
        self._skin = self.skin.create(self.mesh.object())
        self._skin.addInfluence(*influenceNames)

        return True

    def matchInfluences(self):
        """
        Matches the incoming influences with the current influences.

        :rtype: None
        """

        # Iterate through rows
        #
        numRows = self.influenceTableWidget.rowCount()

        for row in range(numRows):

            # Check if row is hidden
            #
            if self.influenceTableWidget.isRowHidden(row):

                log.debug('Skipping row index: %s' % row)
                continue

            # Get selected combo box item
            #
            tableItem = self.influenceTableWidget.item(row, 0)
            influenceName = tableItem.text()

            # Find matching text value from influence table
            #
            comboBox = self.influenceTableWidget.cellWidget(row, 1)
            index = comboBox.findText(influenceName)

            if index != -1:

                comboBox.setCurrentIndex(index)

            else:

                log.warning('Unable to find a match for influence: %s!' % influenceName)

    def selectedMethod(self):
        """
        Returns the user specified load operation:

        :rtype: int
        """

        return self.methodButtonGroup.checkedId()

    def influenceMap(self):
        """
        Returns the user defined influence map.

        :rtype: Dict[int, int]
        """

        # Iterate through rows
        #
        influenceMap = {}
        influenceIds = list(self.skin.influences().keys())

        numRows = self.influenceTableWidget.rowCount()

        for i in range(numRows):

            comboBox = self.influenceTableWidget.cellWidget(i, 1)
            influenceMap[i] = influenceIds[comboBox.currentIndex()]

        # Return influence map
        #
        log.debug('Created influence map: %s' % influenceMap)
        return influenceMap

    def invalidate(self):
        """
        Repopulates the influence table widget items.

        :rtype: None
        """

        # Check skin weights are valid
        #
        meshExists = self.mesh.isValid()
        skinExists = self.skin.isValid()
        skinWeightsExist = isinstance(self.skinWeights, skinweights.SkinWeights)

        if not (meshExists and skinExists and skinWeightsExist):

            return

        # Update row count
        #
        maxInfluenceId = max(self.skinWeights.influences.keys())
        rowCount = maxInfluenceId + 1

        self.influenceTableWidget.clearContents()
        self.influenceTableWidget.setRowCount(rowCount)
        self.influenceTableWidget.setVerticalHeaderLabels(list(map(str, range(rowCount))))

        # Iterate through influences
        #
        currentInfluences = self.skin.influenceNames()
        incomingInfluences = self.skinWeights.influences

        usedInfluenceIds = set(chain(*[weights.keys() for weights in self.skinWeights.weights]))

        for influenceId in range(rowCount):

            # Create weighted influence item
            #
            influenceName = incomingInfluences.get(influenceId, '')
            tableItem = QtWidgets.QTableWidgetItem(influenceName)

            # Create remap combo box
            #
            comboBox = QtWidgets.QComboBox(parent=self.influenceTableWidget)
            comboBox.setFocusPolicy(QtCore.Qt.ClickFocus)
            comboBox.addItems(list(currentInfluences.values()))
            comboBox.installEventFilter(self)

            # Assign items to table
            #
            self.influenceTableWidget.setItem(influenceId, 0, tableItem)
            self.influenceTableWidget.setCellWidget(influenceId, 1, comboBox)

            # Check if row should be hidden
            #
            if influenceId not in usedInfluenceIds:

                self.influenceTableWidget.setRowHidden(influenceId, True)

        # Resize items to contents
        #
        self.influenceTableWidget.resizeColumnsToContents()

        # Try and match influences by name
        #
        self.matchInfluences()

    def exec_(self):
        """
        Shows the dialog as a modal dialog, blocking until the user closes it.

        :rtype: QtWidgets.QDialog.DialogCode
        """

        # Invalidate user interface
        #
        self.invalidate()

        # Call parent method
        #
        return super(QLoadWeightsDialog, self).exec_()
    # endregion

    # region Slots
    @QtCore.Slot()
    def accept(self):
        """
        Slot method for the dialog's `accept` signal.

        :rtype: None
        """

        # Check which load operation to perform
        #
        influenceMap = self.influenceMap()
        method = self.selectedMethod()

        if method == 0:

            self.skinWeights.applyWeights(self.skin, influenceMap=influenceMap)

        elif method == 1:

            self.skinWeights.applyClosestWeights(self.skin, influenceMap=influenceMap)

        else:

            log.debug(f'Unable to process selected method: {method}')

        # Call parent method
        #
        super(QLoadWeightsDialog, self).accept()

    @QtCore.Slot()
    def on_matchPushButton_clicked(self):
        """
        Slot method for the `matchPushButton` widget's `clicked` signal.

        :rtype: None
        """

        self.matchInfluences()
    # endregion
