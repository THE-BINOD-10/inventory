import os
import pandas as pd
from rest_api.views import *
from miebach_admin.models import *
import ftplib
ftp = ftplib.FTP('u213322.your-storagebox.de')
ftp.login('u213322-sub1', '7zkFCvcIzhJVs4RD')
mypath = 'Uploads'
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(os.path.join(HERE))


def make_df_from_excel(file_name, nrows):
    file_path = os.path.abspath(os.path.join(DATA_DIR, file_name))
    xl = pd.ExcelFile(file_path)
    sheetname = xl.sheet_names[0]
    df_header = pd.read_excel(file_path, sheetname=sheetname, nrows=1)
    gomech_users = ['gomechanic_admin','gomechanic_gurgaon', 'gomechanic_mumbai', 'gomechanic_bangalore']
    for username in gomech_users:
        user = User.objects.get(username=username)
        count = 0
        i_chunk = 0
        skiprows = 1
        # upload_file_skus = []
        product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
        while True:
            chunks = []
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
            data_dict = {"user":user.id}
            for index,row in df.iterrows():
                str_dict = {'hsn_code':'HSN Code', 'sku_desc':'Part Desc'}
                num_dict = {'price':'Price', 'mrp':'MRP'}
                # df.to_csv('test.csv', index=index, header=df.columns.values,  mode='a')
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
                        data_dict['product_type'] = tax_type
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
                        data_dict[key] = cell_data
                for key,value in num_dict.iteritems():
                    if row.get(value, 0):
                        cell_data = row.get(value)
                        if not isinstance(cell_data, (int, float)):
                            cell_data = int(cell_data)
                        if sku_data:
                            setattr(sku_data, key, cell_data)
                        data_dict[key] = cell_data
                if sku_data:
                    sku_data.save()
                if not sku_data:
                    sku_master = SKUMaster(**data_dict)
                    sku_master.save()
                    sku_data = sku_master
            
ftp.cwd(mypath)
names = ftp.nlst()
for name in names:
    ftp.retrbinary("RETR " + name, open(name, 'wb').write)
    existingFilepath = "Uploads/"+name
    newFilepath = "Processing/"+name
    ftp.cwd('..')
    success = ftp.rename(existingFilepath,newFilepath)
    com_existingFilepath = "Processing/"+name
    com_newFilepath = "Completed/"+name
    make_df_from_excel(name, nrows=5)
    success = ftp.rename(com_existingFilepath,com_newFilepath)
    ftp.cwd(mypath)
ftp.quit()