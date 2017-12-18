import os

import json
import hashlib
import datetime

from miebach_admin.models import *


def text_file_creator(user, path, data, dump_name):
   if not os.path.exists(path):
      os.makedirs(path)
   data = json.dumps(data)
   path = path + '/' + dump_name + '_' + str(user.id) + '.txt'
   fil  = open(path, 'w').write(data)
   checksum = hashlib.sha256(data).hexdigest()
   file_dump = FileDump.objects.filter(name = dump_name, user_id = user.id)
   NOW = datetime.datetime.now
   if not file_dump:
      FileDump.objects.create(name = dump_name, user_id = user.id,\
                              checksum = checksum, path = path,\
                              creation_date = NOW, updation_date = NOW)
      return 'Created'
   else:
      file_dump = file_dump[0]
      file_dump.checksum = checksum
      file_dump.save()
      return 'Updated'
