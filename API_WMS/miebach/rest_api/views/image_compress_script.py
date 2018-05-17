from __future__ import unicode_literals
import os
import datetime
import json
import time
import ConfigParser
import pytz
from os import path
from PIL import Image

def image_compression(image_path):
    image_size = os.stat(image_path).st_size
    limit = 1
    print 'Original Image Size : ' +str(image_size)
    while image_size > limit:
        image = Image.open(image_path)
        image.save(image_path, quality=35, optimize=True)
        image_size = os.stat(image_path).st_size
        print 'Compressed Image Size : ' +str(image_size)
    return True

def get_images():
    img_list = ['']
    img_path = ''
    for i in img_list:
        full_path = img_path + i
        image_compression(full_path)
    return True

get_images()
