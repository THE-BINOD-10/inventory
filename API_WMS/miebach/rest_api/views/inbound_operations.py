from miebac_admin.models import *


def do_discrepencey(all_data, report_data, user):

    for key, value in all_data.items():
        if user.userprofile.industry_type == 'FMCG':
            discrepencey_price = key[3]*key[14]
            discrepencey_price_tax = (discrepencey_price+ key[14]*key[3]*tax/100)
            total_discrepency_amount += discrepencey_price_tax
            total_discrepency_qty += key[14]


