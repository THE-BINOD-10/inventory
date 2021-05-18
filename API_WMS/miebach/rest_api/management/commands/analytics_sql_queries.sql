CREATE TABLE `ANALYTICS_GRN` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `grn_number` varchar(32) NOT NULL,
  `grn_date` datetime(6) DEFAULT NULL,
  `invoice_date` date DEFAULT NULL,
  `invoice_number` varchar(64) NOT NULL,
  `grn_user` varchar(128) NOT NULL,
  `zone` varchar(64) NOT NULL,
  `plant_code` varchar(64) NOT NULL,
  `plant_name` varchar(128) NOT NULL,
  `department_name` varchar(128) NOT NULL,
  `department_code` varchar(64) NOT NULL,
  `supplier_id` varchar(128) NOT NULL,
  `supplier_name` varchar(256) NOT NULL,
  `supplier_state` varchar(64) NOT NULL,
  `supplier_country` varchar(64) NOT NULL,
  `supplier_gst_number` varchar(64) NOT NULL,
  `sku_code` varchar(128) NOT NULL,
  `sku_desc` varchar(350) NOT NULL,
  `sku_category` varchar(128) NOT NULL,
  `sku_class` varchar(64) NOT NULL,
  `sku_brand` varchar(64) NOT NULL,
  `hsn_code` varchar(20) NOT NULL,
  `sgst_tax` double NOT NULL,
  `cgst_tax` double NOT NULL,
  `igst_tax` double NOT NULL,
  `cess_tax` double NOT NULL,
  `price` double NOT NULL,
  `base_quantity` double NOT NULL,
  `base_uom` varchar(64) NOT NULL,
  `pquantity` double NOT NULL,
  `puom` varchar(64) NOT NULL,
  `pcf` double NOT NULL,
  `overall_discount` double NOT NULL,
  `tcs_value` double NOT NULL,
  `remarks` varchar(64) NOT NULL,
  `challan_number` varchar(64) NOT NULL,
  `challan_date` date DEFAULT NULL,
  `discount_percent` double NOT NULL,
  `round_off_total` double NOT NULL,
  `invoice_value` double NOT NULL,
  `invoice_quantity` double NOT NULL,
  `invoice_receipt_date` date DEFAULT NULL,
  `credit_type` varchar(32) NOT NULL,
  `credit_status` int NOT NULL,
  `batch_no` varchar(64) NOT NULL,
  `mrp` double NOT NULL,
  `manufactured_date` date DEFAULT NULL,
  `expiry_date` date DEFAULT NULL,
  `status` int NOT NULL,
  `creation_date` datetime(6) NOT NULL,
  `updation_date` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ANALYTICS_GRN_grn_number_a2fe0375` (`grn_number`),
  KEY `ANALYTICS_GRN_plant_code_37228d7b` (`plant_code`),
  KEY `ANALYTICS_GRN_sku_code_99776544` (`sku_code`),
  KEY `ANALYTICS_GRN_hsn_code_2a972767` (`hsn_code`)
)


CREATE TABLE `ANALYTICS_PURCHASE_ORDER` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `po_id` bigint DEFAULT NULL,
  `full_po_number` varchar(32) NOT NULL,
  `po_date` datetime(6) DEFAULT NULL,
  `po_raised_date` datetime(6) DEFAULT NULL,
  `requested_user` varchar(128) NOT NULL,
  `wh_user` varchar(128) NOT NULL,
  `zone` varchar(64) NOT NULL,
  `plant_code` varchar(64) NOT NULL,
  `plant_name` varchar(128) NOT NULL,
  `department_name` varchar(128) NOT NULL,
  `department_code` varchar(64) NOT NULL,
  `sku_code` varchar(128) NOT NULL,
  `sku_desc` varchar(350) NOT NULL,
  `sku_category` varchar(128) NOT NULL,
  `sku_class` varchar(64) NOT NULL,
  `sku_brand` varchar(64) NOT NULL,
  `hsn_code` varchar(20) NOT NULL,
  `supplier_id` varchar(128) NOT NULL,
  `supplier_name` varchar(256) NOT NULL,
  `supplier_state` varchar(64) NOT NULL,
  `supplier_country` varchar(64) NOT NULL,
  `supplier_gst_number` varchar(64) NOT NULL,
  `payment_terms` varchar(256) NOT NULL,
  `sgst_tax` double NOT NULL,
  `cgst_tax` double NOT NULL,
  `igst_tax` double NOT NULL,
  `cess_tax` double NOT NULL,
  `price` double NOT NULL,
  `received_quantity` double NOT NULL,
  `base_quantity` double NOT NULL,
  `base_uom` varchar(64) NOT NULL,
  `pquantity` double NOT NULL,
  `puom` varchar(64) NOT NULL,
  `pcf` double NOT NULL,
  `currency` longtext NOT NULL,
  `currency_internal_id` int NOT NULL,
  `currency_rate` double NOT NULL,
  `pending_at` varchar(1024) NOT NULL,
  `po_status` varchar(64) NOT NULL,
  `final_status` varchar(64) NOT NULL,
  `delivery_date` date DEFAULT NULL,
  `creation_date` datetime(6) NOT NULL,
  `updation_date` datetime(6) NOT NULL,
  `analytics_grn_id` int DEFAULT NULL,
  PRIMARY KEY (`id`)
)



 CREATE TABLE `ANALYTICS_PURCHASE_REQUEST` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `full_pr_number` varchar(32) NOT NULL,
  `pr_date` datetime(6) DEFAULT NULL,
  `requested_user` varchar(128) NOT NULL,
  `wh_user` varchar(128) NOT NULL,
  `zone` varchar(64) NOT NULL,
  `plant_code` varchar(64) NOT NULL,
  `plant_name` varchar(128) NOT NULL,
  `department_name` varchar(128) NOT NULL,
  `department_code` varchar(64) NOT NULL,
  `sku_code` varchar(128) NOT NULL,
  `sku_desc` varchar(350) NOT NULL,
  `sku_category` varchar(128) NOT NULL,
  `sku_class` varchar(64) NOT NULL,
  `sku_brand` varchar(64) NOT NULL,
  `hsn_code` varchar(20) NOT NULL,
  `supplier_id` varchar(128) NOT NULL,
  `supplier_name` varchar(256) NOT NULL,
  `supplier_state` varchar(64) NOT NULL,
  `supplier_country` varchar(64) NOT NULL,
  `supplier_gst_number` varchar(64) NOT NULL,
  `sgst_tax` double NOT NULL,
  `cgst_tax` double NOT NULL,
  `igst_tax` double NOT NULL,
  `cess_tax` double NOT NULL,
  `price` double NOT NULL,
  `base_quantity` double NOT NULL,
  `base_uom` varchar(64) NOT NULL,
  `pquantity` double NOT NULL,
  `puom` varchar(64) NOT NULL,
  `pcf` double NOT NULL,
  `pending_at` varchar(1024) NOT NULL,
  `final_status` varchar(64) NOT NULL,
  `delivery_date` date DEFAULT NULL,
  `priority_type` varchar(64) NOT NULL,
  `creation_date` datetime(6) NOT NULL,
  `updation_date` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
);



CREATE TABLE `ANALYTICS_PURCHASE_REQUEST_purchase_orders` (`id` bigint NOT NULL AUTO_INCREMENT,
  `analyticspurchaserequest_id` int NOT NULL,
  `analyticspurchaseorder_id` int NOT NULL,
  PRIMARY KEY (`id`))