import fnmatch

from PySide2 import QtCore, QtWidgets, QtGui
from abc import abstractmethod
from dcc import fnskin, fnnode
from dcc.ui import qiconlibrary

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QInfluenceFilterModel(QtCore.QSortFilterProxyModel):
    """
    Overload of QSortFilterProxyModel used to filter influences.
    """

    def __init__(self, pattern, **kwargs):
        """
        Private method called after a new instance has been created.

        :type pattern: str
        :keyword parent: QtCore.QObject
        :rtype: None
        """

        # Call parent method
        #
        super(QInfluenceFilterModel, self).__init__(**kwargs)

        # Store filter pattern
        #
        self.pattern = pattern

    def filterAcceptsRow(self, row, parent):
        """
        Queries whether or not the supplied row should be filtered.

        :type row: int
        :type parent: QtCore.QModelIndex
        :rtype: bool
        """

        index = self.sourceModel().index(row, 0, parent)

        if index.isValid():

            text = self.sourceModel().itemFromIndex(index).text()
            return not fnmatch.fnmatch(text, self.pattern)

        else:

            return False


class QEditInfluencesDialog(QtWidgets.QDialog):
    """
    Overload of QDialog used to edit influences for a skin deformer.
    """

    __icons__ = {True: qiconlibrary.getIconByName('yes'), False: qiconlibrary.getIconByName('no')}

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        parent = kwargs.get('parent', QtWidgets.QApplication.activeWindow())
        f = kwargs.get('f', QtCore.Qt.WindowFlags())

        super(QEditInfluencesDialog, self).__init__(parent=parent, f=f)

        # Declare class variables
        #
        self._skin = fnskin.FnSkin()
        self._root = fnnode.FnNode()
        self._ignore = kwargs.get('ignore', '_*')

        # Build user interface
        #
        self.__build__(*args, **kwargs)

        # Check if any arguments were supplied
        #
        numArgs = len(args)

        if numArgs == 1:

            self.skin = args[0]

    def __build__(self, *args, **kwargs):
        """
        Private method that builds the user interface.

        :rtype: None
        """

        # Edit dialog properties
        #
        self.setObjectName('QEditInfluencesDialog')
        self.setWindowFlags(QtCore.Qt.Dialog)
        self.setMinimumSize(QtCore.QSize(250, 350))
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Define main layout
        #
        self.setLayout(QtWidgets.QVBoxLayout())

        # Create influence table widget
        #
        self.influenceTreeView = QtWidgets.QTreeView()
        self.influenceTreeView.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        self.influenceTreeView.setAlternatingRowColors(True)
        self.influenceTreeView.setUniformRowHeights(True)
        self.influenceTreeView.setItemsExpandable(True)
        self.influenceTreeView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.influenceTreeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.influenceTreeView.setStyleSheet('QTreeView:Item { height: 20px; }')
        self.influenceTreeView.expanded.connect(self.on_influenceTreeView_expanded)
        self.influenceTreeView.collapsed.connect(self.on_influenceTreeView_collapsed)

        self.influenceItemModel = QtGui.QStandardItemModel(0, 1, parent=self.influenceTreeView)
        self.influenceItemModel.setHorizontalHeaderLabels(['Joint'])

        self.influenceFilterModel = QInfluenceFilterModel(self._ignore, parent=self.influenceTreeView)
        self.influenceFilterModel.setSourceModel(self.influenceItemModel)
        self.influenceTreeView.setModel(self.influenceFilterModel)

        self.influenceTreeView.header().setStretchLastSection(True)
        self.influenceTreeView.header().setDefaultAlignment(QtCore.Qt.AlignCenter)

        self.layout().addWidget(self.influenceTreeView)

        # Create option buttons
        #
        self.optionsLayout = QtWidgets.QHBoxLayout()

        self.okayButton = QtWidgets.QPushButton('OK', self)
        self.okayButton.pressed.connect(self.accept)

        self.cancelButton = QtWidgets.QPushButton('Cancel', self)
        self.cancelButton.pressed.connect(self.reject)

        self.optionsLayout.addWidget(self.okayButton)
        self.optionsLayout.addWidget(self.cancelButton)

        self.layout().addLayout(self.optionsLayout)
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
        if self._skin.acceptsObject(skin):

            self._skin.setObject(skin)
            self._root.setObject(self._skin.findRoot())

            self.invalidate()

        else:

            raise TypeError('skin.setter() expects a valid object (%s given)!' % type(skin).__name__)

    @property
    def root(self):
        """
        Getter method used to retrieve associated skeleton root object.

        :rtype: fnnode.FnNode
        """

        return self._root

    @property
    def ignore(self):
        """
        Getter method that returns the ignore string.

        :rtype: str
        """

        return self._ignore
    # endregion

    # region Methods
    @abstractmethod
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        pass

    def getInfluenceIcon(self, influence):
        """
        Returns the display icon for the given influence.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: QtGui.QIcon
        """

        return self.__class__.__icons__[self.isValidInfluence(influence)]

    def appendInfluenceRow(self, influence, parentItem=None):
        """
        Recursive method used to add all child joints to tree widget.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :type parentItem: QtGui.QStandardItem
        :rtype: None
        """

        # Append row items
        #
        fnNode = fnnode.FnNode(influence)

        item = QtGui.QStandardItem(self.getInfluenceIcon(influence), fnNode.name())
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

    def expandChildren(self, item, expand=True):
        """
        Recursively expands all child nodes.

        :type item: QtGui.QStandardItem
        :type expand: bool
        :rtype: None
        """

        # Set expanded on item rows
        #
        index = item.index()
        expanded = self.influenceTreeView.isExpanded(index)

        rowCount = item.rowCount()

        for i in range(rowCount):

            row = item.child(i, 0)
            self.influenceTreeView.setExpanded(row.index(), expanded)

    def expandChildrenAtIndex(self, index):
        """
        Recursively expands all of the children at the specified index.

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

            expanded = self.influenceTreeView.isExpanded(index)

            for childItem in self.iterChildItems(item):

                childIndex = self.influenceFilterModel.mapFromSource(childItem.index())
                self.influenceTreeView.setExpanded(childIndex, expanded)

        else:

            log.debug('Shift is not pressed...')

        # Resize column headers
        #
        self.influenceTreeView.resizeColumnToContents(0)

    def iterChildItems(self, item):
        """
        Returns a generator that yields all child items.

        :type item: QtGui.QStandardItem
        :rtype: iter
        """

        # Iterate through item rows
        #
        rowCount = item.rowCount()

        for i in range(rowCount):

            yield item.child(i, 0)

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

        # Modify window title
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
    def accept(self):
        """
        Hides the modal dialog and sets the result code to QDialogCode.Accepted.

        :rtype: None
        """

        # Get selected influences before closing dialog
        #
        selectedInfluences = self.selectedInfluences()
        numSelected = len(selectedInfluences)

        # Call parent method
        #
        super(QAddInfluencesDialog, self).accept()

        # Check how many influences were selected
        #
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

        # Modify window title
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
    def accept(self):
        """
        Hides the modal dialog and sets the result code to QDialogCode.Accepted.

        :rtype: None
        """

        # Get selected influences before closing dialog
        #
        selectedInfluences = self.selectedInfluences()
        numSelected = len(selectedInfluences)

        # Call parent method
        #
        super(QRemoveInfluencesDialog, self).accept()

        # Check how many influences were selected
        #
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
    dialog = QAddInfluencesDialog()

    if dialog.skin.acceptsObject(skin):

        dialog.skin = skin
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
    dialog = QRemoveInfluencesDialog()

    if dialog.skin.acceptsObject(skin):

        dialog.skin = skin
        return dialog.exec_()

    else:

        log.warning('removeInfluences() expects a valid object (%s given)!' % type(skin).__name__)
        return 0
