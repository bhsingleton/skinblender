from PySide2 import QtCore, QtWidgets, QtGui
from . import qinfluenceitemmodel

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QWeightItemModel(qinfluenceitemmodel.QInfluenceItemModel):
    """
    Overload of QInfluenceItemModel used to interface with vertex weights.
    """

    # region Dunderscores
    __headers__ = ('Name', 'Weight')

    def __init__(self, parent=None):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QWeightItemModel, self).__init__(parent=parent)

        # Declare private variables
        #
        self._vertexSelection = []
        self._vertexWeights = {}
        self._weights = {}
    # endregion

    # region Methods
    def vertexSelection(self):
        """
        Returns the internal vertex selection.

        :rtype: list[int]
        """

        return self._cwd

    def setVertexSelection(self, vertexSelection):
        """
        Updates the internal vertex selection.

        :type vertexSelection: list[int]
        :rtype: None
        """

        self._vertexSelection = vertexSelection
        self.invalidateWeights()

    def weightFromIndex(self, index):
        """
        Returns the path associated with the given index.

        :type index: QtCore.QModelIndex
        :rtype: float
        """

        return self._weights.get(index.row(), 0.0)

    def isNullWeight(self, index):
        """
        Evaluates if the supplied index represent a null weight.

        :type index: QtCore.QModelIndex
        :rtype: bool
        """

        return self.weightFromIndex(index) <= 0.0

    def vertexWeights(self):
        """
        Returns the internal vertex weights.

        :rtype: dict[int:dict[int:float]]
        """

        return self._vertexWeights

    def weights(self):
        """
        Returns the internal averaged vertex weights.

        :rtype: dict[int:float]
        """

        return self._weights

    def data(self, index, role=None):
        """
        Returns the data stored under the given role for the item referred to by the index.

        :type index: QtCore.QModelIndex
        :type role: int
        :rtype: Any
        """

        # Evaluate data role
        #
        if index.column() == 1 and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

            # Check if influence has weight
            #
            weight = self.weightFromIndex(index)

            if weight is not None:

                return str(weight)

            else:

                return

        else:

            return super(QWeightItemModel, self).data(index, role=role)

    def invalidateWeights(self):
        """
        Invalidates the internal data structure.

        :rtype: None
        """

        # Indicate reset in progress
        #
        self.beginResetModel()

        # Check if skin is valid
        #
        if self._fnSkin.isValid():

            self._vertexWeights = self._fnSkin.vertexWeights(*self._vertexSelection)
            self._weights = self._fnSkin.averageWeights(*list(self._vertexWeights.values()))

        else:

            self._vertexWeights = {}
            self._weights = {}

        # Mark reset complete
        #
        self.endResetModel()
    # endregion
