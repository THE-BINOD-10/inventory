from os.path import abspath
from os.path import dirname
from os.path import join


ROOT_PATH = abspath(join(dirname(__file__), '..'))


DLL_BASE_PATH = join(ROOT_PATH, 'DLL')
DLL_FILE_NAME = ''