from __future__ import unicode_literals
import os
import datetime
import json
import time
import ConfigParser
import pytz
import glob
from os import path
from PIL import Image

def image_compression(image_path):
    image_size = os.stat(image_path).st_size
    limit = 500 * 1024
    print 'Original Image Size : ' +str(image_size)
    while image_size > limit:
        image = Image.open(image_path)
        image.save(image_path, quality=35, optimize=True)
        image_size = os.stat(image_path).st_size
        print 'Compressed Image Size : ' +str(image_size)
    return True

def get_images():
    img_list = glob.glob("/root/aravind/WMS_ANGULAR_FIX_BAK/ANGULAR_WMS/app/images_bak/brand-logos/*.*")
    for full_path in img_list:
        if '.png' in full_path or '.jpg' in full_path:
            print full_path
            image_compression(full_path)
    return True
get_images()
