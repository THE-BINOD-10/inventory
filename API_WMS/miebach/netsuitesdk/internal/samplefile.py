invitem = ns.InventoryItem()
invitem.taxSchedule = ns.RecordRef(internalId=1)
invitem.itemId = "SKU11"
invitem.externalId = "123"
ns.upsert(invitem)


purorder = ns.PurchaseOrder()
purorder.entity = ns.RecordRef(internalId=67, type="vendor")
purorder.tranDate = '2020-06-01T05:47:05+05:30'
purorder.approvalStatus = ns.RecordRef(internalId=2)
purorder.itemList = {'item': [{'item': ns.RecordRef(internalId=35), 'rate': '2025.00'}]}
purorder.externalId = "242"
ns.upsert(purorder)

purreq = ns.PurchaseRequisition()
purreq.entity = ns.RecordRef(internalId=6)
purreq.memo = "Webservice PR"
purreq.approvalStatus = ns.RecordRef(internalId=2)
purreq.itemList = {'purchaseRequisitionItem': [{'item': ns.RecordRef(internalId=35)}]}
purreq.externalId = "423"
ns.upsert(purreq)

grnrec = ns.ItemReceipt()
grnrec.createdFrom = ns.RecordRef(externalId=242)
grnrec.tranDate = '2020-06-01T05:47:05+05:30'
grnrec.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=122, internalId=65))
grnrec.itemList = {'item': [{'itemRecive': True, 'item': ns.RecordRef(internalId=35), 'orderLine': 1, 'quantity': 1, 'location': ns.RecordRef(internalId=100), 'customFieldList': ns.CustomFieldList(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value='2020-05-12T05:47:05+05:30')) }]}
grnrec.externalId = "350"
ns.upsert(grnrec)


npurorder = ns.NonInventoryPurchaseItem()
npurorder.itemId = "SKU11"
npurorder.purchaseOrderQuantity = 1
npurorder.purchaseOrderAmount = 200
npurorder.displayName = 'Testing Non Inventory PO'
npurorder.tranDate = '2020-06-01T05:47:05+05:30'
npurorder.approvalStatus = ns.RecordRef(internalId=2)
npurorder.externalId = "401"
npurorder.taxSchedule = ns.RecordRef(internalId=1)
ns.upsert(npurorder)


purorder = ns.PurchaseOrder()
purorder.entity = ns.RecordRef(internalId=67, type="vendor")
purorder.location = ns.RecordRef(internalId=100)
purorder.tranDate = '2020-06-01T05:47:05+05:30'
purorder.approvalStatus = ns.RecordRef(internalId=2)
purorder.itemList = {'item': [{'item': ns.RecordRef(externalId=401), 'rate': '201.00'}]}
purorder.externalId = "403"
ns.upsert(purorder)














