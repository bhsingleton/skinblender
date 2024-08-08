import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def contextGuard(func):
    """
    Returns a wrapper that queries if the active skin is valid before executing.
    This will help reduce the amount of conditions needed when we're not in edit mode.

    :type func: FunctionType
    :rtype: FunctionType
    """

    # Define wrapper function
    #
    def wrapper(self, *args, **kwargs):

        # Check if active skin is still valid
        #
        if self.skin.isValid():

            return func(self, *args, **kwargs)

        else:

            self.envelopePushButton.setChecked(False)

    return wrapper
