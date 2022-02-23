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

        if self.hasBuddy():

            self.beginSelectionUpdate()
            self.buddy().selectRows(self._selectedRows)
            self.endSelectionUpdate()

            self.synchronized.emit()

    def firstRow(self):
        """
        Returns the first visible row.

        :rtype: int
        """

        model = self.model()
        numActiveInfluences = len(model.activeInfluences)

        if numActiveInfluences > 0:

            return model.activeInfluences[0]

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

        # Update internal selection tracker
        # Be aware that QItemSelection stores both row and column indices!
        #
        model = self.model()

        if isinstance(model, QtCore.QAbstractProxyModel):

            self._selectedRows = [model.mapToSource(x).row() for x in selected.indexes() if model.mapToSource(x).column() == 0]

        else:

            self._selectedRows = [x.row() for x in selected.indexes() if x.column() == 0]

        # Force the sibling to match selections
        # Be sure to check if a sync is pending to avoid cycle checks!
        #
        if self.autoSelect() and (self.hasBuddy() and not self.isBuddyPending()):

            self.synchronize()
    # endregion
