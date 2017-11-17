from __future__ import division
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm, cm 
from reportlab.platypus import Paragraph, Frame, PageTemplate, SimpleDocTemplate, BaseDocTemplate, PageBreak, Spacer, KeepTogether
from reportlab.graphics import barcode
from reportlab.graphics.barcode import createBarcodeDrawing, code39, code128, code93
from reportlab.graphics.barcode import eanbc, qr, usps
from reportlab.lib.pagesizes import *
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
pdfmetrics.registerFont(TTFont('Arial', '%s/static/fonts/arial.ttf' % (settings.BASE_DIR)))
# Campus Sutra Details
'''
data_dict = [{'customer': 'Adom',
	     'info': [{ 'Label': '32423098371234567890',
			  'SKUCode': '32423098371234567890',
			  'SKUPrintQty': '1',
			  'Vendor SKU': 'Vendor SKU Desc',
			  'PO No': '6309-11',
			  'MRP': '100/-',
			  'Size': 'M',
			  'Gender': 'Male',
			  'Qty': 'qunatity',
			  'MFD': '',
			  'Manufactured By': 'No. 5, 80 Feet Main Road, 4th Block, Near Maharaja Hotel, Koramangala, Bengaluru, Karnataka 560034',
			  'Color': 'Blue',
			  'Phone': '9066720134',
			  'Email': 'asubhash50@gmail.com',
			  'Brand': 'brand',
			  'marketed By': 'marketed By',
			  'Contact No': 'Contact Desc',
			  'Product': 'Product Desc'},

		    ],
		'type': 1,
                'show_fields': ['SKUCode', 'Product', ['Size', 'Gender', 'Qty', 'Color'], ['Phone', 'Email']], #Give nested list if u need multiple columns in same line
                'rows_columns' : (1,1),
                'styles' : {'leftIndent': 4, 'spaceAfter': 4, 'spaceBefore': 4, 'fontName': 'Arial', 'fontSize': 6, 'spaceShrinkage': 12, 'leading': 9, 'showBoundary': 0.1, 'rightIndent': 0, 'margin': (0, 10, 0, 5)},
		},
                ]

'''
customer_styles = {'default': {'leftIndent': 4, 'spaceAfter': 4, 'spaceBefore': 4, 'fontName': 'Arial', 'fontSize': 8, 'spaceShrinkage': 10, 'leading': 8, 'showBoundary': 0.1, 'rightIndent': 0},
		  }
bar_width = 0.7
bar_height = 25 

def get_customer_styles(data_dict):
    customer = data_dict.get('customer', 'default')
    styles   = getSampleStyleSheet() 
    customer_style = data_dict.get('styles', customer_styles.get('default', '')) #customer_styles.get(customer, customer_styles.get('default'))
    styles['Normal'].leftIndent = customer_style['leftIndent']
    styles['Normal'].spaceAfter = customer_style['spaceAfter']
    styles['Normal'].spaceBefore= customer_style['spaceBefore']
    styles['Normal'].fontName   = customer_style['fontName']
    styles['Normal'].fontSize   = customer_style['fontSize']
    styles['Normal'].spaceShrinkage = customer_style['spaceShrinkage']
    styles['Normal'].leading    = customer_style['leading']
    styles['Normal'].showBoundary = customer_style['showBoundary']
    styles['Normal'].rightIndent = customer_style['rightIndent']
    styles['Normal'].wordWrap = "LTR"
    styles['Normal'].alignment = 0
    styles['Normal'].justifyLastLine = 1
    styles['Normal'].justifyBreaks = 1

    return styles

def get_paragraph(data={}, fields=[]):

    phrases = []
    for field in fields:
        if isinstance(field, list):
            phrases.append("&nbsp;&nbsp;&nbsp;&nbsp;".join(["%s: %s" % (str(i), data.get(i, '')) for i in field]))
        elif isinstance(field, tuple):
            phrases.append("%s: %s" % (str(field[1]) , data.get(field[0])))
        elif "/" in field:
            field = field.split("/")
            phrases.append("%s: %s" % (str(field[1]) , data.get(field[0])))
        else:
            if "," in data.get(field, ''): 
                phrases.append("%s: %s" % (str(field) , data.get(field).replace(",", ", \n")))
            else:
                phrases.append("%s: %s" % (str(field) , data.get(field)))

    return phrases

def get_barcodes1(data_dict):
    data_dict.update({'file_name': "%s/static/barcodes/%s_barcodes.pdf" %  (settings.BASE_DIR, data_dict.get('customer', 'stockone'))})
    style = get_customer_styles(data_dict)['Normal']
    size = data_dict.get('size', (60,30))
    rows = data_dict.get('rows_columns', (1,1))

    vertical = data_dict.get('styles').get('vertical', 0)
    rotation = 270 if vertical else 0
    if vertical:
        doc = BaseDocTemplate(data_dict['file_name'], pagesize=(size[1]*mm*rows[1], size[0]*mm*rows[0]), pageTemplates=[], leftMargin=0*mm, topMargin=5*mm, bottomMargin=2*mm, rotation=rotation)
    else:
        doc = BaseDocTemplate(data_dict['file_name'], pagesize=(size[0]*mm*rows[1], size[1]*mm*rows[0]), pageTemplates=[], leftMargin=5*mm, topMargin=5*mm, bottomMargin=2*mm, rotation=rotation)
    story, page_frames, frames, pages = [], [], [], []
    prev_width, prev_height = 0, 0
    width, height = 0, 2
    items = 1
    for data in data_dict.get('info', []):
        data['width'], data['height'] = size[0]*mm, size[1]*mm
        
        for qty in range(int(data.get('SKUPrintQty', 1))):
           
            f = Frame(prev_width*mm, prev_height*mm, data['width'], data['height'],  showBoundary=0.1, leftPadding=2*mm, rightPadding=0, topPadding=2*mm, bottomPadding=0)
            code = code128.Code128(data['Label'],  humanReadable=1, barWidth=bar_width,  barHeight=bar_height,  fontSize=style.fontSize, lquiet=0)
            lquiet =  data['width'] - code.width
            code.lquiet = lquiet/2 if lquiet > 0 else 0

            story.append(code)
            story.append(Spacer(2*mm, 2*mm))
            paras = []
            for i in get_paragraph(data, data_dict.get('show_fields', [])):
                '''
                if "Manufactured By" in i:
                    story.append(Paragraph("<br/>".join(paras), style))
                    paras = []
                    story.append(Paragraph(i, style))
                else:
                '''
                paras.append(i)
            if paras:
                story.append(Paragraph("<br/>".join(paras), style))

            frames.append(f)
            page_frames.append(f)
            if (items)%rows[1] == 0:
                story.append(PageBreak())
                pages.append(PageTemplate('normal',frames=page_frames))
                page_frames = []
                items = 1
            else:
                prev_width += size[0]
                items += 1

    doc.addPageTemplates(pages)
    doc.build(story)
    return data_dict['file_name'].replace(settings.BASE_DIR, '').strip('/')
def myFirstPage(canvas, doc):
            canvas.saveState()
            canvas.rotate(90)
            canvas.restoreState()


def myLaterPages(canvas, doc):
            canvas.saveState()
            canvas.rotate(90)
            canvas.restoreState()
