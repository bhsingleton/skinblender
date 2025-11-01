from dcc.vendor.Qt import QtCore, QtWidgets, QtGui

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceView(QtWidgets.QTableView):
    """
    Overload of `QTableView` that displays skin influences.
    This widget also has builtin auto select functionality for buddies.
    """

    # region Signals
    synchronized = QtCore.Signal()
    highlighted = QtCore.Signal(QtCore.QItemSelection)
    # endregion

    # region Dunderscores
    def __init__(self, parent=None):
        """
        Private method called after a new instance has been created.

        :type parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceView, self).__init__(parent)

        # Declare private variables
        #
        self._buddy = None
        self._autoSelect = True
        self._pending = False
        self._selectedRows = []

        # Enable view grid
        #
        self.setShowGrid(True)
    # endregion

    # region Methods
    def buddy(self):
        """
        Returns the buddy widget.
        If there is no buddy then none is returned!

        :rtype: QInfluenceView
        """

        return self._buddy

    def setBuddy(self, buddy):
        """
        Updates the buddy for this widget.

        :type buddy: QInfluenceView
        :rtype: None
        """

        # Check value type
        #
        if not isinstance(buddy, QInfluenceView):

            raise TypeError('setSibling() expects a QInfluenceView (%s given)!' % type(buddy).__name__)

        self._buddy = buddy

    def hasBuddy(self):
        """
        Evaluates if this widget has a buddy.

        :rtype: bool
        """

        return self._buddy is not None

    def autoSelect(self):
        """
        Returns the auto select state.

        :rtype: bool
        """

        return self._autoSelect

    def setAutoSelect(self, autoSelect):
        """
        Returns the auto select state.

        :type autoSelect: bool
        :rtype: None
        """

        self._autoSelect = autoSelect

    def beginSelectionUpdate(self):
        """
        Changes the pending state to prevent cyclical errors.

        :rtype: None
        """

        self._pending = True

    def endSelectionUpdate(self):
        """
        Changes the pending state to prevent cyclical errors.

        :rtype: None
        """

        self._pending = False

    def isPending(self):
        """
        Evaluates if this widget is currently synchronizing with its sibling.

        :rtype: bool
        """

        return self._pending

    def isBuddyPending(self):
        """
        Evaluates if the buddy is attempting to synchronize with this widget.

        :rtype: bool
        """

        if self.hasBuddy():

            return self.buddy().isPending()

        else:

            return False

    def synchronize(self):
        """
        Forces the buddy to synchronize with this widget.

        :rtype: None
        """

        # Check if buddy exists
        #
        if not self.hasBuddy():

            log.debug(f'Cannot locate buddy from "{self.objectName()}" item view!')
            return

        # Check if synchronization is already in progress
        #
        if self.isPending() or self.isBuddyPending():

            log.debug('Item views are already synchronizing!')
            return

        # Synchronize buddy
        #
        self.beginSelectionUpdate()
        self.buddy().selectRows(self.selectedRows())
        self.endSelectionUpdate()

        # Invalidate any item filters
        #
        self.invalidateFilters()

        # Emit synchronized signals
        #
        self.synchronized.emit()
        self.buddy().synchronized.emit()

    def invalidateFilters(self):
        """
        Invalidates the filters for both this and the buddy's model.

        :rtype: None
        """

        # Check if this model should be invalidated
        #
        model = self.model()

        if isinstance(model, QtCore.QSortFilterProxyModel):

            model.invalidateFilter()

        # Check if buddy's model should be invalidated
        #
        otherModel = self.buddy().model()

        if isinstance(otherModel, QtCore.QSortFilterProxyModel):

            otherModel.invalidateFilter()

    def firstRow(self):
        """
        Returns the first visible row.

        :rtype: int
        """

        activeInfluences = self.model().activeInfluences()
        numActiveInfluences = len(activeInfluences)

        if numActiveInfluences > 0:

            return activeInfluences[0]

        else:

            return None

    def selectFirstRow(self):
        """
        Selects the first row from the table.

        :rtype: None
        """

        firstRow = self.firstRow()

        if firstRow is not None:

            self.selectRows([firstRow])

    def selectedRows(self):
        """
        Returns the selected rows.

        :rtype: List[int]
        """

        return self._selectedRows

    def selectRow(self, row):
        """
        Selects the specified row.

        :type row: int
        :rtype: None
        """

        self.selectRows([row])

    def selectRows(self, rows):
        """
        Selects the supplied rows.

        :type rows: List[int]
        :rtype: None
        """

        # Compose item selection from rows
        #
        itemSelection = QtCore.QItemSelection()
        model = self.model()

        if isinstance(model, QtCore.QAbstractProxyModel):

            # Set any overrides
            #
            model.overrides = rows

            # Compose selection from source model
            #
            sourceModel = model.sourceModel()
            numColumns = sourceModel.columnCount()

            for row in rows:

                topLeft = sourceModel.index(row, 0)
                bottomRight = sourceModel.index(row, numColumns - 1)

                itemSelection.merge(QtCore.QItemSelection(topLeft, bottomRight), QtCore.QItemSelectionModel.Select)

            # Remap selection to source model
            #
            itemSelection = model.mapSelectionFromSource(itemSelection)

        else:

            # Compose selection from model
            #
            numColumns = model.columnCount()

            for row in rows:

                topLeft = model.index(row, 0)
                bottomRight = model.index(row, numColumns - 1)

                itemSelection.merge(QtCore.QItemSelection(topLeft, bottomRight), QtCore.QItemSelectionModel.Select)

        # Select items
        #
        self.selectionModel().select(itemSelection, QtCore.QItemSelectionModel.ClearAndSelect)
        self.scrollToTopRow()

    def scrollToTopRow(self):
        """
        Scrolls to the top-most selected row.

        :rtype: None
        """

        # Scroll to top row
        #
        rows = self.selectedRows()
        numRows = len(rows)

        if numRows > 0:

            # Create index from row
            #
            model = self.model()
            index = None

            if isinstance(model, QtCore.QAbstractProxyModel):

                index = model.sourceModel().index(rows[0], 0)
                index = model.mapFromSource(index)

            else:

                index = model.index(rows[0], 0)

            # Scroll to index
            #
            self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

        else:

            self.scrollToTop()

    def selectionChanged(self, selected, deselected):
        """
        Slot method called whenever the active selection is changed.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceView, self).selectionChanged(selected, deselected)

        # Cache selection changes
        #
        selection = self.selectionModel().selection()
        model = self.model()

        if isinstance(model, QtCore.QSortFilterProxyModel):

            selection = model.mapSelectionToSource(selection)

        self._selectedRows = list({index.row() for index in selection.indexes()})
        log.debug(f'"{self.objectName()}" selection changed: {self._selectedRows}')

        # Emit highlighted signal
        #
        self.highlighted.emit(selection)
    # endregion
