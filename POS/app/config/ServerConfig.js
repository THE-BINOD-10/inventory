var ENDPOINT="https://api.stockone.in/";
var STOCKONE = "http://beta.stockone.in/";
var APIENDPOINT=ENDPOINT+"rest_api/";
var GET_SKU_MASTER_CHECKSUM_API=APIENDPOINT+"get_file_checksum/?name=sku_master";
var GET_SKUDATA_API=APIENDPOINT+"get_file_content/?name=sku_master";
var GET_CHECKSUM_CUSTOMER_API=APIENDPOINT+"get_file_checksum/?name=customer_master";
var GET_CUSTOMER_API=APIENDPOINT+"get_file_content/?name=customer_master";
var GET_CURRENT_ORDER_ID_API=APIENDPOINT+"get_current_order_id/?name=customer_master";
var ADD_POS_CUSTOMER_API=APIENDPOINT+"add_customer/";
var SYNC_POS_ORDERS_API=APIENDPOINT+"customer_order/";
var PRE_ORDER_API=APIENDPOINT+"pre_order_data/";
var UPDATE_PRE_ORDER_STATUS_API=APIENDPOINT+"update_order_status/";
