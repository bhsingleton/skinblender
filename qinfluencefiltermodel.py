import fnmatch

from six import string_types
from PySide2 import QtCore, QtWidgets, QtGui

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceFilterModel(QtCore.QSortFilterProxyModel):
    """
    Overload of QSortFilterProxyModel used to filter out influence names.
    """

    def __init__(self, parent=None):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceFilterModel, self).__init__(parent)

        # Declare class variables
        #
        self._visible = []
        self._overrides = []
        self._activeInfluences = []
        self._inactiveInfluences = []

    def filterAcceptsRow(self, row, parent):
        """
        Overloaded method used to dynamically hide/show rows based on the return value.

        :type row: int
        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        # Check if row contains null data
        #
        index = self.sourceModel().index(row, 0, parent)

        if self.isItemNull(index):

            log.debug('%s contains null data.' % row)
            self._inactiveInfluences.append(row)

            return False

        # Check if row should be visible
        #
        selectedRows = self.parent().selectedRows()
        acceptsRow = False

        if row in self._visible or row in selectedRows:

            # Append item to active influences
            #
            self._activeInfluences.append(row)
            acceptsRow = True

        elif row in self._overrides:

            self._activeInfluences.append(row)
            self._overrides.remove(row)

            acceptsRow = True

        else:

            log.debug('%s is marked as hidden.' % row)
            self._inactiveInfluences.append(row)

        return acceptsRow

    def invalidateFilter(self):
        """
        Clears the influence lists before filtering anymore rows.

        :rtype: None
        """

        # Reset private lists
        #
        self._activeInfluences = []
        self._inactiveInfluences = []

        # Call inherited method
        #
        super(QInfluenceFilterModel, self).invalidateFilter()

    def visible(self):
        """
        Returns the list of visible influence IDs.

        :rtype: list[int]
        """

        return self._visible

    @property
    def numVisible(self):
        """
        Getter method that evaluates the number of visible influences.

        :rtype: int
        """

        return len(self._visible)

    def setVisible(self, *args, **kwargs):
        """
        Updates the list of visible influence IDs.

        :type args: tuple[int]
        :rtype: None
        """

        # Check argument types
        #
        if not all([isinstance(x, int) for x in args]):

            raise TypeError('setVisible() expects a sequence of integers!')

        # Reset private variables
        #
        self._visible = args
        self.invalidateFilter()

    def overrides(self):
        """
        Returns a list of overrides that can bypass filtering.
        These items are gradually removed by the "filterAcceptsRow" method.

        :rtype: list[int]
        """

        return self._overrides

    def setOverrides(self, *args):
        """
        Updates the list of overrides that can bypass filtering.

        :type args: tuple[int]
        :rtype: None
        """

        # Check argument types
        #
        if not all([isinstance(x, int) for x in args]):

            raise TypeError('setOverrides() expects a sequence of integers!')

        # Reset private variables
        #
        self._overrides = list(args)
        self.invalidateFilter()

    @property
    def activeInfluences(self):
        """
        Getter method that returns the active influence IDs.

        :rtype: list[int]
        """

        return self._activeInfluences

    @property
    def numActiveInfluences(self):
        """
        Getter method that evaluates the number of active influences.

        :rtype: int
        """

        return len(self._activeInfluences)

    @property
    def inactiveInfluences(self):
        """
        Getter method that returns the inactive influence IDs.

        :rtype: list[int]
        """

        return self._inactiveInfluences

    @property
    def numInactiveInfluences(self):
        """
        Getter method that evaluates the number of inactive influences.

        :rtype: int
        """

        return len(self._inactiveInfluences)

    def isItemNull(self, index):
        """
        Checks if the supplied row contains any data.

        :type index: QtCore.QModelIndex
        :rtype: bool
        """

        # Check if index is valid
        #
        if index.isValid():

            return not self.sourceModel().itemFromIndex(index).text()

        else:

            return False

    def isRowHidden(self, row):
        """
        Checks if the supplied row is hidden.

        :type row: int
        :rtype: bool
        """

        return row in self._inactiveInfluences

    def isRowSelected(self, row, column=0):
        """
        Method used to check if the supplied row index is selected.

        :type row: int
        :type column: int
        :rtype: bool
        """

        # Check value type
        #
        if not isinstance(row, int):

            raise TypeError('isRowSelected() expects a int (%s given)!' % row)

        # Get selection model
        #
        sourceModel = self.sourceModel()
        selectionModel = self.parent().selectionModel()

        # Define model index
        #
        index = sourceModel.index(row, column)
        index = self.mapFromSource(index)

        return selectionModel.isSelected(index)

    def getRowsByText(self, *args, **kwargs):
        """
        Returns a list of rows with the given text strings .

        :type args: tuple[str]
        :keyword column: int
        :rtype: list[int]
        """

        # Check argument types
        #
        if not all([isinstance(x, string_types) for x in args]):

            raise TypeError('getRowsByText() expects a sequence of strings!')

        # Get associate model and iterate through items
        #
        sourceModel = self.sourceModel()
        column = kwargs.get('column', 0)

        rows = []

        for arg in args:

            items = sourceModel.findItems(arg, column=column)
            rows = rows + [x.row() for x in items]

        log.debug('Got %s row indices from %s names.' % (rows, args))
        return rows

    def getSelectedRows(self):
        """
        Gets the selected row indices from the source widget.

        :rtype: list[int]
        """

        # Get the selection model
        #
        parent = self.parent()
        selectionModel = parent.selectionModel()

        # Map selection model to the filter model
        #
        selection = selectionModel.selection()
        selection = self.mapSelectionToSource(selection)

        # Create unique list of rows
        #
        indices = selection.indexes()
        selectedRows = set([x.row() for x in indices])

        return list(selectedRows)

    def getSelectedItems(self, column=0):
        """
        Gets the selected items based on the specified column.
        By default this is set to 0 since we're more concerned with influence names.

        :param column: Forces the operation to query a different column.
        :type column: int
        :rtype: list[str]
        """

        # Get corresponding text value from row indices
        #
        sourceModel = self.sourceModel()
        rows = self.getSelectedRows()

        return [sourceModel.item(x, column).text() for x in rows]

    def filterRowsByPattern(self, pattern, column=0):
        """
        Method used to generate a filtered list of row items based on a supplied pattern.

        :type pattern: str
        :type column: int
        :rtype: list(int)
        """

        # Check value type
        #
        if not isinstance(pattern, string_types):

            raise TypeError('filterRowsByPattern() expects a str (%s given)!' % type(pattern).__name__)

        # Get text values from source model
        #
        sourceModel = self.sourceModel()
        rows = range(sourceModel.rowCount())

        # Compose list using match pattern
        #
        items = [sourceModel.item(row, column).text() for row in rows]
        filtered = [row for row, item in zip(rows, items) if fnmatch.fnmatch(item, pattern)]

        return filtered
