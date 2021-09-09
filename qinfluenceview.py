from PySide2 import QtCore, QtWidgets, QtGui

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceView(QtWidgets.QTableView):
    """
    Overload of QTableView used to display skin influences.
    This widget also has builtin auto select functionality for siblings.
    """

    synchronized = QtCore.Signal()

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
        self._sibling = None
        self._autoSelect = True
        self._pending = False
        self._selectedRows = []

        # Modify view properties
        #
        self.setShowGrid(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def sibling(self):
        """
        Returns the sibling widget.
        If there is no sibling then none is returned!

        :rtype: QInfluenceView
        """

        return self._sibling

    def setSibling(self, sibling):
        """
        Updates the sibling for this widget.

        :type sibling: QInfluenceView
        :rtype: None
        """

        # Check value type
        #
        if not isinstance(sibling, QInfluenceView):

            raise TypeError('setSibling() expects a QInfluenceView (%s given)!' % type(sibling).__name__)

        self._sibling = sibling

    def hasSibling(self):
        """
        Evaluates if this widget has a sibling.

        :rtype: bool
        """

        return self._sibling is not None

    def autoSelect(self):
        """
        Returns the auto select state.

        :rtype: bool
        """

        return self._autoSelect

    def setAutoSelect(self, autoSelect):
        """
        Evaluates the auto select state.

        :type autoSelect: bool
        :rtype: None
        """

        self._autoSelect = autoSelect

    def beginSelectionUpdate(self):
        """
        Changes the filter state to prevent cyclical errors.

        :rtype: None
        """

        self._pending = True

    def endSelectionUpdate(self):
        """
        Changes the filter state to prevent cyclical errors.

        :rtype: None
        """

        self._pending = False

    def isPending(self):
        """
        Evaluates if this widget is currently synchronizing its sibling.

        :rtype: bool
        """

        return self._pending

    def isSiblingPending(self):
        """
        Evaluates if the sibling is attempting to synchronize with this widget.

        :rtype: bool
        """

        if self.hasSibling():

            return self.sibling().isPending()

        else:

            return False

    def firstRow(self):
        """
        Returns the first visible row.

        :rtype: int
        """

        return self.model().activeInfluences[0]

    def selectFirstRow(self):
        """
        Selects the first row from the table.

        :rtype: None
        """

        return self.selectRows([self.firstRow()])

    def selectedRows(self):
        """
        Returns the selected rows.

        :rtype: list[int]
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

        :type rows: list[int]
        :rtype: None
        """

        # Compose item selection from rows
        #
        itemSelection = QtCore.QItemSelection()
        model = self.model()

        if isinstance(model, QtCore.QAbstractProxyModel):

            # Set any overrides
            #
            model.setOverrides(*rows)

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

        # Scroll to top row
        #
        numRows = len(rows)

        if numRows > 0:

            # Create index from row
            #
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

        # Get selected rows
        #
        indices = selected.indexes()
        model = self.model()

        if isinstance(model, QtCore.QAbstractProxyModel):

            self._selectedRows = [model.mapToSource(x).row() for x in indices]

        else:

            self._selectedRows = [x.row() for x in indices]

        # Force the sibling to match selections
        # Be sure to check if a sync is pending to avoid cycle checks!
        #
        if self.autoSelect() and (self.hasSibling() and not self.isSiblingPending()):

            self.beginSelectionUpdate()
            self.sibling().selectRows(self._selectedRows)
            self.endSelectionUpdate()

            self.synchronized.emit()
