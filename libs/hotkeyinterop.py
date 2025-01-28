from Qt import QtCore
from ..ui import qezskinblender
from ..decorators.uiaccessor import uiAccessor

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def showWindow():
    """
    Shows the main window.

    :rtype: None
    """

    hasInstance = qezskinblender.QEzSkinBlender.hasInstance()

    if not hasInstance:

        window = qezskinblender.QEzSkinBlender()
        window.show()

    else:

        window = qezskinblender.QEzSkinBlender.getInstance()
        window.setFocus(QtCore.Qt.ActiveWindowFocusReason)


@uiAccessor
def togglePrecision(window=None):
    """
    Toggles precision mode on the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.precision = not window.precision


@uiAccessor
def copyWeights(window=None):
    """
    Calls the copy weights action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.copyWeights()


@uiAccessor
def pasteWeights(average=False, window=None):
    """
    Calls the paste weights action from the main window.

    :type average: bool
    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.pasteWeights(average=average)


@uiAccessor
def pruneWeights(window=None):
    """
    Calls the prune vertices action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.pruneWeights()


@uiAccessor
def relaxVertices(window=None):
    """
    Calls the relax vertices action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.relaxVertices()


@uiAccessor
def blendVertices(window=None):
    """
    Calls the blend vertices action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.blendVertices()


@uiAccessor
def blendBetweenVertices(window=None):
    """
    Calls the blend between vertices action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.blendBetweenVertices()


@uiAccessor
def setWeights(amount, window=None):
    """
    Calls the set vertices action from the main window.

    :type amount: float
    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.setWeights(amount)


@uiAccessor
def incrementWeights(window=None):
    """
    Calls the increment weights button from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    amount = window.incrementWeightSpinBox.value()
    window.incrementWeights(amount)


@uiAccessor
def decrementWeights(window=None):
    """
    Calls the decrement weights button from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    amount = window.incrementWeightSpinBox.value()
    window.incrementWeights(-amount)


@uiAccessor
def pruneWeights(window=None):
    """
    Calls the prune vertices action from the main window.

    :type window: qezskinblender.QEzSkinBlender
    :rtype: None
    """

    window.pruneWeights()
