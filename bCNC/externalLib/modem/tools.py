import logging
from modem.const import CRC16_MAP, CRC32_MAP
from zlib import crc32 as _crc32


# Configure logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.DEBUG)

log = logging.getLogger('modem')


def crc16(data, crc=0):
    '''
    Calculates the (unsigned) 16 bit cyclic redundancy check of a byte
    sequence::

        >>> crc = crc16('Hello ')
        >>> crc = crc16('world!', crc)
        >>> print hex(crc)
        0x39db

    '''
    for char in data:
        crc = (crc << 8) ^ CRC16_MAP[((crc >> 0x08) ^ ord(char)) & 0xff]
    return crc & 0xffff


def crc32(data, crc=0):
    '''
    Calculates the (unsigned) 32 bit cyclic redundancy check of a byte
    sequence::

        >>> crc = crc32('Hello ')
        >>> crc = crc32('world!', crc)
        >>> print hex(crc)
        0x1b851995

    '''
    return _crc32(data, crc) & 0xffffffff
