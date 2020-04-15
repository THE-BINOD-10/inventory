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


def validate_(df, file_split,file_name):
    df['error_status'] = df.isna().dot(df.columns + '-should not be empty, ').str.rstrip(', ')
    price_check=pd.to_numeric(df.Price, errors='coerce')
    df['price_status'] = price_check.isna()
    price_dict = {False: 'Price Must Be Number', True: ''}
    df['price_status'] = df['price_status'].replace(price_dict)

    mrp_check=pd.to_numeric(df.MRP, errors='coerce')
    df['mrp_status'] = mrp_check.isna()
    mrp_dict = {True: 'MRP Must Be Number', False: ''}
    df['mrp_status'] = df['mrp_status'].replace(mrp_dict)

    if len(set(df['error_status'])) > 1 or len(set(df['mrp_status'])) > 1 or  len(set(df['price_status'])) >1 :
        send_mail(mail_id, 'FTP file Upload', wrapper %("SKU Upload Failed for the file "+file_name))
        if 'xl' in file_split[1]:
            _file_name = file_split[0]+'_error.xlsx'
            df.to_excel(_file_name)
        else:
            _file_name = file_split[0]+'_error.csv'
            df.to_csv(_file_name)
        file = open(_file_name,'rb')
        ftp.cwd('Failed')
        ftp.storbinary(('STOR %s')%_file_name, file)
        ftp.cwd('..')
        ftp.cwd('Processing')
        ftp.delete(file_name)
        ftp.cwd('..')
        file.close()
        return False
    else:
        return True

def validate_sku_code(df):
    sku_code = df['Part No']
    if isinstance(df['Part No'], float):
        sku_code = str(int(df['Part No']))
    sku_code = str(sku_code)
    sku_code = sku_code.lstrip()
    sku_code = sku_code.rstrip()
    if df['Brand'].lower() == 'toyota':
        if len(sku_code) > 10 :
            if isinstance(sku_code[10], int):
                return sku_code[:10]
            else:
                return sku_code[:11]
        else:
            return sku_code
    elif df['Brand'].lower() == 'honda':
        if len(sku_code) >= 8 :
            sku_code = sku_code[:5]+'-'+sku_code[5:8]+'-'+sku_code[8:]
            return sku_code
        else:
            return sku_code
    elif df['Brand'].upper() == 'MGP':
        if len(sku_code) >= 10:
            sku_code = sku_code[:5]+'-'+sku_code[5:]
            return sku_code
        else:
            sku_code = sku_code[:11]+'-'+sku_code[11:]
            return sku_code
    else:
        return sku_code

def make_df_from_excel(file_name, nrows):
    file_path = os.path.abspath(os.path.join(DATA_DIR, file_name))
    # xl = pd.ExcelFile(file_path)
    # sheetname = xl.sheet_names[0]
    file_split = file_name.split('.')
    if 'xl' in file_split[1]:
        df_header = pd.read_excel(file_path, nrows=1)
        df = pd.read_excel(file_path)
    else:
        df_header = pd.read_csv(file_path, nrows=1)
        df = pd.read_csv(file_path)
    st = validate_(df,file_split,file_name)
    if not st:
        return False
    gomech_users = ['GM_admin', 'GM_BOM', 'GM_DEL', 'GM_BLR']
    for username in gomech_users:
        print(username)
        user = User.objects.get(username=username)
        count = 0
        i_chunk = 0
        skiprows = 1
        # upload_file_skus = []
        product_types = list(TaxMaster.objects.filter(user_id=user.id).values_list('product_type', flat=True).distinct())
        while True:
            chunks = []
            try:
                df_chunk = pd.read_excel(file_path,nrows=nrows, skiprows=skiprows, header=None)
            except:
                df_chunk = pd.read_csv(file_path,nrows=nrows, skiprows=skiprows, header=None)
            skiprows += nrows
            if not df_chunk.shape[0]:
                break
            else:
                chunks.append(df_chunk)
            i_chunk += 1

            df_chunks = pd.concat(chunks)
            columns = {i: col for i, col in enumerate(df_header.columns.tolist())}
            df_chunks.rename(columns=columns, inplace=True)
            # df = pd.concat([df_header, df_chunks])
            df_chunks['sku_code']=df_chunks.apply(validate_sku_code,axis=1)
            data_dict = {"user":user.id}
            for index,row in df_chunks.iterrows():
                count += 1
                print(count)
                str_dict = {'hsn_code':'HSN Code', 'sku_desc':'Part Desc','sku_brand':'Brand'}
                num_dict = {'price':'Price', 'mrp':'MRP'}
                if row.get('Part No', ''):
                    sku_code = row.get('Part No')
                    if isinstance(sku_code, float):
                        sku_code = str(int(sku_code))
                    sku_code = str(xcode(sku_code))
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
    return True
            
ftp.cwd(mypath)
wrapper = """<html>
    <head>
    </head>
    <body><p>%s</p></body>
    </html>"""
names = ftp.nlst()
mail_id = ['avinash@mieone.com','imran@mieone.com']
for name in names:
    ftp.retrbinary("RETR " + name, open(name, 'wb').write)
    existingFilepath = "Uploads/"+name
    newFilepath = "Processing/"+name
    send_mail(mail_id, 'FTP file Upload', wrapper %("SKU Upload started for the file "+name))
    ftp.cwd('..')
    success = ftp.rename(existingFilepath,newFilepath)
    com_existingFilepath = "Processing/"+name
    com_newFilepath = "Completed/"+name
    status = make_df_from_excel(name, nrows=10000)
    if status:
        send_mail(mail_id, 'FTP file Upload', wrapper %("SKU Upload Completed for the file "+name))
        os.remove(name)
        success = ftp.rename(com_existingFilepath,com_newFilepath)
    ftp.cwd(mypath)
ftp.quit()