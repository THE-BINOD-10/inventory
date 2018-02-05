from __future__ import division
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, mm, cm
from reportlab.platypus import Paragraph, Frame, PageTemplate, BaseDocTemplate, PageBreak, Spacer
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import *
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
			  'Manufactured By': 'No. 5, 80 Feet Main Road, 4th Block,\
                                              Near Maharaja Hotel, Koramangala,\
                                              Bengaluru, Karnataka 560034',
			  'Color': 'Blue',
			  'Phone': '9066720134',
			  'Email': 'asubhash50@gmail.com',
			  'Brand': 'brand',
			  'marketed By': 'marketed By',
			  'Contact No': 'Contact Desc',
			  'Product': 'Product Desc'},

		    ],
		'type': 1,
                'show_fields': ['SKUCode', 'Product', ['Size', 'Gender', 'Qty', 'Color'],\
                               ['Phone', 'Email']], #Give nested list if u need multiple columns in same line
                'rows_columns' : (1,1),
                'styles' : {'leftIndent': 4, 'spaceAfter': 4, 'spaceBefore': 4, 'fontName': 'Arial',\
                            'fontSize': 6, 'spaceShrinkage': 12, 'leading': 9, 'showBoundary': 0.1,\
                            'rightIndent': 0, 'margin': (0, 10, 0, 5)},

                'format_type': 'format1_A4',
		},
                ]
'''


def get_customer_styles(data_dict):
    '''Creating style object for paragraph'''

    customer = data_dict.get('customer', 'default')
    styles = getSampleStyleSheet()
    customer_style = data_dict.get('styles', {})
    styles['Normal'].leftIndent = customer_style['leftIndent']
    styles['Normal'].spaceAfter = customer_style['spaceAfter']
    styles['Normal'].spaceBefore = customer_style['spaceBefore']
    styles['Normal'].fontName = customer_style['fontName']
    styles['Normal'].fontSize = customer_style['fontSize']
    styles['Normal'].alignment = 0
    styles['Normal'].wordWrap = "LTR"
    styles['Normal'].spaceShrinkage = customer_style['spaceShrinkage']
    styles['Normal'].leading = customer_style['leading']
    styles['Normal'].showBoundary = customer_style['showBoundary']
    styles['Normal'].rightIndent = customer_style['rightIndent']
    styles['Normal'].justifyBreaks = 1
    styles['Normal'].justifyLastLine = 1
    return styles


def get_paragraph(data={}, fields=[]):
    phrases = []
    for field in fields:

        if 'SKUPrintQty' in field:
            val = 1
            if data.has_key('Qty'):
                val = data.get('Qty', 1)
            if "/" in field:
                phrases.append("%s: %s" % (str(field.split("/")[1]), str(val)))
            else:
                phrases.append("%s: %s" % (str(field), str(val)))
            continue

        if isinstance(field, list):
            nw_phs = []
            for i in field:
                if "/" in i:
                    i = i.split("/")
                    v = 1 if 'SKUPrintQty' in i else data.get(i[0], '')
                    v = data.get('Qty', 1) if 'SKUPrintQty' in i and data.has_key('Qty') else data.get(i[0], '')
                    nw_phs.append("%s: %s" % (str(i[1]), v))
                else:
                    nw_phs.append("%s: %s" % (str(i), data.get(i)))

            phrases.append("&nbsp;&nbsp;&nbsp;&nbsp;".join(nw_phs))

        elif isinstance(field, tuple):
            phrases.append("%s: %s" % (str(field[1]), data.get(field[0])))
        elif "/" in field:
            field = field.split("/")
            phrases.append("%s: %s" % (str(field[1]), data.get(field[0])))
        else:
            if "," in data.get(field, ''):
                phrases.append("%s: %s" % (str(field), data.get(field).replace(",", ", \n")))
            else:
                phrases.append("%s: %s" % (str(field), data.get(field)))
    return phrases


def get_barcodes(data_dict):
    data_dict.update({'file_name': "%s/static/barcodes/%s_barcodes.pdf" % (
    settings.BASE_DIR, data_dict.get('customer', 'stockone'))})

    style = get_customer_styles(data_dict)['Normal']
    size = data_dict.get('size', (60, 30))
    rows = data_dict.get('rows_columns', (1, 1))
    pdf_format = data_dict.get('format_type', '')
    paper = data_dict.get('styles').get('paper', '')
    vertical = data_dict.get('styles').get('vertical', 0)
    rotation = 90 if vertical else 0

    if paper:
        pagesize = eval(paper) if isinstance(paper, str) else paper
    elif vertical == 1:
        pagesize = (size[1] * mm * rows[1], size[0] * mm * rows[0])
    else:
        pagesize = (size[0] * mm * rows[1], size[1] * mm * rows[0])

    doc = BaseDocTemplate(data_dict['file_name'], pagesize=pagesize, pageTemplates=[], \
                          leftMargin=0.6 * mm, topMargin=0.5 * mm, bottomMargin=2 * mm, rotation=rotation)

    story, page_frames, frames, pages = [], [], [], []
    width, height, row_items, column_items = 0, 2, 1, 1
    prev_width, prev_height = data_dict.get('styles').get('MarginTop', 0), data_dict.get('styles').get('MarginLeft', 0)

    for data in data_dict.get('info', []):
        '''Iterating On all SKU objects'''

        data['width'], data['height'] = size[0] * mm, size[1] * mm

        iter_qty = 1 if data.has_key('Qty') else data.get('SKUPrintQty', 1)
        for qty in range(int(iter_qty)):
            '''Checking and iterating on SKUPrintQty then qty should be one else bulk qty will be printed'''

            f = Frame(prev_width * mm, prev_height * mm, data['width'], data['height'], \
                      showBoundary=data_dict.get('styles').get('showBoundary', 0), \
                      leftPadding=2 * mm, rightPadding=0, topPadding=2 * mm, bottomPadding=0)

            code = code128.Code128(data['Label'], humanReadable=1,
                                   barWidth=data_dict.get('styles', {}).get('BarWidth', 0.7), \
                                   barHeight=data_dict.get('styles', {}).get('BarHeight', 25), \
                                   fontSize=style.fontSize, lquiet=0)

            lquiet = data['width'] - code.width
            code.lquiet = lquiet / 2 if lquiet > 0 else 0
            code.lquiet += f.leftPadding

            story.append(code)
            story.append(Spacer(2 * mm, 2 * mm))

            paras = [i for i in get_paragraph(data, data_dict.get('show_fields', []))]
            if paras:
                story.append(Paragraph("<br/>".join(paras), style))

            frames.append(f)
            page_frames.append(f)

            """
            if paper == '':
                '''Page completely filled with items'''

                story.append(PageBreak())
                pages.append(PageTemplate('normal', frames=page_frames))
                page_frames = []
                continue
            """

            if column_items % rows[0] == 0:
                '''Row is completely filled and started new Row'''
                prev_height = data_dict.get('styles').get('MarginLeft', 0)
                column_items = 1
            else:
                prev_height += size[1]
                prev_height += data_dict.get('styles').get('HorizontalMiddleSpace', 0)
                column_items += 1
                continue

            if (row_items) % rows[1] == 0:
                story.append(PageBreak())
                pages.append(PageTemplate('normal', frames=page_frames))
                page_frames = []
                row_items = 1
            else:
                '''Column is completely filled and started new column'''

                prev_width += size[0]
                prev_height = data_dict.get('styles').get('MarginLeft', 0)
                prev_width += data_dict.get('styles').get('VerticalMiddleSpace', 0)
                row_items += 1

    if page_frames:
        pages.append(PageTemplate('normal', frames=page_frames))
    doc.addPageTemplates(pages)
    try:
        doc.build(story)
    except:
        import traceback
        print traceback.format_exc()
        return "Failed"

    if data_dict['file_name'].startswith("./"):
        url = data_dict['file_name'].lstrip("./")
    else:
        url = data_dict['file_name'].replace(settings.BASE_DIR, '').strip('/')
    return url
