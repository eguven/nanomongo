import datetime

from bson import DBRef, ObjectId

from .errors import ValidationError

class Field(object):
    """Instances of this class is used to define field types and automatically
    create validators. Note that a Field definition has no value added.

        field_name = Field(str, default='cheeseburger', max_length=42)

    TODO: custom field validator
    """
    allowed_types = (bool, int, float, bytes, str, list, dict, datetime.datetime, DBRef, ObjectId)
    containers = (bytes, str, list, dict)
    # kwarg_name : kwarg_input_validator dictionaries
    allowed_kwargs = {'default': lambda v: True,
                      'none_ok': lambda v: isinstance(v, bool),
                     }
    container_kwargs = {'max_length': lambda v: isinstance(v, int) and v >= 0,
                        'empty_ok': lambda v: isinstance(v, bool),
                       }

    def __init__(self, *args, **kwargs):
        """Field kwargs are checked for correctness and field validator is set
        during __init__

        :Keyword Arguments:
          - `default`: default field value, must past type check
          - `none_ok`: if ``True`` field value can be ``None`` (bool)
          - `max_length`: maximum allowed ``len`` for the field value (``containers``) (int, long >= 0)
          - `empty_ok`: if ``True`` field value can be empty eg. ``[]`` or ``''`` or ``{}`` (bool)
        """
        assert args, 'Field definition incorrect, please provide type'
        assert isinstance(args[0], type), 'Field input not a type'
        self.type_ = args[0]
        if self.type_ not in self.allowed_types and not issubclass(self.type_, self.allowed_types):
            raise AssertionError('Field input type %s is not allowed' % self.type_)
        err_str = args[0].__name__ + ': %s argument not allowed or %s value invalid'
        # check if Field keyword arguments are valid
        for k, v in kwargs.items():
            if k in self.allowed_kwargs:
                assert self.allowed_kwargs[k](v), err_str % (k, v)
            elif issubclass(self.type_, self.containers) and k in self.container_kwargs:
                assert self.container_kwargs[k](v), err_str % (k, v)
            else:
                raise AssertionError(err_str % (k, v))
        self.validator = self.generate_validator(self.type_, **kwargs)
        if 'default' in kwargs and not callable(kwargs['default']):
            try:
                self.validator(kwargs['default'])
            except ValidationError as e:
                new_err = ('default value "%s"' % kwargs['default']) + ''.join(e.args)
                raise AssertionError(new_err)

    def generate_validator(self, t, **kwargs):
        """Generates and returns validator function (value_to_check, field_name='').
        `field_name` kwarg is optional, used for better error reporting
        """
        def validator(val, field_name=''):
            if val is None and 'none_ok' in kwargs and kwargs['none_ok']:
                return True
            elif val is None:
                raise ValidationError('%s: None is not allowed' % field_name)
            if not isinstance(val, t):
                raise ValidationError('%s: "%s" not an instance of %s but an instance of %s' %
                                      (field_name, val, t, type(val)))
            if isinstance(val, self.containers):
                if 0 == len(val) and ('empty_ok' not in kwargs or not kwargs['empty_ok']):
                    raise ValidationError('%s: cannot be empty' % field_name)
                elif 'max_length' in kwargs and kwargs['max_length'] < len(val):
                    raise ValidationError('%s: %d > max_length=%d' % (field_name, len(val), kwargs['max_length']))
            return True
        return validator