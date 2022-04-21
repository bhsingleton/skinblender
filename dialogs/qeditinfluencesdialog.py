from Qt import QtCore, QtWidgets, QtGui
from abc import abstractmethod
from dcc import fnskin, fnnode
from dcc.ui.dialogs import quicdialog

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QEditInfluencesDialog(quicdialog.QUicDialog):
    """
    Overload of QDialog used to edit influences for a skin deformer.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._root = fnnode.FnNode()

        # Declare public variables
        #
        self.influenceItemModel = None  # type: QtGui.QStandardItemModel
        self.influenceFilterModel = None  # type: QtCore.QSortFilterProxyModel

        # Call parent method
        #
        super(QEditInfluencesDialog, self).__init__(*args, **kwargs)
    # endregion

    # region Properties
    @property
    def skin(self):
        """
        Getter method used to retrieve the skin cluster object.

        :return: fnskin.FnSkin

        """

        return self._skin

    @skin.setter
    def skin(self, skin):
        """
        Setter method used to update the skin cluster object.

        :type skin: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: None
        """

        # Check if object is compatible
        #
        success = self._skin.trySetObject(skin)

        if success:

            self._root.setObject(self._skin.findRoot())
            self.invalidate()

    @property
    def root(self):
        """
        Getter method used to retrieve associated skeleton root object.

        :rtype: fnnode.FnNode
        """

        return self._root

    @property
    def filterWildcard(self):
        """
        Getter method that returns the filter wildcard expression.

        :rtype: str
        """

        return self.influenceFilterModel.filterWildcard()

    @filterWildcard.setter
    def filterWildcard(self, filterWildcard):
        """
        Setter method that updates the filter wildcard expression.

        :type filterWildcard: str
        :rtype: None
        """

        self.influenceFilterModel.setFilterWildcard(filterWildcard)
    # endregion

    # region Methods
    def postLoad(self):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Initialize item model
        #
        self.influenceItemModel = QtGui.QStandardItemModel(0, 1, parent=self.influenceTreeView)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Joint'])

        # Initialize filter model
        #
        self.influenceFilterModel = QtCore.QSortFilterProxyModel(parent=self.influenceTreeView)
        self.influenceFilterModel.setObjectName('influenceFilterModel')
        self.influenceFilterModel.setFilterWildcard('*')
        self.influenceFilterModel.setSourceModel(self.influenceItemModel)

        # Assign filter model to tree view
        #
        self.influenceTreeView.setModel(self.influenceFilterModel)

    @abstractmethod
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        pass

    def appendInfluenceRow(self, influence, parentItem=None):
        """
        Recursive method used to add all child joints to tree widget.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :type parentItem: QtGui.QStandardItem
        :rtype: None
        """

        # Initialize function set
        #
        fnNode = fnnode.FnNode()
        success = fnNode.trySetObject(influence)

        if not success:

            return

        # Append row items
        #
        isValidInfluence = self.isValidInfluence(influence)
        icon = QtGui.QIcon(':dcc/icons/yes.png') if isValidInfluence else QtGui.QIcon(':dcc/icons/no.png')
        item = QtGui.QStandardItem(icon, fnNode.name())

        parentItem.appendRow(item)

        # Iterate through children
        #
        fnChild = fnnode.FnNode()

        for child in fnNode.iterChildren():

            # Check if child is a joint
            #
            fnChild.setObject(child)

            if fnChild.isJoint():

                self.appendInfluenceRow(child, parentItem=item)

            else:

                continue

    def expandChildrenAtIndex(self, index):
        """
        Recursively expands all the children at the specified index.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        # Check if shift is pressed
        #
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        if modifiers == QtCore.Qt.ShiftModifier:

            # Get item from index
            #
            sourceIndex = self.influenceFilterModel.mapToSource(index)
            item = self.influenceItemModel.itemFromIndex(sourceIndex)

            # Iterate through children and set expanded
            #
            expanded = self.influenceTreeView.isExpanded(index)
            rowCount = item.rowCount()

            for i in range(rowCount):

                childItem = item.child(i, 0)
                childIndex = self.influenceFilterModel.mapFromSource(childItem.index())

                self.influenceTreeView.setExpanded(childIndex, expanded)

        else:

            log.debug('Shift is not pressed...')

        # Resize column headers
        #
        self.influenceTreeView.resizeColumnToContents(0)

    def selectedInfluences(self):
        """
        Returns a list the selected influence objects.

        :rtype: list
        """

        # Get selected items
        #
        selectedIndices = self.influenceTreeView.selectedIndexes()
        influences = []

        for index in selectedIndices:

            # Get item from index
            #
            itemIndex = self.influenceFilterModel.mapToSource(index)
            item = self.influenceItemModel.itemFromIndex(itemIndex)

            # Check if item is valid
            #
            influenceName = item.text()
            isValid = self.isValidInfluence(influenceName)

            if isValid:

                influence = fnnode.FnNode.getNodeByName(influenceName)
                influences.append(influence)

            else:

                log.warning('Unable to add %s influence!' % influenceName)

        return influences

    def invalidate(self):
        """
        Re-populates the tree view if the skin and root objects are valid.

        :rtype: None
        """

        # Check for none type
        #
        self.influenceItemModel.setRowCount(0)

        if not self.skin.isValid() or not self.root.isValid():

            return

        # Create root node
        #
        self.appendInfluenceRow(self.root.object(), parentItem=self.influenceItemModel.invisibleRootItem())
    # endregion

    # regions Slots
    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTreeView_expanded(self, index):
        """
        Expanded slot method responsible for recursively expanding all derived items.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        self.expandChildrenAtIndex(index)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTreeView_collapsed(self, index):
        """
        Collapsed slot method responsible for recursively collapsing all derived items.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        self.expandChildrenAtIndex(index)
    # endregion


class QAddInfluencesDialog(QEditInfluencesDialog):
    """
    Overload of QEditInfluencesDialog used to add influences to a skin deformer.
    """

    # region Dunderscores
    def __build__(self, *args, **kwargs):
        """
        Private method used to build the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QAddInfluencesDialog, self).__build__(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Add Influences')
    # endregion

    # region Methods
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        return influence not in self.skin.influences()
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
        super(QAddInfluencesDialog, self).accept()

        # Check how many influences were selected
        #
        selectedInfluences = self.selectedInfluences()
        numSelected = len(selectedInfluences)

        if numSelected > 0:

            self.skin.addInfluences(selectedInfluences)

        else:

            log.warning('No influences selected to add!')
    # endregion


class QRemoveInfluencesDialog(QEditInfluencesDialog):
    """
    Overload of QEditInfluencesDialog used to remove influences from a skin deformer.
    """

    # region Dunderscores
    def __build__(self, *args, **kwargs):
        """
        Private method used to build the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QRemoveInfluencesDialog, self).__build__(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Remove Influences')
    # endregion

    # region Methods
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        return influence in self.skin.influences()
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
        super(QRemoveInfluencesDialog, self).accept()

        # Check how many influences were selected
        #
        selectedInfluences = self.selectedInfluences()
        numSelected = len(selectedInfluences)

        if numSelected > 0:

            self.skin.removeInfluences(selectedInfluences)

        else:

            log.warning('No influences selected to add!')
    # endregion


def addInfluences(skin):
    """
    Opens a dialog to add influences to the supplied skin deformer.

    :type skin: Union[om.MObject, pymxs.MXSWrapperBase]
    :rtype: int
    """

    # Check if skin cluster is valid
    #
    dialog = QAddInfluencesDialog(skin=skin)

    if dialog.skin.isValid():

        return dialog.exec_()

    else:

        log.warning('addInfluences() expects a valid object (%s given)!' % type(skin).__name__)
        return 0


def removeInfluences(skin):
    """
    Opens a dialog to removes influences from the supplied skin deformer.

    :type skin: Union[om.MObject, pymxs.MXSWrapperBase]
    :rtype: int
    """

    # Check if skin cluster is valid
    #
    dialog = QRemoveInfluencesDialog(skin=skin)

    if dialog.skin.isValid():

        return dialog.exec_()

    else:

        log.warning('removeInfluences() expects a valid object (%s given)!' % type(skin).__name__)
        return 0
