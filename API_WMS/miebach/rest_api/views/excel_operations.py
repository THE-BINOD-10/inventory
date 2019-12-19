from xlwt import easyxf
from rest_api.views.common import get_work_sheet
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()


def write_excel_col(ws, row_count, column_count, value, bold=False):
    if bold:
        header_style = easyxf('font: bold on')
        ws.write(row_count, column_count, value, header_style)
    else:
        ws.write(row_count, column_count, value)
    column_count += 1
    return ws, column_count


def get_excel_variables(file_name, sheet_name, headers, headers_index=0):
    wb, ws = get_work_sheet(sheet_name, headers, headers_index=headers_index)
    file_name = '%s.%s' % (file_name, 'xls')
    path = 'static/excel_files/%s' % file_name
    if not os.path.exists('static/excel_files/'):
        os.makedirs('static/excel_files/')
    return wb, ws, path, file_name
