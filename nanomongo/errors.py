class NanomongoError(Exception):
    """Base nanomongo error"""


class ValidationError(NanomongoError):
    """Raised when a field fails validation"""


class ExtraFieldError(NanomongoError):
    """Raised when a document has an undefined field"""


class ConfigurationError(NanomongoError):
    """Raised when a required value found to be not set during
    operation, or a Document class is registered more than once
    """


class IndexMismatchError(NanomongoError):
    """Raised when a defined index does not match defined fields"""


class UnsupportedOperation(NanomongoError):
    """Raised when an unsupported opperation/parameters are used"""
