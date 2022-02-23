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

        if sourceModel.isNullWeight(index):

            # Check if row is in overrides
            #
            if row in self._overrides:

                self._activeInfluences.append(row)
                self._overrides.remove(row)
                return True

            else:

                self._inactiveInfluences.append(row)
                return False

        else:

            return super(QWeightItemFilterModel, self).filterAcceptsRow(row, parent)
