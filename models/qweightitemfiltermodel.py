from . import qinfluenceitemfiltermodel

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QWeightItemFilterModel(qinfluenceitemfiltermodel.QInfluenceItemFilterModel):
    """
    Overload of QSortFilterProxyModel used to filter influence weights.
    """

    def filterAcceptsRow(self, row, parent):
        """
        Returns true if the item in the row indicated should be included in the model.

        :type row: int
        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        # Check if row contains null data
        #
        sourceModel = self.sourceModel()
        index = sourceModel.index(row, 0, parent=parent)

        if sourceModel.isNullInfluence(index):

            return False

        # Check if row contains null weights
        #
        if not sourceModel.isNullWeight(index):

            return True

        else:

            # Check if exception can be made to row
            #
            selectedRows = self.parent().selectedRows()

            if row in self._overrides:

                self._overrides.remove(row)
                return True

            elif row in selectedRows:

                return True

            else:

                return False
