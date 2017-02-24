import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from miebach_admin.models import *
import datetime
import shutil

def dump_user_images(source_user, dest_user, sku_codes=[]):
    path = 'static/images/'
    folder = str(dest_user)
    source_skus = SKUMaster.objects.exclude(image_url='').filter(user=source_user)
    if sku_codes:
        SKUMaster.objects.exclude(image_url='').filter(user=source_user, sku_code__in=sku_codes)
    dest_skus = SKUMaster.objects.filter(user=dest_user)
    if not os.path.exists(path + folder):
        os.makedirs(path + folder)
    src_files = os.listdir(path + str(source_user))
    for file_name in src_files:
        full_file_name = os.path.join(path + str(source_user), file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, path + folder)
    for source in source_skus:
        dump_sku = dest_skus.filter(sku_code=source.sku_code, user=dest_user)
        if dump_sku:
            image_url = source.image_url
            if 'static/images/' in source.image_url:
                 image_url = (source.image_url).replace(path + str(source_user), path + folder)
            dump_sku[0].image_url = image_url
            dump_sku[0].save()
        print source.image_url
    print 'success'


