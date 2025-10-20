from ..ui import qskinblender

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def uiAccessor(func):
    """
    Returns a wrapper that validates functions against the UI before executing.
    This will help reduce the amount of conditions needed when we're not in edit mode.

    :type func: Callable
    :rtype: Callable
    """

    # Define validation wrapper
    #
    def wrapper(*args, **kwargs):

        # Check if window exists
        #
        window = qskinblender.QSkinBlender.getInstance()

        if window is not None:

            return func(*args, window=window, **kwargs)

        else:

            log.warning("Cannot locate Skin-Blender window!")

    return wrapper
