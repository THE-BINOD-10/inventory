import clr
import sys
import urllib2
from scrapy import Selector
#from System.Collections import *
#from System import *
#from System.Collections.Generic import *
#from System.Data import *
#import System
import datetime

#sys.path.append('D:\TallyBridgeTool\DLL')
#clr.AddReference('TallyBridgeDll')

#from Tally import *
#from TallyBridge import *

class TallySample:

    def __init__(self, *args, **kwargs):
        #self.tb = TallyBridgeDll()
	pass

    def PostLedger(self, **kwargs):
        import pdb;pdb.set_trace()
	tallyCompanyName = kwargs.get('tallyCompanyName', '')
	oldLedgerName = kwargs.get('oldLedgerName', '')
	ledgerName = kwargs.get('LedgerName', '')
	openingBalance = kwargs.get('openingBalance', '')
	parentGroupName = kwargs.get('parentGroupName', '')
	updateOpeningBalance = kwargs.get('updateOpeningBalance', '')
	ledgerMailingName = kwargs.get('ledgerMailingName', '')
	return
	if tallyCompanyName:
	        x = Ledger()
        	x.tallyCompanyName = tallyCompanyName#"Mieone";
		if oldLedgerName:
		        x.oldLedgerName = oldLedgerName#"Aravind";
        	x.ledgerName = ledgerName#"Aravind 123";
		if updateOpeningBalance:
			x.updateOpeningBalance = True;
	        	x.openingBalance =  System.Decimal(openingBalance)#System.Decimal(-200000);

	        x.ledgerMailingName = ledgerMailingName#"M/s ABCDDD India Pvt. Ltd.";
        	x.parentGroupName = parentGroupName#"Sundry Debtors";
	        tresponse = TallyResponse()
        	tresponse = self.tb.DoTransferLedger(x)
	        if tresponse.errorMsg:
        	    print tresponse
	        else:
        	    print 'success ledger'

    def PostStockItem(self):
        stockItem = StockItem();
        stockItem.tallyCompanyName = "Mieone";

        stockItem.itemName = "Plain Note Book One";#Description

        #You can map SKU code either in item alias or in part no.
        stockItem.itemAlias = "PNB0002";

        #The unit master should already exist in Tally.
        stockItem.primaryUnitName = "nos";
        
        #The stock group should already exist in Tally
        stockItem.stockGroupName = "Stock Group 1";

        #The stock category should already exist in Tally
        #stockItem.stockCategoryName = "Stk Cat 1";

        stockItem.isVatAppl = True;

        #Opening Stock qty in primary units
        stockItem.openingQty = System.Decimal(2);
        stockItem.openingRate = System.Decimal(100);

        #Opening stock amount should ne negative
        stockItem.openingAmt = System.Decimal(-200);

        tresponse = TallyResponse()
        tresponse = self.tb.DoTransferStockItem(stockItem);
        if tresponse.errorMsg:
            print tresponse.errorMsg
        else:
            print 'success stock'


    def PostSalesVoucher(self):
        '''sv = SalesVoucher()
        sv.tallyCompanyName = "Mieone"
        sv.voucherForeignKey = "SLS-005";#unique id of transaction in external software
        sv.dtOfVoucher = datetime.ParseExact("01/04/2016", "dd/MM/yyyy", null);
        sv.voucherTypeName = "Sales";#name of sales voucher type in Tally
        sv.typeOfVoucher = "Sales";#Hardcoded
        sv.voucherNo = "5";'''
        invoice = SalesVoucher();
        invoice.tallyCompanyName = "Mieone";

        #This should be a unique id of the transaction in the external software
        invoice.voucherForeignKey = "SLS-003";

        invoice.dtOfVoucher = System.DateTime.ParseExact("01/05/2016", "dd/MM/yyyy", None);

        #This should be the name of the sales voucher type in Tally
        invoice.voucherTypeName = "Sales";

        #This should be hardcoded as Sales
        invoice.typeOfVoucher = "Sales";

        #You can leave it blank if voucher number is configured as automatic in Tally
        invoice.voucherNo = "1";

        invoice.reference = "ref111";

        #If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
        invoice.voucherIdentifier = "SLS-003";
        

        invoice.despatchDocNo = "Des Doc11";
        invoice.despatchedThrough = "Desp Thru11";
        invoice.destination = "Some Destination";

        #Voucher.OrderDetails 
        ord1 = Voucher.OrderDetails();
        ord1.orderNo = "ORD1";
        ord1.orderDate = System.DateTime.Parse("1-May-2016");
        
        #Voucher.OrderDetails 
        ord2 = Voucher.OrderDetails();
        ord2.orderNo = "ORD2";
        ord2.orderDate = System.DateTime.Parse("1-May-2016");

    
        import pdb;pdb.set_trace()
        invoice.orderDetails = [ord1, ord2]
        #invoice.orderDetails[0] = ord1;        
        #invoice.orderDetails[1] = ord2;
        invoice.termsOfPayment = "Some Terms of Pay";

        #invoice.useSeparateBuyerConsAddr = False;
        invoice.buyerName = "Aravind 123";
        invoice.buyerAddress = ["Buyer Addr2", "Buyer Addr3" ]
        invoice.buyerState = "Karnataka";
        invoice.buyerTINNo = "29123456789";
        invoice.buyerCSTNo = "Buyer CST11";
        invoice.typeOfDealer = "Unregistered Dealer";


        invoice.narration = "Some Narration";
        invoice.isInvoice = True;
        invoice.isOptional = False;


        #1st item in invoice
        invEntry = InventoryEntry();

        #You can give either the main name of the item, or its alias, or its part number
        invEntry.itemName = "Plain Note Book One";
        invEntry.actualQty = System.Decimal(10);
        invEntry.billedQty = System.Decimal(10);
        invEntry.qtyUnit = "nos";
        invEntry.rate = System.Decimal(150);    
        invEntry.rateUnit = "nos";
        invEntry.amount = System.Decimal(1500);

        #Accounting Allocation for the 1st item
        leAccAlloc = LedgerEntry();
        leAccAlloc.ledgerName = "SALES LEDGER2";
        leAccAlloc.ledgerAmount = invEntry.amount;


        invEntry.arlAccountingAllocations.Add(leAccAlloc);
        invoice.arlInvEntries.Add(invEntry);

        #2nd item in invoice
        invEntry = InventoryEntry();
        invEntry.itemName = "Plain Note Book One";
        invEntry.actualQty = System.Decimal(10);
        invEntry.billedQty = System.Decimal(10);
        invEntry.qtyUnit = "nos";
        invEntry.rate = System.Decimal(150);
        invEntry.rateUnit = "nos";
        invEntry.amount = System.Decimal(1500);

        #Accounting Allocation for the 2nd item
        leAccAlloc = LedgerEntry();
        leAccAlloc.ledgerName = "SALES LEDGER2";
        leAccAlloc.ledgerAmount = invEntry.amount;

        invEntry.arlAccountingAllocations.Add(leAccAlloc);
        invoice.arlInvEntries.Add(invEntry);


        #Party Ledger
        lePartyLedger = LedgerEntry();
        lePartyLedger.ledgerName = "Aravind 123";

        #This should be the grand total of the invoice (including VAT and any other charges) with a negative sign
        #Debit ledgers should be posted with a negative amount and isDeemedPositive should be set to True
        lePartyLedger.ledgerAmount = System.Decimal(-3165);
        lePartyLedger.isDeemedPositive = True;

        #Party ledger should be the 1st ledger in the invoice
        invoice.arlLedgerEntries.Add(lePartyLedger);

        leAddlLedger = LedgerEntry();
        leAddlLedger.ledgerName = "Output VAT @ 5.5%";
        leAddlLedger.ledEntryRate = System.Decimal(5.5);
        leAddlLedger.ledgerAmount = System.Decimal(165);
        leAddlLedger.isDeemedPositive = False;
        invoice.arlLedgerEntries.Add(leAddlLedger);
        
        tresponse = TallyResponse()
        tresponse = self.tb.DoTransferVoucher(invoice);
        if tresponse.errorMsg:
            print tresponse.errorMsg
        else:
            print 'success SalesVoucher'

def Customer( tobj):
    CustomerUrl = 'http://176.9.181.43:8778/rest_api/get_customer_data'
    response = urllib2.urlopen(CustomerUrl)
    xml = response.read()
    sel = Selector(text=xml)
    nodes = sel.xpath('//root/item/orders')
    for node in nodes:
  	tallyCompanyName, ledgerName, updateOpeningBalance, ledgerMailingName, parentGroupName = node.xpath('.//text()').extract()
	customerledgers = [{'tallyCompanyName': tallyCompanyName, 'oldLedgerName': '', 'ledgerName': ledgerName, 'openingBalance' : '', 'parentGroupName' : parentGroupName, 'updateOpeningBalance' : updateOpeningBalance ,'ledgerMailingName' : ledgerMailingName }]
	print customerledgers
        import pdb;pdb.set_trace()
	for ledgers in customerledgers:
		tobj.PostLedger(**ledgers)
    response.close()
    


if __name__ == '__main__':
    tobj = TallySample()
    #tobj.PostStockItem()
    Customer(tobj)
    '''ledgers = [{'tallyCompanyName': '', 'oldLedgerName': '', 'ledgerName': '', 'openingBalance' : '', 'parentGroupName' : '', 'updateOpeningBalance' : '' ,'ledgerMailingName' : '' }]
    for led in ledgers:
        tobj.PostLedger(**led)'''
    #tobj.PostSalesVoucher()
