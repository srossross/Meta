'''
Created on May 10, 2012

@author: sean
'''

from imp import get_magic
import time
import struct
import marshal

def extract(binary):
    
    if len(binary) <= 8:
        raise Exception("Binary pyc must be greater than 8 bytes (got %i)" % len(binary))
    
    magic = binary[:4]
    MAGIC = get_magic()
    
    if magic != MAGIC:
        raise Exception("Python version mismatch (%r != %r) Is this a pyc file?" % (magic, MAGIC))
    
    modtime = time.asctime(time.localtime(struct.unpack('i', binary[4:8])[0]))

    code = marshal.loads(binary[8:])
    
    return modtime, code

