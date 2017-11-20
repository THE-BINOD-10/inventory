
var ENDPOINT="http://192.168.1.162:9009/";
var APIENDPOINT=ENDPOINT+"rest_api/";
var GET_SKU_MASTER_CHECKSUM_API=APIENDPOINT+"get_file_checksum/?name=sku_master";
var GET_SKUDATA_API=APIENDPOINT+"get_file_content/?name=sku_master";
var GET_CHECKSUM_CUSTOMER_API=APIENDPOINT+"get_file_checksum/?name=customer_master";
var GET_CUSTOMER_API=APIENDPOINT+"get_file_content/?name=customer_master";
var GET_CURRENT_ORDER_ID_API=ENDPOINT+"get_current_order_id/?name=customer_master";
var ADD_POS_CUSTOMER_API=ENDPOINT+"add_customer/";
var SYNC_POS_ORDERS_API=ENDPOINT+"customer_order/";