from Qt import QtCore, QtWidgets, QtGui

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceItemFilterModel(QtCore.QSortFilterProxyModel):
    """
    Overload of QSortFilterProxyModel used to filter influence objects.
    """

    # region Dunderscores
    def __init__(self, parent=None):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceItemFilterModel, self).__init__(parent)

        # Declare private variables
        #
        self._overrides = []
    # endregion

    # region Properties
    @property
    def overrides(self):
        """
        Getter method that returns a list of exempt influence IDs.

        :rtype: list[int]
        """

        return self._overrides

    @overrides.setter
    def overrides(self, overrides):
        """
        Setter method that updates the list of visible influence IDs.

        :type overrides: list[int]
        :rtype: None
        """

        # Check argument types
        #
        if not all([isinstance(x, int) for x in overrides]):

            raise TypeError('overrides.setter() expects a sequence of integers!')

        # Invalidate filter
        #
        self._overrides = list(overrides)
        self.invalidateFilter()
    # endregion

    # region Methods
    def isNullOrEmpty(self, value):
        """
        Evaluates if the supplied value is null of empty.

        :type value: Any
        :rtype: bool
        """

        if value is None:

            return True

        elif hasattr(value, '__len__'):

            return len(value) == 0

        elif isinstance(value, (int, float)):

            return value == 0.0

        else:

            return False

    def activeInfluences(self):
        """
        Returns a list of active influences.

        :rtype: list[int]
        """

        return [self.mapToSource(self.index(x, 0)).row() for x in range(self.rowCount())]

    def activeInfluenceCount(self):
        """
        Evaluates the number of active influences.

        :rtype: int
        """

        return len(self.activeInfluences())

    def inactiveInfluences(self):
        """
        Returns a list of inactive influences.

        :rtype: list[int]
        """

        return list(set(range(self.sourceModel().rowCount())).difference(set(self.activeInfluences())))

    def inactiveInfluenceCount(self):
        """
        Evaluates the number of inactive influences.

        :rtype: int
        """

        return len(self.inactiveInfluences())

    def filterAcceptsRow(self, row, parent):
        """
        Returns true if the item in the row indicated should be included in the model.

        :type row: int
        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        # Evaluate row for null items
        #
        sourceModel = self.sourceModel()
        columnCount = sourceModel.columnCount()
        indices = [sourceModel.index(row, column, parent=parent) for column in range(columnCount)]

        isNull = any(self.isNullOrEmpty(sourceModel.itemFromIndex(index).text()) for index in indices)

        # Call parent method
        # This will evaluate any regex expressions
        #
        acceptsRow = super(QInfluenceItemFilterModel, self).filterAcceptsRow(row, parent)
        selectedRows = self.parent().selectedRows()

        if (acceptsRow and not isNull) or (row in selectedRows):

            log.debug(f'Accepting row: {row}')
            return True

        elif row in self._overrides:

            log.debug(f'Overriding row: {row}')
            self._overrides.remove(row)

            return True

        elif isNull:

            return False

        else:

            return acceptsRow
    # endregion
