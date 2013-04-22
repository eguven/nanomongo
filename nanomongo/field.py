import copy
import datetime

from bson import DBRef, ObjectId

from .errors import ValidationError
from .util import check_keys


class Field(object):
    """Instances of this class is used to define field types and automatically
    create validators. Note that a Field definition has no value added::

        field_name = Field(str, default='cheeseburger')
        foo = Field(datetime, auto_update=True)
        bar = Field(list, required=False)

    """
    allowed_types = (bool, int, float, bytes, str, list, dict, datetime.datetime, DBRef, ObjectId)
    # kwarg_name : kwarg_input_validator dictionaries
    allowed_kwargs = {
        'default': lambda v: True,
        'required': lambda v: isinstance(v, bool),
    }
    extra_kwargs = {
        datetime.datetime: {'auto_update': lambda v: isinstance(v, bool)}
    }

    def __init__(self, *args, **kwargs):
        """Field kwargs are checked for correctness and field validator is set,
        along with other attributes such as ``required`` and ``auto_update``

        :Keyword Arguments:
          - `default`: default field value, must pass type check, can be a ``callable``
          - `required`: if ``True`` field must exist and not be ``None`` (default: ``True``)
          - `auto_update`: set value to ``datetime.utcnow()`` before inserts/saves;
            only valid for datetime fields (default: ``False``)

        """
        if not args:
            raise TypeError('Field definition incorrect, please provide type')
        elif not isinstance(args[0], type):
            raise TypeError('Field input not a type')
        self.data_type = args[0]
        if ((self.data_type not in self.allowed_types and
             not issubclass(self.data_type, self.allowed_types))):
            raise TypeError('Field input type %s is not allowed' % self.data_type)
        self.check_kwargs(kwargs, self.data_type)
        # attributes
        if 'auto_update' in kwargs and kwargs['auto_update']:
            self.auto_update = self.data_type.utcnow  # datetime.datetime
        self.validator = self.generate_validator(self.data_type, **kwargs)
        self.required = kwargs['required'] if 'required' in kwargs else True
        if 'default' in kwargs:
            self.default_value = kwargs['default']
            if not callable(self.default_value):
                validation_failed = False
                try:
                    self.validator(self.default_value)
                except ValidationError as e:
                    new_err = ('default value "%s"' % kwargs['default']) + ''.join(e.args)
                    validation_failed = True
                if validation_failed:
                    raise TypeError(new_err)
                # check if dict/list type and wrap copy in callable
                if isinstance(self.default_value, (dict, list)):
                    def default_value_wrapper():
                        return copy.deepcopy(kwargs['default'])
                    self.default_value = default_value_wrapper

    @classmethod
    def check_kwargs(cls, kwargs, data_type):
        """Check keyword arguments & their values given to ``Field``
        constructor such as ``default``, ``required`` ...
        """
        err_str = data_type.__name__ + ': %s argument not allowed or "%s" value invalid'
        for k, v in kwargs.items():
            # kwargs allowed for all data_types
            if k in cls.allowed_kwargs:
                if not cls.allowed_kwargs[k](v):  # run kwarg validator
                    raise TypeError(err_str % (k, v))
            # type specific kwargs
            elif data_type in cls.extra_kwargs and k in cls.extra_kwargs[data_type]:
                if not cls.extra_kwargs[data_type][k](v):  # run kwarg validator
                    raise TypeError(err_str % (k, v))
            else:
                raise TypeError(err_str % (k, v))

    def generate_validator(self, t, **kwargs):
        """Generates and returns validator function ``(value_to_check, field_name='')``.
        ``field_name`` kwarg is optional, used for better error reporting.
        """
        def validator(val, field_name=''):
            if val is None and 'required' in kwargs and not kwargs['required']:
                return True
            elif val is None:
                raise ValidationError('%s: None is not allowed (field required)' % field_name)
            if not isinstance(val, t):
                raise ValidationError('%s: "%s" not an instance of %s but an instance of %s' %
                                      (field_name, val, t, type(val)))
            if isinstance(val, dict):
                check_keys(val)  # check against . & $ in keys
            return True
        return validator
