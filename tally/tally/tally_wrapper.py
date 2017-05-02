#!/usr/bin/env python

import clr
import sys
import datetime

import constants
import exceptions
import utils

sys.path.append(constants.DLL_BASE_PATH)


class TallyBridgeApp(object):

    def __init__(self, *args, **kwargs):
        self.dll_file = kwargs.get('dll', constants.DLL_FILE_NAME)
        clr.AddReference(self.dll_file)
        self.tally_bridge = TallyBridgeDll()
        import Tally
        import TallyBridge

    def add_sales_invoice(self, **kwargs):
        tally_company_name = kwargs.get('tally_company_name')
        voucher_foreign_key = kwargs.get('voucher_foreign_key')
        dt_of_voucher = kwargs.get('dt_of_voucher')
        voucher_typeName = kwargs.get('voucher_type_name')
        type_of_voucher = kwargs.get('type_of_voucher')
        voucher_no = kwargs.get('voucher_no')
        reference = kwargs.get('reference')
        despatch_doc_no = kwargs.get('despatch_doc_no')
        despatched_through = kwargs.get('despatched_through')
        destination = kwargs.get('destination')
        terms_of_payment = kwargs.get('terms_of_payment')
        use_separate_buyer_cons_addr = kwargs.get('use_separate_buyer_cons_addr')
        buyer_name = kwargs.get('buyer_name')
        address_line1 = kwargs.get('address_line1')
        address_line2 = kwargs.get('address_line2')
        address_line3 = kwargs.get('address_line3')
        buyer_state = kwargs.get('buyer_state')
        buyer_tin_no = kwargs.get('buyer_tin_no')
        buyer_cst_no = kwargs.get('buyer_cst_no')
        type_of_dealer = kwargs.get('type_of_dealer')
        narration = kwargs.get('narration')
        is_invoice = kwargs.get('is_invoice')
        is_optional = kwargs.get('is_optional')
        orders = kwargs.get('orders')
        items = kwargs.get('items')
        data_list = [
        ]
        if not all(data_list):
            raise exceptions.DataInconsistencyError
        invoice = Tally.SalesVoucher()
        invoice.tallyCompanyName = tally_company_name
        invoice.voucherForeignKey = voucher_foreign_key #This should be a unique id of the transaction in the external software
        invoice.dtOfVoucher = System.DateTime.ParseExact(dt_of_voucher, 'dd/MM/yyyy', None)
        invoice.voucherTypeName = voucher_typeName #'Sales' #This should be the name of the sales voucher type in Tally
        invoice.typeOfVoucher = type_of_voucher or 'Sales' #This should be hardcoded as Sales
        if voucher_no:
            invoice.voucherNo = voucher_no #You can leave it blank if voucher number is configured as automatic in Tally
        invoice.reference = reference #'ref111'
        invoice.voucherIdentifier = voucher_foreign_key #'SLS-003' #If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
        invoice.despatchDocNo = despatch_doc_no
        invoice.despatchedThrough = despatched_through
        invoice.destination = destination
        invoice.termsOfPayment = terms_of_payment
        invoice.useSeparateBuyerConsAddr = use_separate_buyer_cons_addr or False
        invoice.buyerName = buyer_name
        invoice.buyerAddress = [address_line1, address_line2, address_line3]
        invoice.buyerState = buyer_state
        invoice.buyerTINNo = buyer_tin_no
        invoice.buyerCSTNo = buyer_cst_no
        invoice.typeOfDealer = type_of_dealer
        invoice.narration = narration
        invoice.isInvoice = is_invoice or True
        invoice.isOptional = is_optional or False

        # order details
        orders = []
        for order in orders:
            v_order = Tally.Voucher.OrderDetails()
            v_order.orderNo = order['order_no']
            v_order.orderDate = System.DateTime.Parse(order['order_date'])
            orders.append(v_order)
        invoice.orderDetails = orders

        # item details
        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item['name'] #You can give either the main name of the item, or its alias, or its part number
            inv_entry.actualQty = System.Decimal(item['actual_qty'])
            inv_entry.billedQty = System.Decimal(item['billed_qty'])
            inv_entry.qtyUnit = item['unit'] or 'nos'
            inv_entry.rate = System.Decimal(item['rate'])
            inv_entry.rateUnit = item['rate_unit'] or 'nos'
            inv_entry.amount = System.Decimal(item['amount'])

            #Accounting Allocation for the item
            ledger_acc_alloc = Tally.LedgerEntry() 
            ledger_acc_alloc.ledgerName = ledger_name
            ledger_acc_alloc.ledgerAmount = inv_entry.amount
            inv_entry.arlAccountingAllocations.Add(ledger_acc_alloc)

            invoice.arlInvEntries.Add(inv_entry)

        # party Ledger
        for ledg in ledgers:
            ledger = Tally.LedgerEntry()
            ledger.ledgerName = ledg['name']
            #This should be the grand total of the invoice (including VAT and any other charges) with a negative sign
            #Debit ledgers should be posted with a negative amount and isDeemedPositive should be set to True
            leAddlLedger.ledEntryRate = System.Decimal(ledg['entry_rate'])
            ledger.ledgerAmount = System.Decimal(ledg['amount'], * int(ledg['amount_sign']))
            ledger.isDeemedPositive = not amount_sign
            invoice.arlLedgerEntries.Add(ledger)
        return self._transfer_and_get_resp(invoice, 'salse_voucher')

    def add_purchase_invoice(self, **kwargs):
        ''' Adds a purchase invoice to tally
        '''
        invoice = Tally.PurchaseVoucher()
        invoice.tallyCompanyName = "Miebach Demo Data"
        invoice.voucherForeignKey = voucher_foreign_key # This should be a unique id of the transaction in the external software
        invoice.dtOfVoucher = DateTime.ParseExact(dt_of_voucher, "dd/MM/yyyy", null)
        invoice.voucherTypeName = voucher_type_name # This should be the name of the Purchase voucher type in Tally
        invoice.typeOfVoucher = "Purchase" # This should be hardcoded as Purchase
        if voucherNo:
            invoice.voucherNo = voucherNo # You can leave it blank if voucher number is configured as automatic in Tally
        invoice.reference = reference # Supplier Invoice No
        invoice.referenceDate = DateTime.ParseExact(referenceDate, "dd/MM/yyyy", null) # Supplier Invoice Date
        invoice.voucherIdentifier = voucher_dentifier # If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
        invoice.supplierName = supplier_name
        invoice.supplierAddress = []
        invoice.supplierState = supplier_state
        invoice.supplierTINNo = supplier_TINNo
        invoice.supplierCSTNo = supplier_CSTNo
        invoice.typeOfDealer = type_of_dealer
        invoice.consigneeName = consignee_name # In case of purchase, consignee is our company
        invoice.consigneeAddress = [add_linr_1, add_linr_2, add_linr_3]
        invoice.consigneeTINNo = consignee_TINNo
        invoice.consigneeCSTNo = consignee_CSTNo
        invoice.narration = narration
        invoice.isInvoice = True
        invoice.isOptional = False


        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item_name # You can give either the main name of the item, or its alias, or its part number
            inv_entry.isDeemedPositive = True # For purchases, items should have isDeemedPositive set to true
            inv_entry.actualQty = 500
            inv_entry.billedQty = 500
            inv_entry.qtyUnit = "nos"
            inv_entry.rate = 15
            inv_entry.rateUnit = "nos"
            inv_entry.discountPerc = 5
            inv_entry.amount = (decimal) -7125 # For purchase items, amount should be negative

            leAccAlloc = TallyLedgerEntry() # Accounting Allocation for the 1st item
            leAccAlloc.ledgerName = "Vat Purchases 5.5%"
            leAccAlloc.ledgerAmount = inv_entry.amount

            invEntry.arlAccountingAllocations.Add(leAccAlloc)
            invoice.arlInvEntries.Add(invEntry)


        # All additional ledgers in Purchase (Invoice Mode) should have isDeemedPositive set to true
        # However, if the actual amount like Input VAT is positive, the value in ledgerAmount should be negative
        # and if the actual amount like Round Off is negative, the value in ledgerAmount should be positive
        # This applies to Purchase (Invoice Mode).
        # The behaviour for Purchase (Voucher Mode) is different
        # for ledg in ledgers:
        #     ledger_entry = Tally.LedgerEntry()
        #     ledger_entry.ledgerName = "Knowledge Invention"

        #     # This should be the grand total of the invoice (including VAT and any other charges) with a positive sign
        #     # isDeemedPositive should be set to false
        #     ledger_entry.ledgerAmount = (decimal)9415
        #     ledger_entry.isDeemedPositive = false

        #     # Party ledger should be the 1st ledger in the invoice
        #     invoice.arlLedgerEntries.Add(ledger_entry)


        # leAddlLedger = new LedgerEntry()
        # leAddlLedger.ledgerName = "Input VAT 5.5%"
        # leAddlLedger.ledEntryRate = (decimal)5.5
        # leAddlLedger.ledgerAmount = (decimal)490.88 * -1
        # leAddlLedger.isDeemedPositive = true
        # invoice.arlLedgerEntries.Add(leAddlLedger)

        # leAddlLedger = new LedgerEntry()
        # leAddlLedger.ledgerName = "Round Off"
        # leAddlLedger.ledgerAmount = (decimal)0.88
        # leAddlLedger.isDeemedPositive = true
        # invoice.arlLedgerEntries.Add(leAddlLedger)


        return self._transfer_and_get_resp(invoice, 'purchase_invoice')

    def add_ledger(self, **kwargs):
        ''' Adds a new customer or a vendor to tally
        '''
        tallyCompanyName = kwargs.get('tally_company_name')
        oldLedgerName = kwargs.get('old_ledger_name')
        ledgerName = kwargs.get('ledger_name')
        openingBalance = kwargs.get('opening_balance')
        parentGroupName = kwargs.get('parent_group_name')
        updateOpeningBalance = kwargs.get('update_opening_balance')
        ledgerMailingName = kwargs.get('ledger_mailing_name')
        data_list = [
            tallyCompanyName,
            oldLedgerName,
            ledgerName,
            openingBalance,
            parentGroupName,
            updateOpeningBalance,
            ledgerMailingName,
        ]
        if not all(data_list):
            raise exceptions.DataInconsistencyError
        ledger = Tally.Ledger()
        ledger.tallyCompanyName = tallyCompanyName
        ledger.oldLedgerName = oldLedgerName
        ledger.ledgerName = ledgerName
        ledger.updateOpeningBalance = True
        ledger.openingBalance =  System.Decimal(openingBalance)
        ledger.ledgerMailingName = ledgerMailingName
        ledger.parentGroupName = parentGroupName
        return self._transfer_and_get_resp(ledger, 'ledger_master')


    ##-- ITEM MASTER --##
    @utils.required(params=[
        'tally_company_name',
        'item_name',
        'sku_code',
        'unit_name',
        'stock_group_name',
        'stock_category_name',
        'opening_qty',
        'opening_rate',
        'opening_amt'
    ])
    def item_master(self, **kwargs):
        ''' Adds items to item master in tally
        required: [
            tally_company_name,
            item_name,
            sku_code,
            unit_name or 'nos',
            stock_group_name,
            stock_category_name,
            opening_qty,
            opening_rate,
            opening_amt
        ]
        optional: [
            old_item_name,
            part_no,
            description
        ]
        default values if not pased: [
            is_vat_app = True
        ]
        '''
        tally_company_name = kwargs.get('tally_company_name')
        old_item_name = kwargs.get('old_item_name')
        item_name = kwargs.get('item_name')
        part_no = kwargs.get('part_no')
        sku_code = kwargs.get('sku_code')
        description = kwargs.get('description')
        is_vat_app = kwargs.get('is_vat_app')
        unit_name = kwargs.get('unit_name')
        stock_group_name = kwargs.get('stock_group_name')
        stock_category_name = kwargs.get('stock_category_name')

        stock_item = Tally.StockItem()
        
        # required
        stock_item.tallyCompanyName = tally_company_name
        stock_item.itemName = item_name
        stock_item.itemAlias = sku_code
        stock_item.primaryUnitName = unit_name or 'nos'
        stock_item.stockGroupName = stock_group_name
        stock_item.stockCategoryName = stock_category_name
        stock_item.openingQty = System.Decimal(opening_qty)
        stock_item.openingRate = System.Decimal(opening_rate)
        stock_item.openingAmt = System.Decimal(-1 * opening_amt)        # Opening stock amount should be negative

        # defaults if not passed
        stock_item.isVatAppl = is_vat_app or True
        
        # optional
        if old_item_name:
            stock_item.oldItemName = old_item_name
        if part_no:
            stockItem.partNo = part_no
        if description:
            stock_item.description = description
        return self._transfer_and_get_resp(stock_item, 'item_master')

    def add_purchase_returns(self, **kwargs):
            pass    

    def add_sales_returns(self, **kwargs):
            pass    

    # private
    def _transfer_and_get_resp(self, obj, type):
        ''' transfer the objects to tally using dll 
        and responds accordingly
        '''
        resp = Tally.TallyResponse()
        resp = self.tally_bridge.DoTransferStockItem(obj)
        if resp.errorMsg:
            raise exceptions.TallyDataTransferError(error_message=resp.errorMsg)
        return {'success': True, 'type': type, 'resp': resp}
