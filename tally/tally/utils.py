
import exceptions

class required(object):
    def __init__(self, params):
        self._params = params

    def __call__(self, func):
        def inner(resource, *args, **kwargs):
            missing_params = [fld for fld in self._params if fld not in kwargs.keys()]
            if missing_params:
                raise exceptions.RequiredFieldsMissingError(fields=missing_params)
            return func(*args, **kwargs)
        return inner