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
    Overload of `QUicDialog` that edit influences for a skin.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QMainWindow
        :key f: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QEditInfluencesDialog, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._root = fnnode.FnNode()

        # Declare public variables
        #
        self.filterLineEdit = None
        self.influenceTreeView = None
        self.influenceItemModel = None  # type: QtGui.QStandardItemModel
        self.influenceItemFilterModel = None  # type: QtCore.QSortFilterProxyModel
        self.buttonsWidget = None
        self.okayPushButton = None
        self.cancelPushButton = None
    # endregion

    # region Properties
    @property
    def skin(self):
        """
        Getter method used to retrieve the skin cluster object.

        :rtype: fnskin.FnSkin
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
    def textFilter(self):
        """
        Getter method that returns the text filter.

        :rtype: str
        """

        return self.filterLineEdit.text()

    @textFilter.setter
    def textFilter(self, text):
        """
        Setter method that updates the text filter.

        :type text: str
        :rtype: None
        """

        self.filterLineEdit.setText(text)
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QEditInfluencesDialog, self).postLoad(*args, **kwargs)

        # Initialize item model
        #
        self.influenceItemModel = QtGui.QStandardItemModel(0, 1, parent=self.influenceTreeView)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Joint'])

        # Initialize filter model
        #
        self.influenceItemFilterModel = QtCore.QSortFilterProxyModel(parent=self.influenceTreeView)
        self.influenceItemFilterModel.setObjectName('influenceItemFilterModel')
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)

        # Assign filter model to tree view
        #
        self.influenceTreeView.setModel(self.influenceItemFilterModel)

    @abstractmethod
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: fnnode.FnNode
        :rtype: bool
        """

        pass

    def appendInfluenceItem(self, influence, parentItem=None):
        """
        Recursive method used to add all child joints to tree widget.

        :type influence: fnnode.FnNode
        :type parentItem: QtGui.QStandardItem
        :rtype: None
        """

        # Redundancy check
        #
        if influence is None:

            return

        # Append row items
        #
        isValid = self.isValidInfluence(influence)
        icon = QtGui.QIcon(':dcc/icons/yes.png') if isValid else QtGui.QIcon(':dcc/icons/no.png')
        name = influence.name()

        item = QtGui.QStandardItem(icon, name)
        parentItem.appendRow(item)

        # Iterate through children
        #
        child = fnnode.FnNode()

        for obj in influence.iterChildren():

            # Check if child is a joint
            #
            child.setObject(obj)

            if child.isJoint():

                self.appendInfluenceItem(child, parentItem=item)

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
            sourceIndex = self.influenceItemFilterModel.mapToSource(index)
            item = self.influenceItemModel.itemFromIndex(sourceIndex)

            # Iterate through children and set expanded
            #
            expanded = self.influenceTreeView.isExpanded(index)
            rowCount = item.rowCount()

            for i in range(rowCount):

                childItem = item.child(i, 0)
                childIndex = self.influenceItemFilterModel.mapFromSource(childItem.index())

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
            itemIndex = self.influenceItemFilterModel.mapToSource(index)
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

        # Check if skin and root are valid
        #
        self.influenceItemModel.setRowCount(0)

        if self.skin.isValid() and self.root.isValid():

            self.appendInfluenceItem(self.root, parentItem=self.influenceItemModel.invisibleRootItem())

        else:

            log.debug('Unable to invalidate influence model!')
    # endregion

    # region Slots
    @QtCore.Slot(str)
    def on_filterLineEdit_textChanged(self, text):
        """
        Slot method for the filterLineEdit's `textChanged` signal.

        :type text: str
        :rtype: None
        """

        filterWildcard = '*{text}*'.format(text=text)
        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

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
    Overload of `QEditInfluencesDialog` that adds influences to a skin.
    """

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QAddInfluencesDialog, self).postLoad(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Add Influences')

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

            self.skin.addInfluence(*selectedInfluences)

        else:

            log.warning('No influences selected to add!')
    # endregion


class QRemoveInfluencesDialog(QEditInfluencesDialog):
    """
    Overload of `QEditInfluencesDialog` that removes influences from a skin.
    """

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QRemoveInfluencesDialog, self).postLoad(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Add Influences')

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

            self.skin.removeInfluence(*selectedInfluences)

        else:

            log.warning('No influences selected to add!')
    # endregion


def addInfluences(skin, parent=None):
    """
    Opens a dialog to add influences to the specified skin.

    :type skin: Any
    :type parent: QtWidgets.QWidget
    :rtype: int
    """

    # Check if skin cluster is valid
    #
    dialog = QAddInfluencesDialog(skin=skin, parent=parent)

    if dialog.skin.isValid():

        return dialog.exec_()

    else:

        log.warning('addInfluences() expects a valid object (%s given)!' % type(skin).__name__)
        return 0


def removeInfluences(skin, parent=None):
    """
    Opens a dialog to removes influences from the specified skin.

    :type skin: Any
    :type parent: QtWidgets.QWidget
    :rtype: int
    """

    # Check if skin cluster is valid
    #
    dialog = QRemoveInfluencesDialog(skin=skin, parent=parent)

    if dialog.skin.isValid():

        return dialog.exec_()

    else:

        log.warning('removeInfluences() expects a valid object (%s given)!' % type(skin).__name__)
        return 0
