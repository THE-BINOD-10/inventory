from xlrd import open_workbook
import MySQLdb

wms_list = []
conn = MySQLdb.connect(user='root', host='localhost', passwd='Hdrn^Miebach@', db='SELLERWORX_WMS')
cursor = conn.cursor()
open_book = open_workbook('1.inventory_form.xls')
open_sheet = open_book.sheet_by_index(0)

wms_index = 2
location_index = 3
for row_idx in range(1, open_sheet.nrows):
    wms_code = open_sheet.cell(row_idx, wms_index).value
    location = open_sheet.cell(row_idx, location_index).value
    if wms_code in wms_list:
        continue

    wms_list.append(wms_code)

    cursor.execute('select zone_id from LOCATION_MASTER where location=%s', (location, ))
    zone_id = cursor.fetchone()[0]

    cursor.execute('update SKU_MASTER set zone_id=%s where wms_code="%s"', (zone_id, wms_code))


conn.commit()
conn.close()
