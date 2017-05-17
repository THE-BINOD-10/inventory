using System;
using System.Collections.Generic;
using System.Collections;
using System.Collections.Specialized;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Text;
using System.Windows.Forms;

using Tally;
using TallyBridge;


namespace TallyBridgeApp
{
    public partial class TallyBridgeTest : Form
    {
        TallyBridge.TallyBridgeDll tb;
        public TallyBridgeTest()
        {
            InitializeComponent();
            tb = new TallyBridgeDll();
        }

        private void TallyBridgeTest_Load(object sender, EventArgs e)
        {
            btnCustomerMaster.Click += new EventHandler(btnCustomerMaster_Click);
            btnVendorMaster.Click += new EventHandler(btnVendorMaster_Click);
            btnStockItemMaster.Click += new EventHandler(btnStockItemMaster_Click);

            btnSalesInvoice.Click += new EventHandler(btnSalesInvoice_Click);
            btnPurcInvMode.Click += new EventHandler(btnPurcInvMode_Click);
            btnDebitNoteInvMode.Click += new EventHandler(btnDebitNoteInvMode_Click);
            btnCreditNoteInvMode.Click += new EventHandler(btnCreditNoteInvMode_Click);
        }


        void btnSalesInvoice_Click(object sender, EventArgs e)
        {
            SalesVoucher invoice = null;
            InventoryEntry invEntry = null;
            LedgerEntry leAccAlloc = null;
            LedgerEntry lePartyLedger = null;
            LedgerEntry leAddlLedger = null;
            BillAllocation billAlloc = null;
            TallyResponse tallyResponse = null;

            invoice = new SalesVoucher();
            invoice.tallyCompanyName = "Miebach Demo Data";

            //This should be a unique id of the transaction in the external software
            invoice.voucherForeignKey = "SLS-001";

            invoice.dtOfVoucher = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //This should be the name of the sales voucher type in Tally
            invoice.voucherTypeName = "Sales";

            //This should be hardcoded as Sales
            invoice.typeOfVoucher = "Sales";

            //You can leave it blank if voucher number is configured as automatic in Tally
            invoice.voucherNo = "1";

            invoice.reference = "ref111";

            //If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
            invoice.voucherIdentifier = "SLS-001";


            Voucher.DeliveryNoteDetails delNote1 = new Voucher.DeliveryNoteDetails();
            delNote1.deliveryNoteNo = "DN1";
            delNote1.deliveryNoteDate = DateTime.Parse("1-Apr-2016");

            Voucher.DeliveryNoteDetails delNote2 = new Voucher.DeliveryNoteDetails();
            delNote2.deliveryNoteNo = "DN2";
            delNote2.deliveryNoteDate = DateTime.Parse("1-Apr-2016");

            invoice.deliveryNotes = new Voucher.DeliveryNoteDetails[2];
            invoice.deliveryNotes[0] = delNote1;
            invoice.deliveryNotes[1] = delNote2;

            invoice.despatchDocNo = "Des Doc11";
            invoice.despatchedThrough = "Desp Thru11";
            invoice.destination = "Some Destination";

            invoice.billOfLadingNo = "RR1";
            invoice.billOfLadingDt = DateTime.Parse("01-Apr-2016");
            invoice.carrierName = "Carrier1";

            Voucher.OrderDetails ord1 = new Voucher.OrderDetails();
            ord1.orderNo = "ORD1";
            ord1.orderDate = DateTime.Parse("1-Apr-2016");
            
            Voucher.OrderDetails ord2 = new Voucher.OrderDetails();
            ord2.orderNo = "ORD2";
            ord2.orderDate = DateTime.Parse("1-Apr-2016");

            invoice.orderDetails = new Voucher.OrderDetails[2];
            invoice.orderDetails[0] = ord1;
            invoice.orderDetails[1] = ord2;
            invoice.termsOfPayment = "Some Terms of Pay111";
            invoice.otherReference = "Misc. Ref";
            invoice.termsOfDelivery = new string[2];
            invoice.termsOfDelivery[0] = "Del Terms1";
            invoice.termsOfDelivery[1] = "Del Terms2";

            invoice.useSeparateBuyerConsAddr = false;
            invoice.buyerName = "ABC India Pvt. Ltd.";
            invoice.buyerAddress = new string[3];
            invoice.buyerAddress[0] = "Buyer Addr1";
            invoice.buyerAddress[1] = "Buyer Addr2";
            invoice.buyerAddress[2] = "Buyer Addr3";
            invoice.buyerState = "Karnataka";
            invoice.buyerTINNo = "29123456789";
            invoice.buyerCSTNo = "Buyer CST11";
            invoice.typeOfDealer = "Unregistered Dealer";


            invoice.narration = "Some Narration";
            invoice.isInvoice = true;
            invoice.isOptional = false;


            //1st item in invoice
            invEntry = new InventoryEntry();

            //You can give either the main name of the item, or its alias, or its part number
            invEntry.itemName = "Plain Note Book";
            invEntry.actualQty = 10;
            invEntry.billedQty = 10;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 150;
            invEntry.rateUnit = "nos";
            invEntry.amount = 1500;

            //Accounting Allocation for the 1st item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Sales 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;


            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            invoice.arlInvEntries.Add(invEntry);

            //2nd item in invoice
            invEntry = new InventoryEntry();
            invEntry.itemName = "Plain Note Book";
            invEntry.actualQty = 10;
            invEntry.billedQty = 10;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 150;
            invEntry.rateUnit = "nos";
            invEntry.amount = 1500;

            //Accounting Allocation for the 2nd item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Sales 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            invoice.arlInvEntries.Add(invEntry);


            //Party Ledger
            lePartyLedger = new LedgerEntry();
            lePartyLedger.ledgerName = "ABC India Pvt. Ltd.";

            //This should be the grand total of the invoice (including VAT and any other charges) with a negative sign
            //Debit ledgers should be posted with a negative amount and isDeemedPositive should be set to true
            lePartyLedger.ledgerAmount = (decimal)-3165;
            lePartyLedger.isDeemedPositive = true;

            //Party ledger should be the 1st ledger in the invoice
            invoice.arlLedgerEntries.Add(lePartyLedger);

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Output VAT 5.5%";
            leAddlLedger.ledEntryRate = (decimal) 5.5;
            leAddlLedger.ledgerAmount = (decimal)165;
            leAddlLedger.isDeemedPositive = false;
            invoice.arlLedgerEntries.Add(leAddlLedger);

            tallyResponse = tb.DoTransferVoucher(invoice);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Voucher uploaded successfully", "Tally Bridge Tool");
            }
        }

        void btnPurcInvMode_Click(object sender, EventArgs e)
        {
            PurchaseVoucher invoice = null;
            InventoryEntry invEntry = null;
            LedgerEntry leAccAlloc = null;
            LedgerEntry lePartyLedger = null;
            LedgerEntry leAddlLedger = null;
            BillAllocation billAlloc = null;
            TallyResponse tallyResponse = null;

            invoice = new PurchaseVoucher();
            invoice.tallyCompanyName = "Miebach Demo Data";

            //This should be a unique id of the transaction in the external software
            invoice.voucherForeignKey = "PURC-001";

            invoice.dtOfVoucher = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //This should be the name of the Purchase voucher type in Tally
            invoice.voucherTypeName = "Purchase";

            //This should be hardcoded as Purchase
            invoice.typeOfVoucher = "Purchase";

            //You can leave it blank if voucher number is configured as automatic in Tally
            invoice.voucherNo = "1";

            //Supplier Invoice No
            invoice.reference = "2602";

            //Supplier Invoice Date
            invoice.referenceDate = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
            invoice.voucherIdentifier = "PURC-001";

            
            invoice.supplierName = "Knowledge Invention";
            invoice.supplierAddress = new string[3];
            invoice.supplierAddress[0] = "#10, Bore Bank Road,";
            invoice.supplierAddress[1] = "Benson Town";
            invoice.supplierAddress[2] = "Bangalore - 560046";
            invoice.supplierState = "Karnataka";
            invoice.supplierTINNo = "29791201650";
            invoice.supplierCSTNo = "29791201650";
            invoice.typeOfDealer = "Unregistered Dealer";

            //In case of purchase, consignee is our company
            invoice.consigneeName = "Miebach Demo Data";
            invoice.consigneeAddress = new string[3];
            invoice.consigneeAddress[0] = "Our Addr1";
            invoice.consigneeAddress[1] = "Our Addr2";
            invoice.consigneeAddress[2] = "Our Addr3";
            invoice.consigneeTINNo = "Our TIN No. 123";
            invoice.consigneeCSTNo = "Our CST No. 123";

            invoice.narration = "Some Narration";
            invoice.isInvoice = true;
            invoice.isOptional = false;


            //1st item in invoice
            invEntry = new InventoryEntry();

            //You can give either the main name of the item, or its alias, or its part number
            invEntry.itemName = "96 Pages Maths Ruled";

            //For purchases, items should have isDeemedPositive set to true
            invEntry.isDeemedPositive = true;

            invEntry.actualQty = 500;
            invEntry.billedQty = 500;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.discountPerc = 5;

            //For purchase items, amount should be negative
            invEntry.amount = (decimal) -7125;

            //Accounting Allocation for the 1st item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "Vat Purchases 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            invoice.arlInvEntries.Add(invEntry);

            //2nd item in invoice
            invEntry = new InventoryEntry();
            invEntry.itemName = "96 Pages Un Ruled";
            invEntry.isDeemedPositive = true;
            invEntry.actualQty = 120;
            invEntry.billedQty = 120;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.amount = (decimal) -1800;

            //Accounting Allocation for the 2nd item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Purchases 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            invoice.arlInvEntries.Add(invEntry);


            //Party Ledger
            lePartyLedger = new LedgerEntry();
            lePartyLedger.ledgerName = "Knowledge Invention";

            //This should be the grand total of the invoice (including VAT and any other charges) with a positive sign
            //isDeemedPositive should be set to false
            lePartyLedger.ledgerAmount = (decimal)9415;
            lePartyLedger.isDeemedPositive = false;

            //Party ledger should be the 1st ledger in the invoice
            invoice.arlLedgerEntries.Add(lePartyLedger);


            //All additional ledgers in Purchase (Invoice Mode) should have isDeemedPositive set to true
            //However, if the actual amount like Input VAT is positive, the value in ledgerAmount should be negative
            //and if the actual amount like Round Off is negative, the value in ledgerAmount should be positive
            //This applies to Purchase (Invoice Mode).
            //The behaviour for Purchase (Voucher Mode) is different

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Input VAT 5.5%";
            leAddlLedger.ledEntryRate = (decimal)5.5;
            leAddlLedger.ledgerAmount = (decimal)490.88 * -1;
            leAddlLedger.isDeemedPositive = true;
            invoice.arlLedgerEntries.Add(leAddlLedger);

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Round Off";
            leAddlLedger.ledgerAmount = (decimal)0.88;
            leAddlLedger.isDeemedPositive = true;
            invoice.arlLedgerEntries.Add(leAddlLedger);


            tallyResponse = tb.DoTransferVoucher(invoice);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Voucher uploaded successfully", "Tally Bridge Tool");
            }
        }


        void btnDebitNoteInvMode_Click(object sender, EventArgs e)
        {
            DebitNote debitNote = null;
            InventoryEntry invEntry = null;
            LedgerEntry leAccAlloc = null;
            LedgerEntry lePartyLedger = null;
            LedgerEntry leAddlLedger = null;
            BillAllocation billAlloc = null;
            TallyResponse tallyResponse = null;

            debitNote = new DebitNote();
            debitNote.tallyCompanyName = "Miebach Demo Data";

            //This should be a unique id of the transaction in the external software
            debitNote.voucherForeignKey = "DN-001";

            debitNote.dtOfVoucher = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //This should be the name of the Debit Note voucher type in Tally
            debitNote.voucherTypeName = "Debit Note";

            //This should be hardcoded as Debit Note
            debitNote.typeOfVoucher = "Debit Note";

            //You can leave it blank if voucher number is configured as automatic in Tally
            debitNote.voucherNo = "1";

            //Original Invoice No
            debitNote.reference = "313";

            //Original Invoice Date
            debitNote.referenceDate = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
            debitNote.voucherIdentifier = "DN-001";

            //In case of Debit Note, Buyer is the company to whom we are returning goods
            //You can think of Debit Note as if instead of returning goods to supplier
            //we are selling to supplier
            debitNote.buyerName = "Knowledge Invention";
            debitNote.buyerAddress = new string[3];
            debitNote.buyerAddress[0] = "#10, Bore Bank Road,";
            debitNote.buyerAddress[1] = "Benson Town";
            debitNote.buyerAddress[2] = "Bangalore - 560046";
            debitNote.buyerState = "Karnataka";
            debitNote.buyerTINNo = "KI TIN 123";
            debitNote.buyerCSTNo = "KI CST 123";
            debitNote.typeOfDealer = "Unregistered Dealer";

            //In case of Debit Note, consignee is same as buyer
            debitNote.consigneeName = "Knowledge Invention";
            debitNote.consigneeAddress = new string[3];
            debitNote.consigneeAddress[0] = "#10, Bore Bank Road,";
            debitNote.consigneeAddress[1] = "Benson Town";
            debitNote.consigneeAddress[2] = "Bangalore - 560046";

            debitNote.narration = "Some Narration";
            debitNote.isInvoice = true;
            debitNote.isOptional = false;


            //1st item in invoice
            invEntry = new InventoryEntry();

            //You can give either the main name of the item, or its alias, or its part number
            invEntry.itemName = "96 Pages Maths Ruled";

            //For debit note i.e. purchase returns, items should have isDeemedPositive set to false
            invEntry.isDeemedPositive = false;

            invEntry.actualQty = 2;
            invEntry.billedQty = 2;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.discountPerc = 0;

            //For debit note i.e. purchase returns, item amount should be positive
            invEntry.amount = (decimal)30;

            //Accounting Allocation for the 1st item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "Vat Purchases 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            debitNote.arlInvEntries.Add(invEntry);

            //2nd item in invoice
            invEntry = new InventoryEntry();
            invEntry.itemName = "96 Pages Un Ruled";
            invEntry.isDeemedPositive = false;
            invEntry.actualQty = 3;
            invEntry.billedQty = 3;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.amount = (decimal)45;

            //Accounting Allocation for the 2nd item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Purchases 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            debitNote.arlInvEntries.Add(invEntry);


            //Party Ledger
            lePartyLedger = new LedgerEntry();
            lePartyLedger.ledgerName = "Knowledge Invention";

            //This should be the grand total of the invoice (including VAT and any other charges) with a negative sign
            //isDeemedPositive should be set to true
            lePartyLedger.ledgerAmount = (decimal)-79;
            lePartyLedger.isDeemedPositive = true;

            //Party ledger should be the 1st ledger in the invoice
            debitNote.arlLedgerEntries.Add(lePartyLedger);


            //All additional ledgers in Debit Note (Invoice Mode) i.e. Purchase Returns should have isDeemedPositive set to false
            //However, if the actual amount like Input VAT is positive, the value in ledgerAmount should also be positive
            //and if the actual amount like Round Off is negative, the value in ledgerAmount should also be negative
            //This applies to Debit Note (Invoice Mode).
            //The behaviour for Debit Note (Voucher Mode)  is different

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Input VAT 5.5%";
            leAddlLedger.ledEntryRate = (decimal)5.5;
            leAddlLedger.ledgerAmount = (decimal)4.13;
            leAddlLedger.isDeemedPositive = false;
            debitNote.arlLedgerEntries.Add(leAddlLedger);

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Round Off";
            leAddlLedger.ledgerAmount = (decimal)-0.13;
            leAddlLedger.isDeemedPositive = false;
            debitNote.arlLedgerEntries.Add(leAddlLedger);


            tallyResponse = tb.DoTransferVoucher(debitNote);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Voucher uploaded successfully", "Tally Bridge Tool");
            }
        }

        void btnCreditNoteInvMode_Click(object sender, EventArgs e)
        {
            CreditNote creditNote = null;
            InventoryEntry invEntry = null;
            LedgerEntry leAccAlloc = null;
            LedgerEntry lePartyLedger = null;
            LedgerEntry leAddlLedger = null;
            BillAllocation billAlloc = null;
            TallyResponse tallyResponse = null;

            creditNote = new CreditNote();
            creditNote.tallyCompanyName = "Miebach Demo Data";

            //This should be a unique id of the transaction in the external software
            creditNote.voucherForeignKey = "CN-001";

            creditNote.dtOfVoucher = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //This should be the name of the Credit Note voucher type in Tally
            creditNote.voucherTypeName = "Credit Note";

            //This should be hardcoded as Credit Note
            creditNote.typeOfVoucher = "Credit Note";

            //You can leave it blank if voucher number is configured as automatic in Tally
            creditNote.voucherNo = "1";

            //Original Invoice No
            creditNote.reference = "9324";

            //Original Invoice Date
            creditNote.referenceDate = DateTime.ParseExact("01/04/2016", "dd/MM/yyyy", null);

            //If you are not setting voucher number in code, you can specify voucherIdentifier which will appear in log messages
            creditNote.voucherIdentifier = "CN-001";

            //In case of Credit Note, Buyer is the company who is returning the goods to us
            creditNote.buyerName = "ABC India Pvt. Ltd.";
            creditNote.buyerAddress = new string[3];
            creditNote.buyerAddress[0] = "ABC - Addr Line1";
            creditNote.buyerAddress[1] = "ABC - Addr Line2";
            creditNote.buyerAddress[2] = "ABC - Addr Line3";
            creditNote.buyerState = "Karnataka";
            creditNote.buyerTINNo = "ABC - TIN1111111";
            creditNote.buyerCSTNo = "ABC - CST1111111";
            creditNote.typeOfDealer = "Regular";

            //In case of Credit Note, consignee is same as buyer
            creditNote.consigneeName = "ABC India Pvt. Ltd.";
            creditNote.consigneeAddress = new string[3];
            creditNote.consigneeAddress[0] = "ABC - Addr Line1";
            creditNote.consigneeAddress[1] = "ABC - Addr Line2";
            creditNote.consigneeAddress[2] = "ABC - Addr Line3";
            creditNote.consigneeTINNo = "ABC - TIN1111111";
            creditNote.consigneeCSTNo = "ABC - CST1111111";

            creditNote.narration = "Some Narration";
            creditNote.isInvoice = true;
            creditNote.isOptional = false;


            //1st item in invoice
            invEntry = new InventoryEntry();

            //You can give either the main name of the item, or its alias, or its part number
            invEntry.itemName = "96 Pages Maths Ruled";

            //For credit note i.e. sales returns, items should have isDeemedPositive set to true
            invEntry.isDeemedPositive = true;

            invEntry.actualQty = 10;
            invEntry.billedQty = 10;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.discountPerc = 0;

            //For credit note i.e. sales returns, item amount should be negative
            invEntry.amount = (decimal)-150;

            //Accounting Allocation for the 1st item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Sales 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            creditNote.arlInvEntries.Add(invEntry);

            //2nd item in invoice
            invEntry = new InventoryEntry();
            invEntry.itemName = "Plain Note Book";
            invEntry.isDeemedPositive = true;
            invEntry.actualQty = 3;
            invEntry.billedQty = 3;
            invEntry.qtyUnit = "nos";
            invEntry.rate = 15;
            invEntry.rateUnit = "nos";
            invEntry.amount = (decimal)-45;

            //Accounting Allocation for the 2nd item
            leAccAlloc = new LedgerEntry();
            leAccAlloc.ledgerName = "VAT Sales 5.5%";
            leAccAlloc.ledgerAmount = invEntry.amount;

            invEntry.arlAccountingAllocations.Add(leAccAlloc);
            creditNote.arlInvEntries.Add(invEntry);


            //Party Ledger
            lePartyLedger = new LedgerEntry();
            lePartyLedger.ledgerName = "ABC India Pvt. Ltd.";

            //This should be the grand total of the invoice (including VAT and any other charges) with a positive sign
            //isDeemedPositive should be set to false
            lePartyLedger.ledgerAmount = (decimal)205;
            lePartyLedger.isDeemedPositive = false;

            //Party ledger should be the 1st ledger in the invoice
            creditNote.arlLedgerEntries.Add(lePartyLedger);


            //All additional ledgers in Credit Note (Invoice Mode) i.e. Sales Returns should have isDeemedPositive set to true
            //However, if the actual amount like Output VAT is positive, the value in ledgerAmount should be negative
            //and if the actual amount like Round Off is negative, the value in ledgerAmount should be positive
            //This applies to Credit Note (Invoice Mode).
            //The behaviour for Credit Note (Voucher Mode)  is different

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Output VAT 5.5%";
            leAddlLedger.ledEntryRate = (decimal)5.5;
            leAddlLedger.ledgerAmount = (decimal)-10.73;
            leAddlLedger.isDeemedPositive = true;
            creditNote.arlLedgerEntries.Add(leAddlLedger);

            leAddlLedger = new LedgerEntry();
            leAddlLedger.ledgerName = "Round Off";
            leAddlLedger.ledgerAmount = (decimal)0.73;
            leAddlLedger.isDeemedPositive = true;
            creditNote.arlLedgerEntries.Add(leAddlLedger);


            tallyResponse = tb.DoTransferVoucher(creditNote);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Voucher uploaded successfully", "Tally Bridge Tool");
            }
        }


        void btnCustomerMaster_Click(object sender, EventArgs e)
        {
            Ledger custLedger = new Ledger();
            custLedger.tallyCompanyName = "Miebach Demo Data";

            //This line is required only if the ledger is being altered or re-uploaded. 
            //During initial ledger creation, this line is not required.
            custLedger.oldLedgerName = "ABC India Pvt. Ltd.";

            custLedger.ledgerName = "ABC India Pvt. Ltd.";

            //Mailing Name of the customer master
            custLedger.ledgerMailingName = "M/s ABC India Pvt. Ltd.";

            //Alias of the customer master
            custLedger.ledgerAlias = "C0001";

            //Parent Group of the customer master
            custLedger.parentGroupName = "Sundry Debtors";

            custLedger.address = new string[3];
            custLedger.address[0] = "ABC - Addr Line1";
            custLedger.address[1] = "ABC - Addr Line2";
            custLedger.address[2] = "ABC - Addr Line3";

            //State Name should be from the List of States available in Tally
            custLedger.state = "Karnataka";
            custLedger.pinCode = "560001";

            //Country Name should be from the List of Countries available in Tally
            custLedger.country = "India";

            custLedger.contactPerson = "Mr. X";
            custLedger.telephoneNo = "080 22222222";
            custLedger.faxNo = "080 2333 3333";
            custLedger.email = "accounts@abcindia.com";

            custLedger.tinNo = "ABC - TIN1111111";
            custLedger.cstNo = "ABC - CST1111111";
            custLedger.panNo = "ABCPAN1111";
            custLedger.serviceTaxNo = "ABCDEF";

            //Use negative amount for debit opening balance
            custLedger.openingBalance = (decimal) -200000;
            custLedger.updateOpeningBalance = true;

            //Check whether this needs to be set to true or false with the client
            custLedger.maintainBillWiseDetails = true;
            custLedger.defaultCreditPeriod = "15 days";

            TallyResponse tallyResponse = null;
            tallyResponse = tb.DoTransferLedger(custLedger);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Ledger uploaded successfully", "Tally Bridge Tool");
            }
        }

        void btnVendorMaster_Click(object sender, EventArgs e)
        {
            Ledger vendorLedger = new Ledger();
            vendorLedger.tallyCompanyName = "Miebach Demo Data";

            //This line is required only if the ledger is being altered or re-uploaded. 
            //During initial ledger creation, this line is not required.
            vendorLedger.oldLedgerName = "AK Printers Pvt. Ltd.";

            vendorLedger.ledgerName = "AK Printers Pvt. Ltd.";

            //Mailing Name of the vendor master
            vendorLedger.ledgerMailingName = "M/s AK Printers Pvt. Ltd.";

            //Alias of the vendor master
            vendorLedger.ledgerAlias = "V0001";

            //Parent Group of the vendor master
            vendorLedger.parentGroupName = "Sundry Creditors";

            vendorLedger.address = new string[3];
            vendorLedger.address[0] = "AK - Addr Line1";
            vendorLedger.address[1] = "AK - Addr Line2";
            vendorLedger.address[2] = "AK - Addr Line3";

            //State Name should be from the List of States available in Tally
            vendorLedger.state = "Karnataka";
            vendorLedger.pinCode = "560001";

            //Country Name should be from the List of Countries available in Tally
            vendorLedger.country = "India";

            vendorLedger.contactPerson = "Mr. X";
            vendorLedger.telephoneNo = "080 22222222";
            vendorLedger.faxNo = "080 2333 3333";
            vendorLedger.email = "accounts@abcindia.com";

            vendorLedger.tinNo = "ABC - TIN1111111";
            vendorLedger.cstNo = "ABC - CST1111111";
            vendorLedger.panNo = "ABCPAN1111";
            vendorLedger.serviceTaxNo = "ABCDEF";

            //Use positive amount for credit opening balance
            vendorLedger.openingBalance = (decimal)200000;
            vendorLedger.updateOpeningBalance = true;

            vendorLedger.maintainBillWiseDetails = true;
            vendorLedger.defaultCreditPeriod = "15 days";

            TallyResponse tallyResponse = null;
            tallyResponse = tb.DoTransferLedger(vendorLedger);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Ledger uploaded successfully", "Tally Bridge Tool");
            }
        }


        void btnStockItemMaster_Click(object sender, EventArgs e)
        {
            StockItem stockItem = new StockItem();
            stockItem.tallyCompanyName = "Miebach Demo Data";

            //This line is required only if the Stock Item is being altered or re-uploaded. 
            //During initial Stock Item creation, this line is not required.
            stockItem.oldItemName = "Plain Note Book";

            stockItem.itemName = "Plain Note Book";

            //You can map SKU code either in item alias or in part no.
            stockItem.itemAlias = "PNB0001";
            stockItem.partNo = "Part0001";

            //The unit master should already exist in Tally.
            stockItem.primaryUnitName = "nos";

            stockItem.description = "Enter description here, if required";
            
            //The stock group should already exist in Tally
            stockItem.stockGroupName = "Stock Group 1";

            //The stock category should already exist in Tally
            stockItem.stockCategoryName = "Stk Cat 1";

            stockItem.isVatAppl = true;

            //Opening Stock qty in primary units
            stockItem.openingQty = (decimal) 101;
            stockItem.openingRate = (decimal) 112;

            //Opening stock amount should ne negative
            stockItem.openingAmt = -11312;

            TallyResponse tallyResponse = null;
            tallyResponse = tb.DoTransferStockItem(stockItem);
            if (tallyResponse.errorCode != 0)
            {
                MessageBox.Show(tallyResponse.errorMsg, "Tally Bridge Tool");
            }
            else
            {
                MessageBox.Show("Stock Item uploaded successfully", "Tally Bridge Tool");
            }
        }


    }
}