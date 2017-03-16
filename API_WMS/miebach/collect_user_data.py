import sys
from miebach_admin.user_data import CollectData

CollectData(company_name='easyops', api_object='EasyopsAPI', run_script=sys.argv[1]).run_main()
#CollectData(company_name='retailone', api_object='EasyopsAPI').run_main()
