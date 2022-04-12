import os

from PySide2 import QtCore, QtWidgets, QtGui
from six import string_types
from copy import deepcopy
from itertools import chain
from scipy.spatial import cKDTree
from dcc import fnskin, fnnode
from dcc.ui.dialogs import quicdialog

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QLoadWeightsDialog(quicdialog.QUicDialog):
    """
    Overload of QDialog used to remap skin weights onto a skin deformer.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QMainWindow
        :key f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._filePath = ''
        self._maxInfluences = None
        self._incomingInfluences = None
        self._currentInfluences = None
        self._influenceMap = None
        self._vertices = None
        self._points = None

        # Call parent method
        #
        super(QLoadWeightsDialog, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
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

        # Update function set object
        #
        success = self._skin.trySetObject(skin)

        if not success:

            return

        # Get current influences
        #
        self._currentInfluences = {influenceId: influenceName for (influenceId, influenceName) in self._skin.influenceNames().items()}
        self._influenceMap = dict(enumerate(self._currentInfluences.keys()))

        # Invalidate user interface
        #
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
        # Be aware that json does not support numerical keys!
        # So we have to cast all numerical keys to integers!
        #
        state = self.skin.loadWeights(filePath)

        self._maxInfluences = int(state['maxInfluences'])
        self._incomingInfluences = {int(influenceId): influenceName for (influenceId, influenceName) in state['influences'].items()}
        self._vertices = {int(vertexIndex): {int(influenceId): weight for (influenceId, weight) in weights.items()} for (vertexIndex, weights) in state['vertices'].items()}
        self._points = state['points']

        # Invalidate user interface
        #
        self.invalidate()
    # endregion

    # region Methods
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
        numRows = self.influenceTableWidget.rowCount()

        for i in range(numRows):

            comboBox = self.influenceTableWidget.cellWidget(i, 1)

            currentIndex = comboBox.currentIndex()
            influenceMap[i] = self._influenceMap[currentIndex]

        # Return influence map
        #
        log.debug('Created influence map: %s' % influenceMap)
        return influenceMap

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
        maxInfluenceId = max(self._incomingInfluences.keys())
        maxRowCount = maxInfluenceId + 1

        self.influenceTableWidget.setRowCount(maxRowCount)

        for influenceId in range(maxRowCount):

            # Create weighted influence item
            #
            influenceName = self._incomingInfluences.get(influenceId, '')
            tableItem = QtWidgets.QTableWidgetItem(influenceName)

            # Create remap combo box
            #
            comboBox = QtWidgets.QComboBox(parent=self.influenceTableWidget)
            comboBox.addItems(list(self._currentInfluences.values()))

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
    # endregion

    # region Slots
    @QtCore.Slot()
    def accept(self):
        """
        Hides the modal dialog and sets the result code to QDialogCode.Accepted.

        :rtype: None
        """

        # Call parent method
        #
        super(QLoadWeightsDialog, self).accept()

        # Check which load operation to perform
        #
        influenceMap = self.influenceMap()
        method = self.selectedMethod()

        if method == 0:

            # Apply weights
            #
            log.info('Loading weights by vertex index.')

            vertices = self.skin.remapVertexWeights(self._vertices, influenceMap)
            self.skin.applyVertexWeights(vertices)

        elif method == 1:

            # Query point tree
            #
            log.info('Loading weights by closest point.')
            tree = cKDTree(list(self._points.values()))

            vertexMap = {x: y for (x, y) in enumerate(self._points.keys())}
            distances, closestIndices = tree.query(self.skin.controlPoints())

            # Remap vertex weights
            #
            closestVertexIndices = [vertexMap[x] for x in closestIndices]
            vertices = {x + self.skin.arrayIndexType: deepcopy(self._vertices[x]) for x in closestVertexIndices}

            # Apply weights
            #
            vertices = self.skin.remapVertexWeights(vertices, influenceMap)
            self.skin.applyVertexWeights(vertices)

        else:

            raise RuntimeError('Unknown load method encountered!')

    @QtCore.Slot(bool)
    def on_matchPushButton_clicked(self, clicked=False):
        """
        Clicked slot that matches the incoming influences with the current influences.

        :type clicked: bool
        :rtype: None
        """

        self.matchInfluences()
    # endregion


def loadSkinWeights(skin, filePath):
    """
    Loads the skin weights from the specified file onto the supplied skin deformer.

    :type skin: Union[om.MObject, pymxs.runtime.MXSWrapperBase]
    :type filePath: str
    :rtype: None
    """

    # Check path type
    #
    if not isinstance(filePath, string_types):

        raise TypeError('loadSkinWeights() expects a valid file path (%s given)!' % type(filePath).__name__)

    # Initialize dialog from skin
    #
    dialog = QLoadWeightsDialog(skin=skin, filePath=filePath)

    if dialog.skin.isValid():

        dialog.exec_()

    else:

        raise TypeError('loadSkinWeights() expects a valid skin (%s given)!' % type(skin).__name__)
