from . import qezskinblender

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def togglePrecision():
    """
    Toggles precision mode on the main window.

    :rtype: None
    """

    instance = qezskinblender.QEzSkinBlender.getInstance()

    if instance is not None:

        instance.precision = not instance.precision

    else:

        log.warning("Cannot locate Ez'Skin-Blender window!")


def copyWeights():
    """
    Calls the copy weights action from the main window.

    :rtype: None
    """

    instance = qezskinblender.QEzSkinBlender.getInstance()

    if instance is not None:

        instance.copyWeights()

    else:

        log.warning("Cannot locate Ez'Skin-Blender window!")


def pasteWeights(average=False):
    """
    Calls the paste weights action from the main window.

    :type average: bool
    :rtype: None
    """

    instance = qezskinblender.QEzSkinBlender.getInstance()

    if instance is not None:

        instance.pasteWeights(average=average)

    else:

        log.warning("Cannot locate Ez'Skin-Blender window!")


def blendVertices():
    """
    Calls the blend vertices action from the main window.

    :rtype: None
    """

    instance = qezskinblender.QEzSkinBlender.getInstance()

    if instance is not None:

        instance.blendVertices()

    else:

        log.warning("Cannot locate Ez'Skin-Blender window!")


def blendBetweenVertices():
    """
    Calls the blend between vertices action from the main window.

    :rtype: None
    """

    instance = qezskinblender.QEzSkinBlender.getInstance()

    if instance is not None:

        instance.blendBetweenVertices()

    else:

        log.warning("Cannot locate Ez'Skin-Blender window!")
