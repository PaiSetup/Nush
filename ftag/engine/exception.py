class TagEngineException(Exception):
    def __init__(self, message, developer_error=False):
        self.message = message
        if developer_error and message is not None:
            self.message += " This is a developer error. It should never happen and it's likely a bug in ftag."
