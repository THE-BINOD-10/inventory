import constants


class CommonBaseException(Exception):

    def __init__(self, message, error_code, title=None):
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return self.message

    def get_error(self):
        return {
            api_constants.API_ERROR_CODE: self.error_code,
            api_constants.API_ERROR_MESSAGE: self.message,
        }


class DataInconsistencyError(CommonBaseException):
    message = 'Data is inconsistent'
    error_code = 'dataInconsistency'

    def __init__(self, error_message=None):
        if error_message:
            self.message = error_message
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
