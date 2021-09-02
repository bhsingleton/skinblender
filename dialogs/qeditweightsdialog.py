import os

from six import string_types
from copy import deepcopy
from itertools import chain
from scipy.spatial import cKDTree
from PySide2 import QtCore, QtWidgets, QtGui

from dcc import fnskin

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QLoadWeightsDialog(QtWidgets.QDialog):
    """
    Overload of QDialog used to remap skin weights onto a skin deformer.
    """

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :keyword parent: QtWidgets.QMainWindow
        :keyword f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        parent = kwargs.get('parent', QtWidgets.QApplication.activeWindow())
        f = kwargs.get('f', QtCore.Qt.WindowFlags())

        super(QLoadWeightsDialog, self).__init__(parent=parent, f=f)

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._filePath = ''
        self._maxInfluences = None
        self._influences = None
        self._influenceMap = None
        self._vertices = None
        self._points = None

        # Call build method
        #
        self.__build__()

        # Check if any arguments were supplied
        #
        numArgs = len(args)

        if numArgs == 2:

            self.skin = args[0]
            self.filePath = args[1]

    def __build__(self):
        """
        Private method used to build the user interface.

        :rtype: None
        """

        # Define dialog properties
        #
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setObjectName('QLoadWeightsDialog')
        self.setWindowTitle('|| Load Weights')
        self.setMinimumSize(QtCore.QSize(465, 280))
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Define main layout
        #
        self.setLayout(QtWidgets.QVBoxLayout())

        # Create influence table widget
        #
        self.influenceLayout = QtWidgets.QVBoxLayout()

        self.influenceGrp = QtWidgets.QGroupBox('Influences:')
        self.influenceGrp.setLayout(self.influenceLayout)

        self.influenceTable = QtWidgets.QTableWidget()
        self.influenceTable.setShowGrid(True)
        self.influenceTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.influenceTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.influenceTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.influenceTable.horizontalHeader().setStretchLastSection(True)
        self.influenceTable.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.influenceTable.setColumnCount(2)
        self.influenceTable.setHorizontalHeaderLabels(['Incoming', 'Current'])

        self.influenceLayout.addWidget(self.influenceTable)
        self.layout().addWidget(self.influenceGrp)

        # Create option buttons
        #
        self.optionsLayout = QtWidgets.QHBoxLayout()

        self.loadLayout = QtWidgets.QHBoxLayout()
        self.loadLabel = QtWidgets.QLabel('Load By:')
        self.indexRadioBtn = QtWidgets.QRadioButton('Index')
        self.positionRadioBtn = QtWidgets.QRadioButton('Position')

        self.loadLayout.addWidget(self.loadLabel)
        self.loadLayout.addWidget(self.indexRadioBtn)
        self.loadLayout.addWidget(self.positionRadioBtn)

        self.matchBtn = QtWidgets.QPushButton('Match By Name')
        self.matchBtn.pressed.connect(self.matchInfluences)

        self.okayBtn = QtWidgets.QPushButton('OK')
        self.okayBtn.clicked.connect(self.accept)

        self.cancelBtn = QtWidgets.QPushButton('Cancel')
        self.cancelBtn.clicked.connect(self.reject)

        self.optionsLayout.addLayout(self.loadLayout)
        self.optionsLayout.addWidget(self.matchBtn)
        self.optionsLayout.addWidget(self.okayBtn)
        self.optionsLayout.addWidget(self.cancelBtn)

        self.layout().addLayout(self.optionsLayout)

        # Trigger invalidation
        #
        self.indexRadioBtn.setChecked(QtCore.Qt.Checked)

    def accept(self, *args, **kwargs):
        """
        Overloaded method called after the user presses the okay button.

        :rtype: None
        """

        # Get load method before closing dialog
        #
        influenceMap = self.getInfluenceMap()
        method = self.selectedMethod()

        # Call parent method
        #
        super(QLoadWeightsDialog, self).accept(*args, **kwargs)

        # Check which load operation to perform
        #
        if method == 0:

            log.info('Loading weights by vertex index.')

            vertices = self.skin.remapVertexWeights(self._vertices, influenceMap)
            self.skin.applyVertexWeights(vertices)

        elif method == 1:

            log.info('Loading weights by closest point.')

            # Query point tree
            #
            tree = cKDTree(list(self._points.values()))

            vertexMap = {x: y for (x, y) in enumerate(self._points.keys())}
            distances, closestIndices = tree.query(self.skin.controlPoints())

            # Remap vertex weights
            #
            closestVertexIndices = [vertexMap[x] for x in closestIndices]
            vertices = {x + self.skin.arrayOffset: deepcopy(self._vertices[x]) for x in closestVertexIndices}

            # Apply weights
            #
            vertices = self.skin.remapVertexWeights(vertices, influenceMap)
            self.skin.applyVertexWeights(vertices)

        else:

            raise RuntimeError('Unknown load method encountered!')

    def reject(self, *args, **kwargs):
        """
        Inherited method called after the user pressed the cancel button.

        :rtype: None
        """

        # Call parent method
        #
        super(QLoadWeightsDialog, self).reject(*args, **kwargs)
        log.debug('Operation aborted...')

    @property
    def skin(self):
        """
        Getter method that returns the skin deformer.

        :return: fnskin.FnSkin
        """

        return self._skin

    @skin.setter
    def skin(self, skin):
        """
        Setter method that updates the skin deformer.

        :type skin: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: None
        """

        # Check if value type
        #
        if not self._skin.acceptsObject(skin):

            raise TypeError('skinCluster.setter() expects a valid object (%s given)!' % type(skin).__name__)

        # Set private variable and repopulate combo box
        #
        self._skin.setObject(skin)
        self.invalidate()

    @property
    def filePath(self):
        """
        Getter method that returns the current file path.

        :rtype: str
        """

        return self._filePath

    @filePath.setter
    def filePath(self, filePath):
        """
        Setter method that updates the current file path.

        :type filePath: str
        :rtype: None
        """

        # Update private variable
        #
        self._filePath = filePath

        # Load weights from file
        #
        state = self.skin.loadWeights(filePath)

        self._maxInfluences = state['maxInfluences']
        self._influences = state['influences']
        self._influenceMap = {x: y for (x, y) in enumerate(self._influences.keys())}
        self._vertices = state['vertices']
        self._points = state['points']

    def selectedMethod(self):
        """
        Method used to retrieve the user specified load operation:
            0 - Load by vertex index.
            1 - Load by closest position.

        :rtype: int
        """

        if self.indexRadioBtn.isChecked():

            return 0

        elif self.positionRadioBtn.isChecked():

            return 1

        else:

            return -1

    def invalidate(self):
        """
        Invalidate method used to rebuild the table widget.

        :rtype: None
        """

        # Check if xml weights are valid
        #
        if not self.skin.isValid() or not os.path.exists(self.filePath):

            return

        # Iterate through influences
        #
        usedInfluenceIds = set(chain(*[vertexWeights.keys() for vertexWeights in self._vertices.values()]))
        maxInfluenceId = max(self._influences.keys())
        maxRowCount = maxInfluenceId + 1

        self.influenceTable.setRowCount(maxRowCount)

        for influenceId in range(maxRowCount):

            # Create weighted influence item
            #
            influenceName = self._influences.get(influenceId, '')
            tableItem = QtWidgets.QTableWidgetItem(influenceName)

            # Create remap combo box
            #
            comboBox = QtWidgets.QComboBox()
            comboBox.addItems(list(self._influences.values()))

            # Assign items to table
            #
            self.influenceTable.setItem(influenceId, 0, tableItem)
            self.influenceTable.setCellWidget(influenceId, 1, comboBox)

            # Check if row should be hidden
            #
            if influenceId not in usedInfluenceIds:

                self.influenceTable.setRowHidden(influenceId, True)

        # Resize items to contents
        #
        self.influenceTable.resizeRowsToContents()
        self.influenceTable.resizeColumnsToContents()

        # Try and match influences by name
        #
        self.matchBtn.animateClick()

    def matchInfluences(self):
        """
        Iterates through unhidden rows and finds the closest influence name.

        :rtype: None
        """

        # Iterate through rows
        #
        numRows = self.influenceTable.rowCount()

        for row in range(numRows):

            # Check if row is hidden
            #
            if self.influenceTable.isRowHidden(row):
                log.debug('Skipping row index: %s' % row)
                continue

            # Get selected combo box item
            #
            tableItem = self.influenceTable.item(row, 0)
            influenceName = tableItem.text()

            # Find matching text value from influence table
            #
            comboBox = self.influenceTable.cellWidget(row, 1)
            index = comboBox.findText(influenceName)

            if index != -1:

                comboBox.setCurrentIndex(index)

            else:

                log.warning('Unable to find a match for influence: %s!' % influenceName)

    def getInfluenceMap(self):
        """
        Gets the user defined influence map.

        :rtype: dict
        """

        # Iterate through rows
        #
        influenceMap = {}
        numRows = self.influenceTable.rowCount()

        for i in range(numRows):
            comboBox = self.influenceTable.cellWidget(i, 1)

            currentIndex = comboBox.currentIndex()
            influenceMap[i] = comboBox.influenceMap[currentIndex]

        # Return influence map
        #
        log.debug('Created %s influence binder.' % influenceMap)
        return influenceMap


def loadSkinWeights(skin, filePath):
    """
    Loads the skin weights from the specified file onto the supplied skin deformer.

    :type skin: Union[om.MObject, pymxs.runtime.MXSWrapperBase]
    :type filePath: str
    :rtype: None
    """

    # Check argument types
    #
    dialog = QLoadWeightsDialog()

    if dialog.skin.acceptsObject(skin) and isinstance(filePath, string_types):

        dialog.skin = skin
        dialog.filePath = filePath
        dialog.exec_()

    else:

        raise TypeError('loadSkinWeights() expects a skin and file path (%s and %s given)!' % (type(args[0]).__name__, type(args[1]).__name__,))
