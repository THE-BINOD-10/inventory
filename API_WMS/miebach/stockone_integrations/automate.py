from __future__ import absolute_import, unicode_literals
from django.contrib.auth.models import User

from miebach.celery import app
from stockone_integrations.views import Integrations
import datetime
from stockone_integrations.utils import init_logger

ListOfExecution = [
    { 'function': 'IntegrateUOM', 'objType': 'uom', 'unique_param': 'name'},
    { 'function': 'integrateSkuMaster', 'objType': 'InventoryItem', 'unique_param': 'sku_code'},
    { 'function': 'IntegrateInventoryAdjustment', 'objType': 'InventoryAdjustment', 'unique_param': 'ia_number'},
    { 'function': 'IntegrateInventoryTransfer', 'objType': 'InventoryTransfer', 'unique_param': 'it_number'},
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
batch = 50

@app.task
def runStoredAutomatedTasks():
    users = User.objects.filter()
    for row in ListOfExecution:
        for userObj in users:
            executeAutomatedTaskForUser(userObj, row)

@app.task
def executeAutomatedTaskForUser(userObj, row):
    intObj = Integrations(userObj, intType='netsuiteIntegration', executebatch=True)
    if not intObj.is_connected:
        log.info('Connection With Integration Layer Failed')
    try:
        for action in ['add', 'delete', 'upsert']:
            currentData = intObj.getRelatedJson(row.get('objType'), action=action)
            print(row.get('objType'), userObj, currentData, action)
            log.info('Executing %s' % (row.get('objType')))
            if len(currentData):
                log.info('Executing %s' % (row.get('objType')))
                dataToSend = []
                for drow in currentData:
                    dataToSend.append(drow)
                    if len(dataToSend) >= batch:
                        getattr(intObj, row.get('function'))(dataToSend, row.get('unique_param'), is_multiple=True, action=action)
                        dataToSend = []
                if len(dataToSend):
                    getattr(intObj, row.get('function'))(dataToSend, row.get('unique_param'), is_multiple=True, action=action)

                log.info('Executed %s' % (row.get('objType')))
                # intObj.writeJsonToFile(row.get('objType'), [])
            else:
                log.info('Empty For Queue %s' % (row.get('objType')))
    except Exception as e:
        import traceback
        log_err.debug(traceback.format_exc())
        log_err.info('Faied Executing %s' % row.get('objType'))
def getFunctionName(moduleType):
    for row in ListOfExecution:
        if row['objType'] == moduleType:
            return row

def executeTaskForRow(userObj, moduleType, integration_type, rows):
    row = getFunctionName(moduleType)
    intObj = Integrations(userObj, intType=integration_type, executebatch=True)
    getattr(intObj, row.get('function'))(dataToSend, row.get('unique_param'), is_multiple=True)
