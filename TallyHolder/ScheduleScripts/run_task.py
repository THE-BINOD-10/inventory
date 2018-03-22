from os import path
import sys
sys.path.append(path.abspath('../PullFromStockone'))
sys.path.append(path.abspath('../PushToCustomer'))
from api_consumer import *
from push import *
log = init_logger('logs/schedule_script.log')
pull_mapping = {'populate_api_item_data': 'push_item_master', 'populate_api_customer_data': 'push_customer_vendor_master',
 				'populate_api_sales_invoice_data': 'push_sales_invoice_data'}
sys_args = sys.argv
#push_to_tally
if sys_args:
	resp_status = eval(sys.argv[2])(sys.argv[1])
	if resp_status:
		eval(pull_mapping[sys.argv[2]])()
#log.info(sys.argv)
