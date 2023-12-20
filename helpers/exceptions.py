# This class is used for exceptions that can be directly displayed to the user
class UserFriendlyError(Exception):
    pass


# This class indicates an issue with the syntax of a command
class CommandSyntaxError(Exception):
    pass
