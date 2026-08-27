#!/usr/bin/env python3

from commons import *


def data_file_get_path():
    root_dir            = get_root_path()
    data_filename       = 'data.json'
    data_file_path      = Path( '{}/data_file/{}'.format(root_dir, data_filename) )
    return data_file_path

DATA_FILE_PATH = data_file_get_path()
DATA_LIFE = {
    'quotes': 12,
    'products': 1,
    'supported_currencies': 168,
}

def data_file_init():
    file_content = {
        'quotes': {
            'USD' : {
                'quote': 1,
                'last_update': '',
            }
        },
        'products': {
            # '1d0b814b-28e6-49b2-af68-767f93f774f0': {
            #    'prices': [],
            #    'last_update': '',
            # }
        }
    }
    data_file_write( file_content )
    log('File dati creato!', context='data_file_init', color='light_green')
    return file_content

def data_file_get():
    if not os.path.isfile( DATA_FILE_PATH ):
        data_file_init()
    with open(DATA_FILE_PATH, 'r') as f:
        lines           = f.readlines()
        if not lines:
            return {}
        str_obj         = lines[0]
        data_dict       = json.loads( str_obj )
        return data_dict
    
def data_file_write( file_content ):
    file_content = json.dumps( file_content )
    f = open(DATA_FILE_PATH, 'w')
    f.write( file_content )
    f.close()

def data_file_save( file_content ):
    data_file_write( file_content )
    log('File dati salvato!', context='data_file_save', color='light_green')
    return 

def data_file_update( file_content ):
    data_file_write( file_content )
    log('File dati aggiornato!', context='data_file_update', color='light_green')
    return 


