from __future__ import absolute_import, unicode_literals
from django.contrib.auth.models import User

from miebach.celery import app
from stockone_integrations.views import Integrations
import datetime
from stockone_integrations.utils import init_logger

ListOfExecution = [
    { 'function': 'integrateSkuMaster', 'objType': 'InventoryItem', 'unique_param': 'sku_code'},
    { 'function': 'integrateServiceMaster', 'objType': 'ServicePurchaseItem', 'unique_param': 'sku_code'},
    { 'function': 'integrateAssetMaster', 'objType': 'NonInventoryPurchaseItem', 'unique_param': 'sku_code'},
    { 'function': 'IntegratePurchaseRequizition', 'objType': 'PurchaseRequizition', 'unique_param': 'full_pr_number'},
    { 'function': 'IntegratePurchaseOrder', 'objType': 'PurchaseOrder', 'unique_param': 'po_number'},
    { 'function': 'IntegrateGRN', 'objType': 'grn', 'unique_param': 'grn_number'},
    { 'function': 'IntegrateRTV', 'objType': 'rtv', 'unique_param': 'rtv_number'}
]

today = datetime.datetime.now().strftime("%Y%m%d")
log = init_logger('logs/automated_tasks_' + today + '.log')
log_err = init_logger('logs/automated_tasks_errors.log')

@app.task
def runStoredAutomatedTasks():
    for userObj in User.objects.filter():
        executeAutomatedTaskForUser(userObj)    

def executeAutomatedTaskForUser(userObj):
    intObj = Integrations(userObj, intType='netsuiteIntegration', executebatch=True)
    if not intObj.is_connected:
        log.info('Connection With Integration Layer Failed')
    for row in ListOfExecution:
        try:
            currentData = intObj.getRelatedJson(row.get('objType'))

            log.info('Executing %s' % (row.get('objType')))
            if len(currentData):
                log.info('Executing %s' % (row.get('objType')))
                getattr(intObj, row.get('function'))(currentData, row.get('unique_param'), is_multiple=True)
                log.info('Executed %s' % (row.get('objType')))
                # intObj.writeJsonToFile(row.get('objType'), [])
            else:
                log.info('Empty For Queue %s' % (row.get('objType')))
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Faied Executing %s' % row.get('objType'))
