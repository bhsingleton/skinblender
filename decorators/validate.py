def validate(func):
    """
    Returns a wrapper that validates functions against the UI before executing.
    This will help reduce the amount of conditions needed when we're not in edit mode.

    :type func: Callable
    :rtype: Callable
    """

    # Define validation wrapper
    #
    def wrapper(*args, **kwargs):

        # Check if skin is still valid
        #
        window = args[0]

        if window.skin.isValid():

            return func(*args, **kwargs)

        else:

            return

    return wrapper
