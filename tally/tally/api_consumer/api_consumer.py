import requests
dns = 'http://0.0.0.0:8081/rest_api/'

def apiItemData():
	url = dns + 'GetItemMaster/';
	resp_data = requests.post(url = url, data = {})
	print resp_data.json()
	return True

def apiCustomerData():
	url = dns + 'GetCustomerMaster/';
	resp_data = requests.post(url = url, data = {})
	print resp_data.json()
	return True

def apiSupplierData():
	url = dns + 'GetSupplierMaster/';
	resp_data = requests.post(url = url, data = {})
	print resp_data.json()
	return True
print '----------------------'
apiItemData()
print '----------------------'
apiCustomerData()
print '----------------------'
apiSupplierData()
print '----------------------'