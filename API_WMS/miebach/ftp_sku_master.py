import os
import pandas as pd
from rest_api.views import *
from miebach_admin.models import *

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(os.path.join(HERE))


def make_df_from_excel(file_name, nrows):
    file_path = os.path.abspath(os.path.join(DATA_DIR, file_name))
    xl = pd.ExcelFile(file_path)
    sheetname = xl.sheet_names[0]
    df_header = pd.read_excel(file_path, sheetname=sheetname, nrows=1)
    user = User.objects.get(username='demo')
    chunks = []
    i_chunk = 0
    skiprows = 1
    # upload_file_skus = []
    product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
    while True:
        df_chunk = pd.read_excel(
            file_path, sheetname=sheetname,
            nrows=nrows, skiprows=skiprows, header=None)
        skiprows += nrows
        if not df_chunk.shape[0]:
            break
        else:
            chunks.append(df_chunk)
        i_chunk += 1

        df_chunks = pd.concat(chunks)
        columns = {i: col for i, col in enumerate(df_header.columns.tolist())}
        df_chunks.rename(columns=columns, inplace=True)
        df = pd.concat([df_header, df_chunks])
        data_dict = {}
        for index,row in df.iterrows():
            str_dict = {'hsn_code':'HSN Code', 'sku_desc':'Part Desc'}
            num_dict = {'price':'Price', 'mrp':'MRP'}
            if row.get('Part No', ''):
                sku_code = row.get('Part No')
                if isinstance(sku_code, float):
                    sku_code = str(int(sku_code))
                # if sku_code in upload_file_skus:
                #     index_status.setdefault(row_idx, set()).add('Duplicate SKU Code found in File')
                # else:
                #     upload_file_skus.append(sku_code)
                wms_code = sku_code
                data_dict['sku_code'] = wms_code
                data_dict['wms_code'] = wms_code
                if wms_code:
                    sku_data = SKUMaster.objects.filter(user=user.id, sku_code=wms_code)
                    if sku_data:
                        sku_data = sku_data[0]
            if row.get('TAX', ''):
                tax_type = row.get('TAX')
                if isinstance(tax_type, (int, float)):
                    tax_type = 'Tax-'+str(int(tax_type))
                if tax_type in product_types:
                    if sku_data:
                        sku_data.tax_type = tax_type
                    data_dict['tax_type'] = tax_type
                # if tax_type not in product_types:
                #     index_status.setdefault(row_idx, set()).add(
                #         'Product Type should match with Tax master product type')
            for key,value in str_dict.iteritems():
                if row.get(value, ''):
                    cell_data = row.get(value)
                    if isinstance(cell_data, (int, float)):
                        cell_data = str(int(cell_data))
                    if sku_data:
                        setattr(sku_data, key, cell_data)
                    data_dict[value] = cell_data
            if sku_data:
                sku_data.save()
            if not sku_data:
                sku_master = SKUMaster(**data_dict)
                sku_master.save()
                sku_data = sku_master
            
if __name__ == '__main__':
    df = make_df_from_excel('PRICE _LIST _TOYOTA-2020.xlsx', nrows=5)