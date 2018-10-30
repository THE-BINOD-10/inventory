#!/usr/bin/env python

import clr
import sys
import datetime

import constants
import common_exceptions
import utils

null = None


class TallyBridgeApp(object):

    def __init__(self, **kwargs):
        self.dll_file = kwargs.get('dll', constants.DLL_FILE_NAME)

        sys.path.append(self.dll_file)
        clr.AddReference(self.dll_file)
        clr.AddReference('System')

        global System
        global TallyBridge
        global Tally

        import System
        import Tally
        import TallyBridge

        self.tally_bridge = TallyBridge.TallyBridgeDll()
        self.TRANSFER_FUNCTION_MAP = {
            constants.SALES_INVOICE: self.tally_bridge.DoTransferVoucher,
            constants.PURCHASE_INVOICE: self.tally_bridge.DoTransferVoucher,
            constants.VENDOR_OR_CUSTOMER: self.tally_bridge.DoTransferLedger,
            constants.ITEM_MASTER: self.tally_bridge.DoTransferStockItem,
            constants.DEBIT_NOTE_INVOICE: self.tally_bridge.DoTransferVoucher,
            constants.CREDIT_NOTE_INVOICE: self.tally_bridge.DoTransferVoucher,
        }

    ##--- Sales Invoice Master ---##
    @utils.required(params=[
        'tally_company_name',
        'voucher_foreign_key',
        'dt_of_voucher',
        'voucher_type_name',
        'voucher_foreign_key',
        'buyer_state',
        'orders',
        'items',
        'party_ledger'
    ])
    def sales_invoice(self, **kwargs):
        ''' Add/Edits sales invoice
        required: [
            tally_company_name,
            voucher_foreign_key,
            dt_of_voucher,
            voucher_type_name,
            voucher_foreign_key,
            buyer_state,
            orders,
            items,
            party_ledger
        ]
        optional: [
            party_ledger_tax,
            voucher_no,
            reference,
            despatch_doc_no,
            despatched_through,
            destination,
            bill_of_lading_no,
            bill_of_lading_dt,
            carrier_name,
            terms_of_payment,
            other_reference,
            terms_of_delivery_1,
            buyer_name,
            address_line1,
            buyer_tin_no,
            buyer_cst_no,
            type_of_dealer,
            narration,
            del_notes,
        ]
        defaults if not passed: [
            use_separate_buyer_cons_addr or False
            is_invoice or True
            is_optional or False
            type_of_voucher or 'Sales'
        ]
        '''
        tally_company_name = kwargs.get('tally_company_name')
        voucher_foreign_key = kwargs.get('voucher_foreign_key')
        dt_of_voucher = kwargs.get('dt_of_voucher')
        voucher_typeName = kwargs.get('voucher_type_name')
        type_of_voucher = kwargs.get('type_of_voucher', 'Sales')

        # TODO: ask rajesh
        voucher_no = kwargs.get('voucher_no')

        reference = kwargs.get('reference')
        voucher_identifier = kwargs.get('voucher_dentifier')
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
        bill_of_lading_no = kwargs.get('bill_of_lading_no')
        bill_of_lading_dt = kwargs.get('bill_of_lading_dt')
        carrier_name = kwargs.get('carrier_name')
        other_reference = kwargs.get('other_reference')
        terms_of_delivery_1 = kwargs.get('terms_of_delivery_1')
        terms_of_delivery_2 = kwargs.get('terms_of_delivery_2')
        del_notes = kwargs.get('del_notes')
        party_ledger = kwargs.get('party_ledger')
        party_ledger_tax = kwargs.get('party_ledger_tax', [])
        ledger_name = kwargs.get('ledger_name')

        invoice = Tally.SalesVoucher()
        # required
        invoice.tallyCompanyName = tally_company_name
        invoice.voucherForeignKey = voucher_foreign_key

        invoice.dtOfVoucher = System.DateTime.ParseExact(dt_of_voucher, 'dd/MM/yyyy', None)
        #invoice.dtOfVoucher = System.DateTime.ParseExact("01/03/2018", 'dd/MM/yyyy', None)
        
        invoice.voucherTypeName = voucher_typeName

        # modified
        # invoice.voucherIdentifier = voucher_foreign_key
        invoice.voucherIdentifier = voucher_identifier

        invoice.buyerState = buyer_state
        # order details
        updated_orders = []
        for order in orders:
            v_order = Tally.Voucher.OrderDetails()
            v_order.orderNo = order['order_no']
            v_order.orderDate = System.DateTime.ParseExact(order['order_date'], 'dd/MM/yyyy', None)
            updated_orders.append(v_order)
        invoice.orderDetails = updated_orders
        # item details
        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item['name']
            inv_entry.actualQty = System.Decimal(item['actual_qty'])
            inv_entry.billedQty = System.Decimal(item['billed_qty'])
            inv_entry.qtyUnit = item['unit'] or 'nos'
            inv_entry.rate = System.Decimal(item['rate'])
            inv_entry.rateUnit = item['rate_unit'] or 'nos'
            inv_entry.amount = System.Decimal(item['amount'])
            print(inv_entry.actualQty, inv_entry.billedQty, inv_entry.qtyUnit, inv_entry.rate, inv_entry.rateUnit,
                  inv_entry.amount)
            # Accounting Allocation for the item
            ledger_acc_alloc = Tally.LedgerEntry()
            ledger_acc_alloc.ledgerName = item['ledger_name'] or 'GST Sales'
            ledger_acc_alloc.ledgerAmount = inv_entry.amount
            inv_entry.arlAccountingAllocations.Add(ledger_acc_alloc)
            # print(inv_entry)
            # print(ledger_acc_alloc)
            invoice.arlInvEntries.Add(inv_entry)
        # party Ledger
        party_ledger_entry = Tally.LedgerEntry()
        party_ledger_entry.ledgerName = party_ledger.get('name')
        party_ledger_entry.ledgerAmount = System.Decimal(party_ledger.get('amount') * -1)  # always negetive
        party_ledger_entry.isDeemedPositive = party_ledger.get('is_deemed_positive') or True  # always True
        invoice.arlLedgerEntries.Add(party_ledger_entry)
        # party ledger tax entry
        for tax_obj in party_ledger_tax:
            party_tax_ledger = Tally.LedgerEntry()
            party_tax_ledger.ledgerName = tax_obj.get('name', 'sam')
            party_tax_ledger.ledgerAmount = System.Decimal(tax_obj.get('amount'))  # always positive
            if 'entry_rate' in tax_obj.keys():
                party_tax_ledger.ledEntryRate = System.Decimal(tax_obj.get('entry_rate'))
            if 'is_deemed_positive' in tax_obj.keys():
                party_tax_ledger.isDeemedPositive = tax_obj.get('is_deemed_positive') or True  # always True

            invoice.arlLedgerEntries.Add(party_tax_ledger)

            # import pdb;pdb.set_trace()
            # Testing Ledger
            # party_tax_ledger = Tally.LedgerEntry()
            # party_tax_ledger.ledgerName = 'Bill of Supply'
            # party_tax_ledger.ledgerAmount = System.Decimal(0)  # always positive
            # if 'entry_rate' in tax_obj.keys():
            #     party_tax_ledger.ledEntryRate = System.Decimal(0)
            # if 'is_deemed_positive' in tax_obj.keys():
            #     party_tax_ledger.isDeemedPositive = tax_obj.get('is_deemed_positive') or True  # always True
            # invoice.arlLedgerEntries.Add(party_tax_ledger)

        if voucher_no:
            invoice.voucherNo = voucher_no
        if reference:
            invoice.reference = str(reference)
        if despatch_doc_no:
            invoice.despatchDocNo = despatch_doc_no
        if despatched_through:
            invoice.despatchedThrough = despatched_through
        if destination:
            invoice.destination = destination
        if bill_of_lading_no:
            invoice.billOfLadingNo = bill_of_lading_no
        if bill_of_lading_dt:
            invoice.billOfLadingDt = System.DateTime.ParseExact(bill_of_lading_dt, 'dd/MM/yyyy', None)
        if carrier_name:
            invoice.carrierName = carrier_name
        if terms_of_payment:
            invoice.termsOfPayment = terms_of_payment
        if other_reference:
            invoice.otherReference = other_reference
        if terms_of_delivery_1:
            invoice.termsOfDelivery = [terms_of_delivery_1, terms_of_delivery_2]
        if buyer_name:
            invoice.buyerName = buyer_name
        if address_line1:
            invoice.buyerAddress = [address_line1, address_line2, address_line3]
        if buyer_tin_no:
            invoice.buyerGstin = buyer_tin_no
        if buyer_cst_no:
            invoice.buyerCSTNo = buyer_cst_no
        if type_of_dealer:
            invoice.typeOfDealer = type_of_dealer
        if narration:
            invoice.narration = narration
        '''
        Missing
        invoice.buyerGstRegType = "Regular";
        invoice.placeOfSupply = "Karnataka";
        '''
        # Delivery Notes
        if del_notes:
            notes = []
            for del_note in del_notes:
                note = Tally.Voucher.DeliveryNoteDetails()
                note.deliveryNoteNo = del_note['delivery_note_no']
                note.deliveryNoteDate = System.DateTime.ParseExact(del_note['delivery_note_Date'], 'dd/MM/yyyy', None)
                notes.append(note)
            invoice.deliveryNotes = notes

        # defaults if not passed
        invoice.useSeparateBuyerConsAddr = use_separate_buyer_cons_addr or False
        invoice.isInvoice = is_invoice or True
        invoice.isOptional = is_optional or False
        invoice.typeOfVoucher = type_of_voucher or 'Sales'
        return self._transfer_and_get_resp(invoice, constants.SALES_INVOICE)

    @utils.required(params=[
        'tally_company_name',
        'voucher_foreign_key',
        'dt_of_voucher',
        'voucher_foreign_key',
        'supplier_name',
        'supplier_state',
        'items',
        'party_ledger'
    ])
    def purchase_invoice(self, **kwargs):
        ''' Add/Edits purchase invoice
        required: [
            tally_company_name,
            voucher_foreign_key,
            dt_of_voucher,
            supplier_name,
            supplier_state,
            items,
            party_ledger
        ]
        optional: [
            party_ledger_tax,
            voucher_no,
            reference,
            despatch_doc_no,
            despatched_through,
            destination,
            bill_of_lading_no,
            bill_of_lading_dt,
            carrier_name,
            terms_of_payment,
            other_reference,
            terms_of_delivery_1,
            buyer_name,
            address_line1,
            buyer_tin_no,
            buyer_cst_no,
            type_of_dealer,
            narration,
            del_notes,
        ]
        defaults if not passed: [
            use_separate_buyer_cons_addr or False
            is_invoice or True
            is_optional or False
            type_of_voucher or 'Sales'
        ]
        '''
        tally_company_name = kwargs.get('tally_company_name')
        voucher_foreign_key = kwargs.get('voucher_foreign_key')
        dt_of_voucher = kwargs.get('dt_of_voucher')
        supplier_name = kwargs.get('supplier_name')
        voucher_foreign_key = kwargs.get('voucher_foreign_key')
        buyer_state = kwargs.get('buyer_state')
        orders = kwargs.get('orders')
        items = kwargs.get('items')
        party_ledger = kwargs.get('party_ledger')
        party_ledger_tax = kwargs.get('party_ledger_tax')
        voucher_no = kwargs.get('voucher_no')
        reference = kwargs.get('reference')
        reference_date = kwargs.get('reference_date')
        voucher_identifier = kwargs.get('voucher_identifier')
        supplier_address_1 = kwargs.get('supplier_address_1')
        supplier_TIN_no = kwargs.get('supplier_TIN_no')
        supplier_CST_no = kwargs.get('supplier_CST_no')
        narration = kwargs.get('narration')
        voucher_type_name = kwargs.get('voucher_type_name')
        type_of_voucher = kwargs.get('type_of_voucher')
        is_invoice = kwargs.get('is_invoice')
        is_optional = kwargs.get('is_optional')
        supplier_state = kwargs.get('supplier_state')
        type_of_dealer = kwargs.get('type_of_dealer')
        consignee_name = kwargs.get('consignee_name')
        consignee_address_1 = kwargs.get('consignee_address_1')
        consignee_TIN_no = kwargs.get('consignee_TIN_no')
        consignee_CST_no = kwargs.get('consignee_CST_no')
        invoice = Tally.PurchaseVoucher()

        # required
        invoice.tallyCompanyName = tally_company_name
        invoice.voucherForeignKey = voucher_foreign_key
        invoice.dtOfVoucher = System.DateTime.ParseExact(dt_of_voucher, "dd/MM/yyyy", null)
        invoice.supplierName = supplier_name
        invoice.supplierState = supplier_state
        # item details
        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item['name']
            inv_entry.isDeemedPositive = bool(item['is_deemeed_positive']) or True
            inv_entry.actualQty = System.Decimal(item['actual_qty'])
            inv_entry.billedQty = System.Decimal(item['billed_qty'])
            inv_entry.qtyUnit = item['unit'] or 'nos'
            inv_entry.rate = System.Decimal(item['rate'])
            inv_entry.rateUnit = item['rate_unit'] or 'nos'
            inv_entry.amount = System.Decimal(item['amount']) * -1  # always negetive
            inv_entry.discountPerc = System.Decimal(item.get('discount_percent', 0))
            # Accounting Allocation for the item
            ledger_acc_alloc = Tally.LedgerEntry()
            ledger_acc_alloc.ledgerName = item['ledger_name']
            ledger_acc_alloc.ledgerAmount = inv_entry.amount
            inv_entry.arlAccountingAllocations.Add(ledger_acc_alloc)
            invoice.arlInvEntries.Add(inv_entry)
        # party Ledger
        party_ledger_entry = Tally.LedgerEntry()
        party_ledger_entry.ledgerName = party_ledger.get('name')
        party_ledger_entry.ledgerAmount = System.Decimal(party_ledger.get('amount'))  # always positive
        party_ledger_entry.isDeemedPositive = party_ledger.get('is_deemed_positive') or False  # always False
        invoice.arlLedgerEntries.Add(party_ledger_entry)

        # optional
        # party ledger tax entry (optional)
        if party_ledger_tax and party_ledger_tax.get('entry_rate', 0):
            party_tax_ledger = Tally.LedgerEntry()
            party_tax_ledger.ledgerName = party_ledger_tax.get('name')
            party_tax_ledger.ledgerAmount = System.Decimal(party_ledger_tax.get('amount') * -1)  # always negetive
            if 'entry_rate' in party_ledger_tax.keys():
                party_tax_ledger.ledEntryRate = System.Decimal(party_ledger_tax.get('entry_rate'))
            if 'is_deemed_positive' in party_ledger_tax.keys():
                party_tax_ledger.isDeemedPositive = party_ledger_tax.get('is_deemed_positive') or True  # always True
            invoice.arlLedgerEntries.Add(party_tax_ledger)
        # TODO: ROUND OFF
        if voucher_no:
            invoice.voucherNo = voucher_no
        if reference:
            invoice.reference = reference
        if reference_date:
            invoice.referenceDate = System.DateTime.ParseExact(reference_date, "dd/MM/yyyy", null)
        if voucher_identifier:
            invoice.voucherIdentifier = voucher_identifier
        if supplier_address_1:
            invoice.supplierAddress = [supplier_address_1, supplier_address_2, supplier_address_3]
        if supplier_TIN_no:
            invoice.supplierTINNo = supplier_TIN_no
        if supplier_CST_no:
            invoice.supplierCSTNo = supplier_CST_no
        if type_of_dealer:
            invoice.typeOfDealer = type_of_dealer
        if consignee_name:
            invoice.consigneeName = consignee_name
        if consignee_address_1:
            invoice.consigneeAddress = [consignee_address_1, consignee_address_2, consignee_address_3]
        if consignee_TIN_no:
            invoice.consigneeTINNo = consignee_TIN_no
        if consignee_CST_no:
            invoice.consigneeCSTNo = consignee_CST_no
        if narration:
            invoice.narration = narration

        # defaults if not passed
        invoice.voucherTypeName = voucher_type_name or 'Purchase'
        invoice.typeOfVoucher = type_of_voucher or 'Purchase'
        invoice.isInvoice = is_invoice or True
        invoice.isOptional = is_optional or False
        return self._transfer_and_get_resp(invoice, constants.PURCHASE_INVOICE)

    ##--- Customer and Vendor Master ---##
    @utils.required(params=[
        'tally_company_name',
        'ledger_name',
        'ledger_alias',
        'parent_group_name',
        'state'
    ])
    def customer_and_vendor_master(self, **kwargs):
        ''' Adds a new customer or a vendor to tally
        required: [
            tally_company_name,
            ledger_name,
            ledger_alias,
            parent_group_name,
            state
        ]
        optional: [
            opening_balance,
            update_opening_balance,
            country,
            contact_person,
            telephone_no,
            fax_no,
            email,
            tin_no,
            cst_no,
            pan_no,
            service_tax_no,
            pin_code,
            address,
            old_ledger_name,
            ledger_mailing_name
        ]
        default values if not pased: [
            maintain_billWise_details = True
            update_opening_balance = True,
        ]
        '''
        tallyCompanyName = kwargs.get('tally_company_name')
        oldLedgerName = kwargs.get('ledger_name')  # kwargs.get('old_ledger_name')
        ledgerName = kwargs.get('ledger_name')
        openingBalance = kwargs.get('opening_balance')
        ledgerAlias = kwargs.get('ledger_alias')
        parentGroupName = kwargs.get('parent_group_name')
        updateOpeningBalance = kwargs.get('update_opening_balance')
        ledgerMailingName = kwargs.get('ledger_mailing_name')
        address_1 = 'Headrun Tech'  # kwargs.get('address_1', '')
        address_2 = kwargs.get('address_2', '')
        address_3 = kwargs.get('address_3', '')
        state = kwargs.get('state')
        pinCode = kwargs.get('pin_code')
        country = kwargs.get('country')
        contactPerson = kwargs.get('contact_person')
        telephoneNo = kwargs.get('telephone_no')
        # new added
        mobileNo = kwargs.get('mobile_no')
        faxNo = kwargs.get('fax_no')
        email = kwargs.get('email')
        tinNo = kwargs.get('tin_no')
        cstNo = kwargs.get('cst_no')
        panNo = kwargs.get('pan_no')
        serviceTaxNo = kwargs.get('service_tax_no')
        defaultCreditPeriod = kwargs.get('default_credit_period')
        maintainBillWiseDetails = kwargs.get('maintain_billWise_details')

        # missing
        # custLedger.emailCc = "manager@abcindia.com";
        # custLedger.website = "www.abcindia.com";
        # custLedger.gstRegistrationType = "Regular";

        ledger = Tally.Ledger()

        # required
        ledger.tallyCompanyName = tallyCompanyName
        ledger.ledgerName = ledgerName
        ledger.ledgerAlias = str(ledgerAlias)
        ledger.parentGroupName = parentGroupName
        ledger.state = state

        # defaults if not passed
        ledger.maintainBillWiseDetails = maintainBillWiseDetails or True
        ledger.updateOpeningBalance = updateOpeningBalance or True
        # optional
        if openingBalance:
            ledger.openingBalance = System.Decimal(openingBalance)
        if country:
            ledger.country = country
        if contactPerson:
            ledger.contactPerson = contactPerson
        if telephoneNo:
            ledger.telephoneNo = telephoneNo
        if mobileNo:
            ledger.mobileNo = mobileNo
        if faxNo:
            ledger.faxNo = faxNo
        if email:
            ledger.email = email
        if tinNo:
            ledger.gstin = tinNo
        if cstNo:
            ledger.cstNo = cstNo
        if panNo:
            ledger.panNo = panNo
        if serviceTaxNo:
            ledger.serviceTaxNo = serviceTaxNo
        if pinCode:
            ledger.pinCode = pinCode
        if address_1:
            ledger.address = [address_1, address_2, address_3]
        if oldLedgerName:
            ledger.oldLedgerName = oldLedgerName
        if ledgerMailingName:
            ledger.ledgerMailingName = ledgerMailingName
        return self._transfer_and_get_resp(ledger, constants.VENDOR_OR_CUSTOMER)

    ##-- ITEM MASTER --##
    @utils.required(params=[
        'tally_company_name',
        'item_name',
        'sku_code',
        'unit_name',
        'stock_group_name',
        # 'stock_category_name',
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
        opening_qty = kwargs.get('opening_qty', 0)
        opening_rate = kwargs.get('opening_rate', 0)
        opening_amt = kwargs.get('opening_amt', 0)

        stock_item = Tally.StockItem()

        # required
        stock_item.tallyCompanyName = tally_company_name
        stock_item.itemName = item_name
        #stock_item.itemAlias = sku_code
        stock_item.primaryUnitName = unit_name or 'nos'
        stock_item.stockGroupName = stock_group_name
        stock_item.stockCategoryName = ''
        stock_item.openingQty = System.Decimal(opening_qty)
        stock_item.openingRate = System.Decimal(opening_rate)
        stock_item.openingAmt = System.Decimal(-1 * opening_amt)  # Opening stock amount should be negative

        # defaults if not passed
        stock_item.isVatAppl = is_vat_app or True

        # optional
        if old_item_name:
            stock_item.oldItemName = old_item_name
        if part_no:
            stock_item.partNo = part_no
        if description:
            stock_item.description = description
        return self._transfer_and_get_resp(stock_item, constants.ITEM_MASTER)

    @utils.required(params=[
        'tally_company_name',
        'voucher_foreign_key',
        'dt_of_voucher',
        'buyer_name',
        'buyer_state',
        'items',
        'party_ledger'
    ])
    def sales_returns(self, **kwargs):
        ''' Adds/Edits sales returns in tally
        required: [
            tally_company_name,
            voucher_foreign_key,
            dt_of_voucher,
            buyer_name,
            buyer_state,
            items,
            party_ledger
        ]
        optional: [
            party_ledger_tax,
            voucher_no,
            reference,
            reference_date,
            voucher_identifier,
            consignee_name,
            consignee_address,
            consignee_address_1,
            buyer_address_1,
            buyer_TIN_no,
            buyer_CST_no,
            type_of_dealer,
            narration
        ]
        default values if not pased: [
            voucher_type_name = Debit Note,
            type_of_voucher = Debit Note,
            is_invoice = True,
            is_optional = False
        ]
        '''
        tally_company_name = kwargs.get('tally_company_name')
        voucher_foreign_key = kwargs.get('dt_of_voucher')
        dt_of_voucher = kwargs.get('dt_of_voucher')
        buyer_name = kwargs.get('dt_of_voucher')
        buyer_state = kwargs.get('dt_of_voucher')
        items = kwargs.get('items')
        voucher_no = kwargs.get('voucher_no')
        reference = kwargs.get('reference')
        reference_date = kwargs.get('reference_date')
        voucher_identifier = kwargs.get('voucher_identifier')
        consignee_name = kwargs.get('consignee_name')
        consignee_address = kwargs.get('consignee_address')
        consignee_address_1 = kwargs.get('consignee_address_1')
        buyer_address_1 = kwargs.get('buyer_address_1')
        buyer_TIN_no = kwargs.get('buyer_TIN_no')
        buyer_CST_no = kwargs.get('buyer_CST_no')
        type_of_dealer = kwargs.get('type_of_dealer')
        narration = kwargs.get('narration')
        voucher_type_name = kwargs.get('voucher_type_name')
        type_of_voucher = kwargs.get('type_of_voucher')
        is_invoice = kwargs.get('is_invoice')
        is_optional = kwargs.get('is_optional')
        party_ledger = kwargs.get('party_ledger')
        party_ledger_tax = kwargs.get('party_ledger_tax')

        credit_note = Tally.CreditNote()
        debit_note = Tally.DebitNote()

        # required
        credit_note.tallyCompanyName = tally_company_name
        credit_note.voucherForeignKey = voucher_foreign_key
        credit_note.dtOfVoucher = System.DateTime.ParseExact(dt_of_voucher, "dd/MM/yyyy", null)
        credit_note.buyerName = buyer_name
        credit_note.buyerState = buyer_state
        # items entry
        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item.get('name')
            inv_entry.isDeemedPositive = item.get('is_deemed_positive', True)  # always True
            inv_entry.actualQty = System.Decimal(item.get('actual_qty'))
            inv_entry.billedQty = System.Decimal(item.get('billed_qty'))
            inv_entry.qtyUnit = item.get('qty_unit')
            inv_entry.rate = System.Decimal(item.get('rate'))
            inv_entry.rateUnit = item.get('rate_unit')
            inv_entry.discountPerc = System.Decimal(item.get('discount_percentage', 0))
            inv_entry.amount = System.Decimal(item.get('amount', 0) * -1)  # always positive
            # Accounting Allocation for the item
            inv_entry_acc = Tally.LedgerEntry()
            inv_entry_acc.ledgerName = item.get('ledger_name')
            inv_entry_acc.ledgerAmount = inv_entry.amount
            inv_entry.arlAccountingAllocations.Add(inv_entry_acc)
            debit_note.arlInvEntries.Add(inv_entry)
        # Party Ledger
        party_ledger_entry = Tally.LedgerEntry()
        party_ledger_entry.ledgerName = party_ledger.get('name')
        party_ledger_entry.ledgerAmount = System.Decimal(party_ledger.get('amount', 0))  # always positive
        party_ledger_entry.isDeemedPositive = party_ledger.get('is_deemed_positive') or False  # always False
        credit_note.arlLedgerEntries.Add(party_ledger_entry);

        # optional
        # party ledger tax entry
        if party_ledger_tax and party_ledger_tax.get('entry_rate', 0):
            party_ledger_tax_entry = Tally.LedgerEntry();
            party_ledger_tax_entry.ledgerName = party_ledger_tax.get('name')
            party_ledger_tax_entry.ledEntryRate = System.decimal(party_ledger_tax.get('entry_rate'))
            party_ledger_tax_entry.ledgerAmount = System.decimal(party_ledger_tax.get('amount')) * -1  # always negetive
            party_ledger_tax_entry.isDeemedPositive = party_ledger_tax.get('is_deemed_positive') or True  # always True
            debitNote.arlLedgerEntries.Add(party_ledger_tax_entry);
        # TODO: ROUND OFF
        if voucher_no:
            credit_note.voucherNo = voucher_no
        if reference:
            credit_note.reference = reference
        if reference_date:
            credit_note.referenceDate = System.DateTime.ParseExact(reference_date, "dd/MM/yyyy", null)
        if voucher_identifier:
            credit_note.voucherIdentifier = voucher_identifier
        if consignee_name:
            credit_note.consigneeName = consignee_name  # In case of Debit Note, consignee is same as buyer
        if consignee_address:
            credit_note.consigneeAddress = consignee_address
        if consignee_address_1:
            credit_note.consigneeAddress = [consignee_address_1, consignee_address_2, consignee_address_3]
        if buyer_address_1:
            credit_note.buyerAddress = [buyer_address_1, buyer_address_2, buyer_address_3]
        if buyer_TIN_no:
            credit_note.buyerTINNo = buyer_TIN_no
        if buyer_CST_no:
            credit_note.buyerCSTNo = buyer_CST_no
        if type_of_dealer:
            credit_note.typeOfDealer = type_of_dealer
        if narration:
            credit_note.narration = narration

        # defaults if not passed
        credit_note.voucherTypeName = voucher_type_name or "Credit Note"  # This should be the name of the Debit Note voucher type in Tally
        credit_note.typeOfVoucher = type_of_voucher or "Credit Note"
        credit_note.isInvoice = is_invoice or True
        credit_note.isOptional = is_optional or False
        return self._transfer_and_get_resp(credit_note, constants.CREDIT_NOTE_INVOICE)

    @utils.required(params=[
        'tally_company_name',
        'voucher_foreign_key',
        'dt_of_voucher',
        'buyer_name',
        'buyer_state',
        'items',
        'party_ledger'
    ])
    def purchase_returns(self, **kwargs):
        ''' Adds/Edits purchase returns in tally
        required: [
            tally_company_name,
            voucher_foreign_key,
            dt_of_voucher,
            buyer_name,
            buyer_state,
            items,
            party_ledger
        ]
        optional: [
            party_ledger_tax,
            voucher_no,
            reference,
            reference_date,
            voucher_identifier,
            consignee_name,
            consignee_address,
            consignee_address_1,
            buyer_address_1,
            buyer_TIN_no,
            buyer_CST_no,
            type_of_dealer,
            narration
        ]
        default values if not pased: [
            voucher_type_name = Debit Note,
            type_of_voucher = Debit Note,
            is_invoice = True,
            is_optional = False
        ]
        '''
        tally_company_name = kwargs.get('tally_company_name')
        voucher_foreign_key = kwargs.get('dt_of_voucher')
        dt_of_voucher = kwargs.get('dt_of_voucher')
        buyer_name = kwargs.get('dt_of_voucher')
        buyer_state = kwargs.get('dt_of_voucher')
        items = kwargs.get('items')
        voucher_no = kwargs.get('voucher_no')
        reference = kwargs.get('reference')
        reference_date = kwargs.get('reference_date')
        voucher_identifier = kwargs.get('voucher_identifier')
        consignee_name = kwargs.get('consignee_name')
        consignee_address = kwargs.get('consignee_address')
        consignee_address_1 = kwargs.get('consignee_address_1')
        buyer_address_1 = kwargs.get('buyer_address_1')
        buyer_TIN_no = kwargs.get('buyer_TIN_no')
        buyer_CST_no = kwargs.get('buyer_CST_no')
        type_of_dealer = kwargs.get('type_of_dealer')
        narration = kwargs.get('narration')
        voucher_type_name = kwargs.get('voucher_type_name')
        type_of_voucher = kwargs.get('type_of_voucher')
        is_invoice = kwargs.get('is_invoice')
        is_optional = kwargs.get('is_optional')
        party_ledger = kwargs.get('party_ledger')
        party_ledger_tax = kwargs.get('party_ledger_tax')

        debit_note = Tally.DebitNote()

        # required
        debit_note.tallyCompanyName = tally_company_name
        debit_note.voucherForeignKey = voucher_foreign_key
        debit_note.dtOfVoucher = System.DateTime.ParseExact(dt_of_voucher, "dd/MM/yyyy", null)
        debit_note.buyerName = buyer_name
        debit_note.buyerState = buyer_state
        # items entry
        for item in items:
            inv_entry = Tally.InventoryEntry()
            inv_entry.itemName = item.get('name')
            inv_entry.isDeemedPositive = item.get('is_deemed_positive', False)  # always False
            inv_entry.actualQty = item.get('actual_qty')
            inv_entry.billedQty = item.get('billed_qty')
            inv_entry.qtyUnit = item.get('qty_unit')
            inv_entry.rate = item.get('rate')
            inv_entry.rateUnit = item.get('rate_unit')
            inv_entry.discountPerc = item.get('discount_percentage', 0)
            inv_entry.amount = System.Decimal(item.get('amount'))  # always positive
            # Accounting Allocation for the item
            inv_entry_acc = Tally.LedgerEntry()
            inv_entry_acc.ledgerName = item.get('ledger_name')
            inv_entry_acc.ledgerAmount = inv_entry.amount
            inv_entry.arlAccountingAllocations.Add(inv_entry_acc)
            debitNote.arlInvEntries.Add(inv_entry)
        # Party Ledger
        party_ledger_entry = Tally.LedgerEntry()
        party_ledger_entry.ledgerName = party_ledger.get('name')
        party_ledger_entry.ledgerAmount = System.Decimal(party_ledger.get('amount', 0)) * -1  # always negetive
        party_ledger_entry.isDeemedPositive = party_ledger.get('is_deemed_positive') or True  # always True
        debit_note.arlLedgerEntries.Add(party_ledger_entry);

        # optional
        # party ledger tax entry
        if party_ledger_tax and party_ledger_tax.get('entry_rate', 0):
            party_ledger_tax_entry = Tally.LedgerEntry();
            party_ledger_tax_entry.ledgerName = party_ledger_tax.get('name')
            party_ledger_tax_entry.ledEntryRate = System.decimal(party_ledger_tax.get('entry_rate'))
            party_ledger_tax_entry.ledgerAmount = System.decimal(party_ledger_tax.get('amount'))  # always positive
            party_ledger_tax_entry.isDeemedPositive = party_ledger_tax.get(
                'is_deemed_positive') or False  # always False
            debitNote.arlLedgerEntries.Add(party_ledger_tax_entry);
        # TODO: ROUND OFF
        if voucher_no:
            debit_note.voucherNo = voucher_no
        if reference:
            debit_note.reference = reference
        if reference_date:
            debit_note.referenceDate = System.DateTime.ParseExact(reference_date, "dd/MM/yyyy", null)
        if voucher_identifier:
            debit_note.voucherIdentifier = voucher_identifier
        if consignee_name:
            debit_note.consigneeName = consignee_name  # In case of Debit Note, consignee is same as buyer
        if consignee_address:
            debit_note.consigneeAddress = consignee_address
        if consignee_address_1:
            debit_note.consigneeAddress = [consignee_address_1, consignee_address_2, consignee_address_3]
        if buyer_address_1:
            debit_note.buyerAddress = [buyer_address_1, buyer_address_2, buyer_address_3]
        if buyer_TIN_no:
            debit_note.buyerTINNo = buyer_TIN_no
        if buyer_CST_no:
            debit_note.buyerCSTNo = buyer_CST_no
        if type_of_dealer:
            debit_note.typeOfDealer = type_of_dealer
        if narration:
            debit_note.narration = narration

        # defaults if not passed
        debit_note.voucherTypeName = voucher_type_name or "Debit Note"  # This should be the name of the Debit Note voucher type in Tally
        debit_note.typeOfVoucher = type_of_voucher or "Debit Note"
        debit_note.isInvoice = is_invoice or True
        debit_note.isOptional = is_optional or False
        return self._transfer_and_get_resp(debit_note, constants.DEBIT_NOTE_INVOICE)

    # private
    def _transfer_and_get_resp(self, obj, type):
        ''' transfer the objects to tally using dll 
        and responds accordingly
        '''
        resp = Tally.TallyResponse()
        resp = self.TRANSFER_FUNCTION_MAP[type](obj)
        if resp.errorMsg:
            raise common_exceptions.TallyDataTransferError(error_message=resp.errorMsg)
        return {'success': True, 'type': type, 'resp': resp}
