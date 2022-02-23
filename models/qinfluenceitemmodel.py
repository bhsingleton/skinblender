from PySide2 import QtCore, QtWidgets, QtGui
from dcc import fnnode, fnskin

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceItemModel(QtCore.QAbstractItemModel):
    """
    Overload of QAbstractItemModel used to interface with influence objects.
    """

    # region Dunderscores
    __headers__ = ('Name',)

    def __init__(self, parent=None):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceItemModel, self).__init__(parent=parent)

        # Declare private variables
        #
        self._fnSkin = fnskin.FnSkin()
        self._influences = {}
        self._rowHeight = 24
    # endregion

    # region Methods
    def skin(self):
        """
        Returns the current skin object.

        :rtype: object
        """

        return self._fnSkin.object()

    def setSkin(self, skin):
        """
        Updates the current skin object.

        :type skin: object
        :rtype: None
        """

        # Check for none type
        #
        if skin is not None:

            self._fnSkin.trySetObject(skin)

        else:

            self._fnSkin.resetObject()

        # Invalidate internal data
        #
        self.invalidateInfluences()

    def rowHeight(self):
        """
        Returns the row height for all influences.

        :rtype: int
        """

        return self._rowHeight

    def setRowHeight(self, rowHeight):
        """
        Updates the row height for all influences.

        :type rowHeight: int
        :rtype: None
        """

        self._rowHeight = rowHeight

    def influenceFromIndex(self, index):
        """
        Returns the path associated with the given index.

        :type index: QtCore.QModelIndex
        :rtype: object
        """

        return self._influences.get(index.row(), None)

    def isNullInfluence(self, index):
        """
        Evaluates if the supplied index represent a null influence.

        :type index: QtCore.QModelIndex
        :rtype: bool
        """

        return self.influenceFromIndex(index) is None

    def parent(self, index):
        """
        Returns the parent of the model item with the given index.
        If the item has no parent, an invalid QModelIndex is returned.

        :type index: QtCore.QModelIndex
        :rtype: QtCore.QModelIndex
        """

        return QtCore.QModelIndex()

    def index(self, row, column, parent=None):
        """
        Returns the index of the item in the model specified by the given row, column and parent index.

        :type row: int
        :type column: int
        :type parent: QtCore.QModelIndex
        :rtype: QtCore.QModelIndex
        """

        return self.createIndex(row, column)

    def rowCount(self, parent=None):
        """
        Returns the number of rows under the given parent.

        :type parent: QtCore.QModelIndex
        :rtype: int
        """

        influenceIds = list(self._influences.keys())
        numInfluenceIds = len(influenceIds)

        if numInfluenceIds > 0:

            return max(influenceIds)

        else:

            return 0

    def columnCount(self, parent=None):
        """
        Returns the number of columns under the given parent.

        :type parent: QtCore.QModelIndex
        :rtype: int
        """

        return len(self.__headers__)

    def getTextSizeHint(self, text, padding=6):
        """
        Returns a size hint for the supplied text.

        :type text: str
        :type padding: int
        :rtype: QtCore.QSize
        """

        application = QtWidgets.QApplication.instance()
        font = application.font()

        fontMetric = QtGui.QFontMetrics(font)
        width = fontMetric.width(text) + padding

        return QtCore.QSize(width, self._rowHeight)

    def data(self, index, role=None):
        """
        Returns the data stored under the given role for the item referred to by the index.

        :type index: QtCore.QModelIndex
        :type role: int
        :rtype: Any
        """

        # Evaluate data role
        #
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

            # Check if influence exists at index
            #
            fnInfluence = fnnode.FnNode()
            success = fnInfluence.trySetObject(self.influenceFromIndex(index))

            if success:

                return fnInfluence.name()

            else:

                return

        elif role == QtCore.Qt.SizeHintRole:

            text = self.data(index, role=QtCore.Qt.DisplayRole)
            return self.getTextSizeHint(text)

        elif role == QtCore.Qt.TextAlignmentRole:

            return QtCore.Qt.AlignCenter

        else:

            return

    def headerData(self, section, orientation, role=None):
        """
        Returns the data for the given role and section in the header with the specified orientation.

        :type section: int
        :type orientation: int
        :type role: int
        :rtype: Any
        """

        if orientation == QtCore.Qt.Horizontal and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

            return self.__headers__[section]

        elif orientation == QtCore.Qt.Vertical and role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):

            return str(section)

        else:

            return super(QInfluenceItemModel, self).headerData(section, orientation, role=role)

    def invalidateInfluences(self):
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

            self._influences = self._fnSkin.influences()

        else:

            self._influences = {}

        # Mark reset complete
        #
        self.endResetModel()
    # endregion
