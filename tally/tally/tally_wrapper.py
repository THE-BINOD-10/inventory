#!/usr/bin/env python

import clr
import sys
import datetime

from optparse import OptionParser

from scrapy import Selector

import constants
import exceptions

sys.path.append(constants.DLL_BASE_PATH)


class TallyBridgeApp(object):

    def __init__(self, *args, **kwargs):
        self.dll_file = kwargs.get('dll', constants.DLL_FILE_NAME)
        clr.AddReference(self.dll_file)
        import Tally
        import TallyBridge

    # customer mater + vendor master
    def post_ledger(self, **kwargs):
        tallyCompanyName = kwargs.get('tallyCompanyName', '')
        oldLedgerName = kwargs.get('oldLedgerName', '')
        ledgerName = kwargs.get('LedgerName', '')
        openingBalance = kwargs.get('openingBalance', '')
        parentGroupName = kwargs.get('parentGroupName', '')
        updateOpeningBalance = kwargs.get('updateOpeningBalance', '')
        ledgerMailingName = kwargs.get('ledgerMailingName', '')
        
        ledger = Tally.Ledger()
        if tallyCompanyName:
            ledger.tallyCompanyName = tallyCompanyName #"Mieone"
        if oldLedgerName:
            ledger.oldLedgerName = oldLedgerName #"Aravind"
            ledger.ledgerName = ledgerName #"Aravind 123"
        if updateOpeningBalance:
            ledger.updateOpeningBalance = True
            ledger.openingBalance =  System.Decimal(openingBalance) #System.Decimal(-200000)
            ledger.ledgerMailingName = ledgerMailingName #"M/s ABCDDD India Pvt. Ltd."
            ledger.parentGroupName = parentGroupName #"Sundry Debtors"
            tresponse = Tally.TallyResponse()
            tresponse = self.tb.DoTransferLedger(x)
            if tresponse.errorMsg:
                print tresponse
            else:
                print 'success ledger'

    # item master
    def post_stock_item(self):
        stockItem = StockItem()
        stockItem.tallyCompanyName = "Mieone"
        stockItem.itemName = "Plain Note Book One"#Description
        #You can map SKU code either in item alias or in part no.
        stockItem.itemAlias = "PNB0002"
        #The unit master should already exist in Tally.
        stockItem.primaryUnitName = "nos"
        #The stock group should already exist in Tally
        stockItem.stockGroupName = "Stock Group 1"
        #The stock category should already exist in Tally
        #stockItem.stockCategoryName = "Stk Cat 1"
        stockItem.isVatAppl = True
        #Opening Stock qty in primary units
        stockItem.openingQty = System.Decimal(2)
        stockItem.openingRate = System.Decimal(100)
        #Opening stock amount should ne negative
        stockItem.openingAmt = System.Decimal(-200)
        tresponse = TallyResponse()
        tresponse = self.tb.DoTransferStockItem(stockItem)
        if tresponse.errorMsg:
            print tresponse.errorMsg
            return
        print 'success stock'
        return

    # sales invoice
    def post_sales_voucher(self):
        '''sv = SalesVoucher()
        sv.tallyCompanyName = "Mieone"
        sv.voucherForeignKey = "SLS-005"#unique id of transaction in external software
        sv.dtOfVoucher = datetime.ParseExact("01/04/2016", "dd/MM/yyyy", null)
        sv.voucherTypeName = "Sales"#name of sales voucher type in Tally
        sv.typeOfVoucher = "Sales"#Hardcoded
        sv.voucherNo = "5"'''
        invoice = SalesVoucher()
        invoice.tallyCompanyName = "Mieone"
        invoice.voucherForeignKey = "SLS-003" #This should be a unique id of the transaction in the external software
        invoice.dtOfVoucher = System.DateTime.ParseExact("01/05/2016", "dd/MM/yyyy", None)
        invoice.voucherTypeName = "Sales" #This should be the name of the sales voucher type in Tally
        invoice.typeOfVoucher = "Sales" #This should be hardcoded as Sales
        invoice.voucherNo = "1" #You can leave it blank if voucher number is configured as automatic in Tally
        invoice.reference = "ref111"
        invoice.voucherIdentifier = "SLS-003" #If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
        invoice.despatchDocNo = "Des Doc11"
        invoice.despatchedThrough = "Desp Thru11"
        invoice.destination = "Some Destination"
        #Voucher.OrderDetails 
        ord1 = Voucher.OrderDetails()
        ord1.orderNo = "ORD1"
        ord1.orderDate = System.DateTime.Parse("1-May-2016")
        #Voucher.OrderDetails
        ord2 = Voucher.OrderDetails()
        ord2.orderNo = "ORD2"
        ord2.orderDate = System.DateTime.Parse("1-May-2016")

        import pdb;pdb.set_trace()
        invoice.orderDetails = [ord1, ord2]
        #invoice.orderDetails[0] = ord1        
        #invoice.orderDetails[1] = ord2
        invoice.termsOfPayment = "Some Terms of Pay"

        #invoice.useSeparateBuyerConsAddr = False
        invoice.buyerName = "Aravind 123"
        invoice.buyerAddress = ["Buyer Addr2", "Buyer Addr3" ]
        invoice.buyerState = "Karnataka"
        invoice.buyerTINNo = "29123456789"
        invoice.buyerCSTNo = "Buyer CST11"
        invoice.typeOfDealer = "Unregistered Dealer"
        invoice.narration = "Some Narration"
        invoice.isInvoice = True
        invoice.isOptional = False

        #1st item in invoice
        invEntry = InventoryEntry()
        invEntry.itemName = "Plain Note Book One" #You can give either the main name of the item, or its alias, or its part number
        invEntry.actualQty = System.Decimal(10)
        invEntry.billedQty = System.Decimal(10)
        invEntry.qtyUnit = "nos"
        invEntry.rate = System.Decimal(150)    
        invEntry.rateUnit = "nos"
        invEntry.amount = System.Decimal(1500)

        #Accounting Allocation for the 1st item
        leAccAlloc = LedgerEntry() 
        leAccAlloc.ledgerName = "SALES LEDGER2"
        leAccAlloc.ledgerAmount = invEntry.amount


        invEntry.arlAccountingAllocations.Add(leAccAlloc)
        invoice.arlInvEntries.Add(invEntry)

        #2nd item in invoice
        invEntry = InventoryEntry()
        invEntry.itemName = "Plain Note Book One"
        invEntry.actualQty = System.Decimal(10)
        invEntry.billedQty = System.Decimal(10)
        invEntry.qtyUnit = "nos"
        invEntry.rate = System.Decimal(150)
        invEntry.rateUnit = "nos"
        invEntry.amount = System.Decimal(1500)

        #Accounting Allocation for the 2nd item
        leAccAlloc = LedgerEntry()
        leAccAlloc.ledgerName = "SALES LEDGER2"
        leAccAlloc.ledgerAmount = invEntry.amount

        invEntry.arlAccountingAllocations.Add(leAccAlloc)
        invoice.arlInvEntries.Add(invEntry)

        #Party Ledger
        lePartyLedger = LedgerEntry()
        lePartyLedger.ledgerName = "Aravind 123"

        #This should be the grand total of the invoice (including VAT and any other charges) with a negative sign
        #Debit ledgers should be posted with a negative amount and isDeemedPositive should be set to True
        lePartyLedger.ledgerAmount = System.Decimal(-3165)
        lePartyLedger.isDeemedPositive = True

        #Party ledger should be the 1st ledger in the invoice
        invoice.arlLedgerEntries.Add(lePartyLedger)

        leAddlLedger = LedgerEntry()
        leAddlLedger.ledgerName = "Output VAT @ 5.5%"
        leAddlLedger.ledEntryRate = System.Decimal(5.5)
        leAddlLedger.ledgerAmount = System.Decimal(165)
        leAddlLedger.isDeemedPositive = False
        invoice.arlLedgerEntries.Add(leAddlLedger)
        
        tresponse = TallyResponse()
        tresponse = self.tb.DoTransferVoucher(invoice)
        if tresponse.errorMsg:
            print tresponse.errorMsg
        else:
            print 'success SalesVoucher'
