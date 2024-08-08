from Qt import QtCore, QtWidgets, QtGui
from abc import abstractmethod
from dcc import fnskin, fnnode
from dcc.python import stringutils
from dcc.ui.dialogs import qmaindialog

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class QEditInfluencesDialog(qmaindialog.QMainDialog):
    """
    Overload of `QMainDialog` that add/removes influence objects from a skin.
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
        self._influences = {}
        self._usedInfluenceIds = []

        # Declare public variables
        #
        self.yesIcon = QtGui.QIcon(':dcc/icons/yes.png')
        self.noIcon = QtGui.QIcon(':dcc/icons/no.png')

        self.filterLineEdit = None
        self.influenceTreeView = None
        self.influenceItemModel = None  # type: QtGui.QStandardItemModel
        self.influenceItemFilterModel = None  # type: QtCore.QSortFilterProxyModel

        self.buttonsLayout = None
        self.buttonsWidget = None
        self.okayPushButton = None
        self.cancelPushButton = None

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QEditInfluencesDialog, self).__setup_ui__(*args, **kwargs)

        # Initialize dialog
        #
        self.setWindowTitle("|| Edit Influences")
        self.setMinimumSize(QtCore.QSize(250, 350))

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        self.setLayout(centralLayout)

        # Initialize influence tree-view
        #
        self.filterLineEdit = QtWidgets.QLineEdit()
        self.filterLineEdit.setObjectName('filterLineEdit')
        self.filterLineEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.filterLineEdit.setFixedHeight(24)
        self.filterLineEdit.setPlaceholderText('Filter Influences...')
        self.filterLineEdit.setClearButtonEnabled(True)
        self.filterLineEdit.textChanged.connect(self.on_filterLineEdit_textChanged)

        self.influenceTreeView = QtWidgets.QTreeView()
        self.influenceTreeView.setObjectName('influenceTreeView')
        self.influenceTreeView.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.influenceTreeView.setStyleSheet('QTreeView:item { height: 24; }')
        self.influenceTreeView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.influenceTreeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.influenceTreeView.setAlternatingRowColors(True)
        self.influenceTreeView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.influenceTreeView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.influenceTreeView.setRootIsDecorated(True)
        self.influenceTreeView.setUniformRowHeights(True)
        self.influenceTreeView.setAnimated(True)
        self.influenceTreeView.setHeaderHidden(True)
        self.influenceTreeView.expanded.connect(self.on_influenceTreeView_expanded)
        self.influenceTreeView.collapsed.connect(self.on_influenceTreeView_collapsed)

        self.influenceItemModel = QtGui.QStandardItemModel(0, 1, parent=self.influenceTreeView)
        self.influenceItemModel.setObjectName('influenceItemModel')
        self.influenceItemModel.setHorizontalHeaderLabels(['Name'])

        self.influenceItemFilterModel = QtCore.QSortFilterProxyModel(parent=self.influenceTreeView)
        self.influenceItemFilterModel.setObjectName('influenceItemFilterModel')
        self.influenceItemFilterModel.setSourceModel(self.influenceItemModel)
        self.influenceItemFilterModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.influenceItemFilterModel.setRecursiveFilteringEnabled(True)

        self.influenceTreeView.setModel(self.influenceItemFilterModel)

        centralLayout.addWidget(self.filterLineEdit)
        centralLayout.addWidget(self.influenceTreeView)

        # Initialize buttons widget
        #
        self.buttonsLayout = QtWidgets.QHBoxLayout()
        self.buttonsLayout.setObjectName('buttonsLayout')
        self.buttonsLayout.setContentsMargins(0, 0, 0, 0)

        self.buttonsWidget = QtWidgets.QWidget()
        self.buttonsWidget.setObjectName('buttonsWidget')
        self.buttonsWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.buttonsWidget.setFixedHeight(24)
        self.buttonsWidget.setLayout(self.buttonsLayout)

        self.okayPushButton = QtWidgets.QPushButton('OK')
        self.okayPushButton.setObjectName('okayPushButton')
        self.okayPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.okayPushButton.clicked.connect(self.accept)

        self.cancelPushButton = QtWidgets.QPushButton('Cancel')
        self.cancelPushButton.setObjectName('cancelPushButton')
        self.cancelPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.cancelPushButton.clicked.connect(self.reject)

        self.buttonsLayout.addWidget(self.okayPushButton)
        self.buttonsLayout.addWidget(self.cancelPushButton)

        centralLayout.addWidget(self.buttonsWidget)
    # endregion

    # region Properties
    @property
    def skin(self):
        """
        Getter method that returns the skin interface.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @skin.setter
    def skin(self, skin):
        """
        Setter method that updates the skin interface.

        :type skin: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: None
        """

        # Check if object is compatible
        #
        success = self._skin.trySetObject(skin)

        if success:

            self._root.setObject(self._skin.findRoot())
            self._influences = self._skin.influences()
            self._usedInfluenceIds = self._skin.getUsedInfluenceIds()

            self.invalidate()

    @property
    def root(self):
        """
        Getter method that returns the skin influence root.

        :rtype: fnnode.FnNode
        """

        return self._root

    @property
    def influences(self):
        """
        Getter method that returns the skin influence objects.

        :rtype: Dict[int, fnnode.FnNode]
        """

        return self._influences

    @property
    def usedInfluenceIds(self):
        """
        Getter method that returns the active influence IDs.

        :rtype: List[int]
        """

        return self._usedInfluenceIds

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
        icon = self.yesIcon if isValid else self.noIcon
        name = influence.absoluteName()
        whatsThis = name if isValid else ''

        item = QtGui.QStandardItem(icon, name)
        item.setWhatsThis(whatsThis)

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

    def selectedInfluences(self, id=False):
        """
        Returns a list of the selected influence names.

        :type id: bool
        :rtype: List[int]
        """

        # Get selected items
        #
        selectedIndices = self.influenceTreeView.selectedIndexes()
        influences = []

        for (i, index) in enumerate(selectedIndices):

            # Check if selected item is valid
            #
            index = self.influenceItemFilterModel.mapToSource(index)
            item = self.influenceItemModel.itemFromIndex(index)
            whatsThis = item.whatsThis()

            isValid = not stringutils.isNullOrEmpty(whatsThis)

            if not isValid:

                continue

            # Check if ID should be returned
            #
            if id:

                influences.append(self.influences.index(whatsThis))

            else:

                influences.append(item.text())

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
        Slot method for the `filterLineEdit` widget's `textChanged` signal.

        :type text: str
        :rtype: None
        """

        filterWildcard = '*{text}*'.format(text=text)
        self.influenceItemFilterModel.setFilterWildcard(filterWildcard)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTreeView_expanded(self, index):
        """
        Slot method for the `influenceTreeView` widget's `expanded` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        self.expandChildrenAtIndex(index)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_influenceTreeView_collapsed(self, index):
        """
        Slot method for the `influenceTreeView` widget's `collapsed` signal.

        :type index: QtCore.QModelIndex
        :rtype: None
        """

        self.expandChildrenAtIndex(index)
    # endregion


class QAddInfluencesDialog(QEditInfluencesDialog):
    """
    Overload of `QEditInfluencesDialog` that adds influences to a skin.
    """

    # region Dunderscores
    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QAddInfluencesDialog, self).__setup_ui__(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Add Influence(s)')
    # endregion

    # region Methods
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        return influence not in self.influences
    # endregion

    # region Slots
    @QtCore.Slot()
    def accept(self):
        """
        Slot method for the dialog's `accept` signal.

        :rtype: None
        """

        # Check how many influences were selected
        #
        selectedInfluences = self.selectedInfluences(id=False)
        numSelected = len(selectedInfluences)

        if numSelected > 0:

            log.debug(f'Adding influences: {selectedInfluences}')
            self.skin.addInfluence(*selectedInfluences)

        else:

            log.warning('No influences selected to add!')

        # Call parent method
        #
        super(QAddInfluencesDialog, self).accept()
    # endregion


class QRemoveInfluencesDialog(QEditInfluencesDialog):
    """
    Overload of `QEditInfluencesDialog` that removes influences from a skin.
    """

    # region Dunderscores
    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QRemoveInfluencesDialog, self).__setup_ui__(*args, **kwargs)

        # Edit window title
        #
        self.setWindowTitle('|| Remove Influence(s)')
    # endregion

    # region Methods
    def isValidInfluence(self, influence):
        """
        Evaluates if the supplied influence is valid.

        :type influence: Union[om.MObject, pymxs.MXSWrapperBase]
        :rtype: bool
        """

        influenceId = self.influences.index(influence)
        return influenceId is not None and influenceId not in self.usedInfluenceIds
    # endregion

    # region Slots
    @QtCore.Slot()
    def accept(self):
        """
        Slot method for the dialog's `accept` signal.

        :rtype: None
        """

        # Check how many influences were selected
        #
        selectedInfluences = self.selectedInfluences(id=True)
        numSelected = len(selectedInfluences)

        if numSelected > 0:

            log.debug(f'Removing influences: {selectedInfluences}')
            self.skin.removeInfluence(*selectedInfluences)

        else:

            log.warning('No influences selected to add!')

        # Call parent method
        #
        super(QRemoveInfluencesDialog, self).accept()
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
