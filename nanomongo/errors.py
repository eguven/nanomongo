class ValidationError(Exception):
    """Raised when a field fails validation"""
    pass

class ExtraFieldError(Exception):
	"""Raised when a document has an undefined field"""