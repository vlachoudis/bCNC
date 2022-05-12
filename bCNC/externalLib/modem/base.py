from modem.const import CRC16_MAP, CRC32_MAP
from modem.tools import crc16, crc32


class Modem(object):
    '''
    Base modem class.
    '''

    def __init__(self, getc, putc):
        self.getc = getc
        self.putc = putc

    def calc_checksum(self, data, checksum=0):
        '''
        Calculate the checksum for a given block of data, can also be used to
        update a checksum.

            >>> csum = modem.calc_checksum('hello')
            >>> csum = modem.calc_checksum('world', csum)
            >>> hex(csum)
            '0x3c'

        '''
        return (sum(map(ord, data)) + checksum) % 256

    def calc_crc16(self, data, crc=0):
        '''
        Calculate the 16 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.

            >>> crc = modem.calc_crc16('hello')
            >>> crc = modem.calc_crc16('world', crc)
            >>> hex(crc)
            '0xd5e3'

        '''
        for char in data:
            crc = crc16(char, crc)
        return crc

    def calc_crc32(self, data, crc=0):
        '''
        Calculate the 32 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.

            >>> crc = modem.calc_crc32('hello')
            >>> crc = modem.calc_crc32('world', crc)
            >>> hex(crc)
            '0x20ad'

        '''
        for char in data:
            crc = crc32(char, crc)
        return crc

    def _check_crc(self, data, crc_mode):
        '''
        Depending on crc_mode check CRC or checksum on data.

            >>> data = self._check_crc(data,crc_mode,quiet=quiet,debug=debug)
            >>> if data:
            >>>    income_size += len(data)
            >>>    stream.write(data)
            ...

        In case the control code is valid returns data without checksum/CRC,
        or returns False in case of invalid checksum/CRC
        '''
        if crc_mode:
            csum = (ord(data[-2]) << 8) + ord(data[-1])
            data = data[:-2]
            mine = self.calc_crc16(data)
            if csum == mine:
                return data
        else:
            csum = ord(data[-3])
            data = data[:-1]
            mine = self.calc_checksum(data)
            if csum == mine:
                return data
        return False
