
import common_exceptions

class required(object):
    def __init__(self, params):
        self._params = params

    def __call__(self, func):
        def inner(**kwargs):
            if not self._params:
                return func(**kwargs)
            missing_params = []
            for fld in self._params:
                if not fld:
                    continue
                if fld not in kwargs.keys():
                    missing_params.append(fld)
            if missing_params:
                raise common_exceptions.RequiredFieldsMissingError(fields=missing_params)
            return func(**kwargs)
        return inner
