import json

import constants


class CommonBaseException(Exception):

    def __init__(self, message, error_code, extra={}):
        self.message = message
        self.error_code = error_code
        self.extra = extra

    def __str__(self):
        return json.dumps(self.get_error())

    def get_error(self):
        error = {
            constants.ERROR_CODE: self.error_code,
            constants.ERROR_MESSAGE: self.message,
        }
        if self.extra:
            error.update(self.extra)
        return error


class DataInconsistencyError(CommonBaseException):
    message = 'Data is inconsistent'
    error_code = 'dataInconsistency'

    def __init__(self, error_message=None):
        if error_message:
            self.message = error_message
        CommonBaseException.__init__(self, self.message, self.error_code)


class RequiredFieldsMissingError(CommonBaseException):
    message = 'required fields are not present'
    error_code = 'requiredFieldsMissing'

    def __init__(self, fields=[]):
        if fields:
            extra = {'fields': fields}
        CommonBaseException.__init__(self, self.message, self.error_code, extra=extra)


class TallyDataTransferError(CommonBaseException):
    message = 'could not transmitt data! '
    error_code = 'tallyDataTransfer'

    def __init__(self, error_message=None):
        if error_message:
            self.message += error_message
        CommonBaseException.__init__(self, self.message, self.error_code)


class CompanyNameNotPresentError(CommonBaseException):
    message = 'Company name is mandatory'
    error_code = 'companyNameNotPresent'

    def __init__(self):
        CommonBaseException.__init__(self, self.message, self.error_code)


class DllFileNotPresentError(CommonBaseException):
    message = 'Please pass a valid dll file name'
    error_code = 'dllFileNotPresent'

    def __init__(self):
        CommonBaseException.__init__(self, self.message, self.error_code)
