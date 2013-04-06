class ValidationError(Exception):
    """Raised when a field fails validation"""


class ExtraFieldError(Exception):
    """Raised when a document has an undefined field"""
