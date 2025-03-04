"""
Declares all NetSuite types which are available through attribute lookup `ns.<type>`
of a :class:`~netsuitesdk.client.NetSuiteClient` instance `ns`.
"""

COMPLEX_TYPES = {
    'ns0': [
        'BaseRef',
        'GetAllRecord',
        'GetAllResult',
        'Passport',
        'RecordList',
        'ListOrRecordRef',
        'RecordRef',
        'SearchResult',
        'SearchStringField',
        'SearchMultiSelectField',
        'Status',
        'StatusDetail',
        'TokenPassport',
        'TokenPassportSignature',
        'WsRole',
        'DateCustomFieldRef',
        'StringCustomFieldRef',
        'CustomFieldList',
        'SelectCustomFieldRef',
        'DoubleCustomFieldRef'
    ],

    # ns4: https://webservices.netsuite.com/xsd/platform/v2017_2_0/messages.xsd
    'ns4': [
        'ApplicationInfo',
        'GetAllRequest',
        'GetRequest',
        'GetResponse',
        'GetAllResponse',
        'PartnerInfo',
        'ReadResponse',
        'SearchPreferences',
        'SearchResponse'
    ],

    # https://webservices.netsuite.com/xsd/platform/v2017_2_0/common.xsd
    'ns5': [
        'AccountSearchBasic',
        'CustomerSearchBasic',
        'LocationSearchBasic',
        'TransactionSearchBasic',
        'VendorSearchBasic',
        'ItemSearchBasic'
    ],

    # urn:relationships.lists.webservices.netsuite.com
    'ns13': [
        'Customer', 'CustomerSearch',
        'Vendor', 'VendorSearch',
    ],

    # urn:accounting_2017_2.lists.webservices.netsuite.com
    # https://webservices.netsuite.com/xsd/lists/v2017_2_0/accounting.xsd
    'ns17': [
        'Account', 'AccountSearch',
        'AccountingPeriod',
        'Classification', 'ClassificationSearch',
        'Department', 'DepartmentSearch',
        'Location', 'LocationSearch',
        'VendorCategory', 'VendorCategorySearch', 
        'ItemSearch',
        'InventoryItem',
        'UnitsType',
        'UnitsTypeUom',
        'NonInventoryPurchaseItem',
        'NonInventorySaleItem',
        'NonInventoryResaleItem',
        'ServicePurchaseItem',
        'ServiceSaleItem',
        'ServiceResaleItem',
    ],

    'ns19': [
        'TransactionSearch'
    ],
    'ns29': [
        'InventoryAdjustment',
        'InventoryTransfer'
    ],
    # urn:purchases_2017_2.transactions.webservices.netsuite.com
    # https://webservices.netsuite.com/xsd/transactions/v2017_2_0/purchases.xsd
    'ns21': [
        'VendorBill',
        'VendorBillExpense',
        'VendorBillExpenseList',
        'VendorBillItem',
        'VendorBillItemList',
        'VendorPayment',
        'PurchaseOrder',
        'PurchaseRequisition',
        'ItemReceipt',
        'VendorReturnAuthorization',
    ],

}

SIMPLE_TYPES = {
    # ns1: view-source:https://webservices.netsuite.com/xsd/platform/v2017_2_0/coreTypes.xsd
    'ns1': [
        'RecordType',
        'GetAllRecordType',
        'SearchRecordType',
        'SearchStringFieldOperator',
    ],
}
