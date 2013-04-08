class ValidationError(Exception):
    """Raised when a field fails validation"""


class ExtraFieldError(Exception):
    """Raised when a document has an undefined field"""


class ConfigurationError(Exception):
    """Raised when a required value found to be not set during
    operation, or a Document class is registered more than once
    """


class IndexMismatchError(Exception):
    """Raised when a defined index does not match defined fields"""
