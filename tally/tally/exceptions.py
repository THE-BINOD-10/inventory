import json

import constants


class CommonBaseException(Exception):

    def __init__(self, message, error_code):
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return json.dumps(self.get_error())

    def get_error(self):
        return {
            constants.ERROR_CODE: self.error_code,
            constants.ERROR_MESSAGE: self.message,
        }


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
            message += ', '.join(fields)
        CommonBaseException.__init__(self, self.message, self.error_code)


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
