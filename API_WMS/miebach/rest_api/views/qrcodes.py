import json
import ast
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
# from miebach_admin.models import QrCodeSettings
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm

# Create your views here.
def generate_qr(user='', data_list=None, display_dict=None, qr_name=''):
    """
    Creating QR Code and embed in a PDF
    """
    if not data_list:
        data_list = []
    if not display_dict:
        display_dict = {}
    show_fields = []
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename="qrcodes.pdf"'
    c = canvas.Canvas(response)
    c.setFont("Times-Roman", 10)
    c.setFontSize(5)
    total_text_height = 0
    page_width = 130
    page_height = 130
    text_height_space = 10
    qr_width = 130
    qr_height = 130
    qr_position = 0
    # qr_obj = QrCodeSettings.objects.filter(user=user.id, qr_name=qr_name)
    page_properties =  '(100,60)'
    qr_code_properties = '(25, 25, 10)'
    # if qr_obj.exists():
    # qr_obj = qr_obj[0]
    page_sizes = ast.literal_eval(page_properties)
    qr_code_sizes = ast.literal_eval(qr_code_properties)
    if len(page_sizes) == 2:
        page_width = page_sizes[0] * mm
        page_height = page_sizes[1] * mm
    if len(qr_code_sizes) == 3:
        qr_width = qr_code_sizes[0] * mm
        qr_height = qr_code_sizes[1] * mm
        qr_position = qr_code_sizes[2] * mm
    show_fields = ast.literal_eval("[{'mapping':0,'mapping_type':'address','x':2,'y':5,'text':'Metropolise Health care' , 'font_size':4},{'mapping': 1,'mapping_type': 'supplier_id','x': 2,'y': 9,'text': ' ','extra_text': '','font_size': 4},{'mapping':1,'mapping_type':'po_num','x':2,'y':42,'text': '','name': 'ASN Number: ', 'font_size': 4},{'mapping': 1,'mapping_type': 'asn_number','x': 2,'y': 35,'text': ' ','name': 'ASN Number: ','font_size': 4},{'mapping': 1,'mapping_type': 'asn_date','x': 2,'y': 47,'text': ' ','extra_text': '','font_size': 4}]")

    if display_dict:
        total_text_height += (len(display_dict.keys())*text_height_space)
    page_height += total_text_height
    qr_left_position = 0
    qr_bottom_position = total_text_height
    font_size = 8
    c.setPageSize((page_width, page_height))
    exclude_keys = ['image', 'qr_data', 'supplier_id', 'supplier_name', 'asn_date', 'po_num']
    for data_dict in data_list:
        c.setFont("Times-Roman", 10)
        if data_dict.get('qr_data',False):
            scan_obj = data_dict.copy()
            exclude_keys = [i for i in exclude_keys if i in scan_obj.keys()]
            for key in exclude_keys:
                del scan_obj[key]
            scanned_data = json.dumps(scan_obj)

        else:
            scanned_data = data_dict.get('asn_number')
        qr_code = qr.QrCodeWidget(scanned_data)
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing(45, 0, transform=[qr_width / width, 0, 0,
                                      qr_height / height,
                                      qr_left_position, qr_bottom_position])
        d.add(qr_code)
        renderPDF.draw(d, c, 0, qr_position)
        height_val = 5
        for display_key, display_val in display_dict.iteritems():
            c.setFontSize(font_size)
            c.drawString(15, height_val, '%s: %s' %
                         (display_key, str(data_dict.get(display_val, '1'))))
            height_val += text_height_space
            
        for obj in show_fields:
            x_value = obj.get('x') * mm
            y_value = obj.get('y') * mm
            data = obj.get('text', '')
            font_size = obj.get('font_size', 10) * mm
            extra_text = obj.get('extra_text','')
            field_name = obj.get('name', '')
            if obj.get('mapping', 0):
                if obj.get('mapping_type') == 'image':
                    logo = ImageReader(data_dict.get(obj.get('mapping_type')))
                    width = obj.get("width") if obj.get('width') else 60
                    height = obj.get("height") if  obj.get('height') else 35
                    c.drawImage(logo, x_value, y_value, width, height)
                else:
                    data = data_dict.get(obj.get('mapping_type'), '')
                    c.setFontSize(font_size)
                    if isinstance(data, list):
                        for item in data:
                            c.drawString(x_value, y_value, str(item))
                            y_value -= 5 * mm
                    else:
                        display_text = str(name)+str(data)+str(extra_text)
                        c.drawString(x_value, y_value,display_text)
            else:
                c.setFontSize(font_size)
                if '\n' in data:
                    texts = data.split('\n')
                    y_param = y_value
                    for text in texts:
                        c.drawString(x_value, y_param, text)
                        y_param -= 2 * mm
                else:
                    c.drawString(x_value, y_value, data)
        c.save()

    return response
