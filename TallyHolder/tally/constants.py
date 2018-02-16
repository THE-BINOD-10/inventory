from os.path import abspath
from os.path import dirname
from os.path import join


ROOT_PATH = abspath(join(dirname(__file__), '..'))


DLL_BASE_PATH = join(ROOT_PATH, 'DLL')
DLL_FILE_NAME = ''

# Exception Keys
ERROR_CODE = 'error_code'
ERROR_MESSAGE = 'message'

# TALLY interaction point types
SALES_INVOICE = 'sales_invoice'
PURCHASE_INVOICE = 'purchase_invioce'
VENDOR_OR_CUSTOMER = 'vendor_or_customer'
ITEM_MASTER = 'item_master'
DEBIT_NOTE_INVOICE = 'debit_note_invioce'
CREDIT_NOTE_INVOICE = 'credit_note_invioce'
