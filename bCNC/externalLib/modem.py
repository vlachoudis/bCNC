import glob
import os
import time
import logging
from zlib import crc32 as _crc32

from gettext import gettext as _

ABORT = _('Aborting transfer')
ABORT_WHY = _('Aborting transfer; %s')
ERROR = _('Error')
ERROR_WHY = _('Error; %s')
WARNS = _('Warning')
WARNS_WHY = _('Warnings; %s')

ABORT_ERROR_LIMIT = ABORT_WHY % _('error limit reached')
ABORT_EXPECT_NAK_CRC = ABORT_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ABORT_EXPECT_SOH_EOT = ABORT_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ABORT_INIT_NEXT = ABORT_WHY % _('initialisation of next failed')
ABORT_OPEN_FILE = ABORT_WHY % _('error opening file')
ABORT_PACKET_SIZE = ABORT_WHY % _('incompatible packet size')
ABORT_PROTOCOL = ABORT_WHY % _('protocol error')
ABORT_RECV_CAN_CAN = ABORT_WHY % _('second <CAN> received')
ABORT_RECV_PACKET = ABORT_WHY % _('packet recv failed')
ABORT_RECV_STREAM = ABORT_WHY % _('stream recv failed')
ABORT_SEND_PACKET = ABORT_WHY % _('packet send failed')
ABORT_SEND_STREAM = ABORT_WHY % _('stream send failed')

DEBUG_RECV_CAN = _('First <CAN> received')
DEBUG_SEND_CAN = _('First <CAN> sent')
DEBUG_START_FILENAME = _('Start sending "%s"')
DEBUG_TRY_CRC = _('Try CRC mode')
DEBUG_TRY_CHECKSUM = _('Try check sum mode')

ERROR_EXPECT_NAK_CRC = ERROR_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ERROR_EXPECT_SOH_EOT = ERROR_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ERROR_PROTOCOL = ERROR_WHY % _('protocol error')
ERROR_SEND_EOT = ERROR_WHY % _('failed sending <EOT>')
ERROR_SEND_PACKET = ERROR_WHY % _('failed to send packet')

WARNS_SEQUENCE = WARNS_WHY % \
                 _('invalid sequence; expected %02x got %02x/%02x')

SOH = chr(0x01)
STX = chr(0x02)
EOT = chr(0x04)
ACK = chr(0x06)
XON = chr(0x11)
XOFF = chr(0x13)
NAK = chr(0x15)
CAN = chr(0x18)
CRC = chr(0x43)

ZPAD = 0x2a
ZDLE = 0x18
ZDLEE = 0x58
ZBIN = 0x41
ZHEX = 0x42
ZBIN32 = 0x43
ZBINR32 = 0x44
ZVBIN = 0x61
ZVHEX = 0x62
ZVBIN32 = 0x63
ZVBINR32 = 0x64
ZRESC = 0x7e

# ZMODEM Frame types
ZRQINIT = 0x00
ZRINIT = 0x01
ZSINIT = 0x02
ZACK = 0x03
ZFILE = 0x04
ZSKIP = 0x05
ZNAK = 0x06
ZABORT = 0x07
ZFIN = 0x08
ZRPOS = 0x09
ZDATA = 0x0a
ZEOF = 0x0b
ZFERR = 0x0c
ZCRC = 0x0d
ZCHALLENGE = 0x0e
ZCOMPL = 0x0f
ZCAN = 0x10
ZFREECNT = 0x11
ZCOMMAND = 0x12
ZSTDERR = 0x13

# ZMODEM ZDLE sequences
ZCRCE = 0x68
ZCRCG = 0x69
ZCRCQ = 0x6a
ZCRCW = 0x6b
ZRUB0 = 0x6c
ZRUB1 = 0x6d

# ZMODEM Receiver capability flags
CANFDX = 0x01
CANOVIO = 0x02
CANBRK = 0x04
CANCRY = 0x08
CANLZW = 0x10
CANFC32 = 0x20
ESCCTL = 0x40
ESC8 = 0x80

# ZMODEM ZRINIT frame
ZF0_CANFDX = 0x01
ZF0_CANOVIO = 0x02
ZF0_CANBRK = 0x04
ZF0_CANCRY = 0x08
ZF0_CANLZW = 0x10
ZF0_CANFC32 = 0x20
ZF0_ESCCTL = 0x40
ZF0_ESC8 = 0x80
ZF1_CANVHDR = 0x01

# ZMODEM ZSINIT frame
ZF0_TESCCTL = 0x40
ZF0_TESC8 = 0x80

# ZMODEM Byte positions within header array
ZF0, ZF1, ZF2, ZF3 = range(4, 0, -1)
ZP0, ZP1, ZP2, ZP3 = range(1, 5)

# ZMODEM Frame contents
ENDOFFRAME = 2
FRAMEOK = 1
TIMEOUT = -1  # Rx routine did not receive a character within timeout
INVHDR = -2  # Invalid header received; but within timeout
INVDATA = -3  # Invalid data subpacket received
ZDLEESC = 0x8000  # One of ZCRCE/ZCRCG/ZCRCQ/ZCRCW was ZDLE escaped

# MODEM Protocol types
PROTOCOL_XMODEM = 0x00
PROTOCOL_XMODEMCRC = 0x01
PROTOCOL_XMODEM1K = 0x02
PROTOCOL_YMODEM = 0x03
PROTOCOL_ZMODEM = 0x04

PACKET_SIZE = {
    PROTOCOL_XMODEM: 128,
    PROTOCOL_XMODEMCRC: 128,
    PROTOCOL_XMODEM1K: 1024,
    PROTOCOL_YMODEM: 1024,
    PROTOCOL_ZMODEM: 1024,
}

# CRC tab calculated by Mark G. Mendel, Network Systems Corporation
CRC16_MAP = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
]

# CRC tab calculated by Gary S. Brown
CRC32_MAP = [
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
    0xe963a535, 0x9e6495a3, 0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
    0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
    0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
    0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9,
    0xfa0f3d63, 0x8d080df5, 0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
    0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b, 0x35b5a8fa, 0x42b2986c,
    0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
    0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
    0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
    0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d, 0x76dc4190, 0x01db7106,
    0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
    0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
    0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
    0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
    0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
    0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
    0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
    0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
    0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
    0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
    0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
    0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
    0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
    0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
    0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
    0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
    0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
    0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
    0x316e8eef, 0x4669be79, 0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
    0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
    0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
    0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
    0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
    0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
    0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
    0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
    0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
    0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
    0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
    0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
    0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
    0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
]

# Configure logging
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG)

log = logging.getLogger('modem')


def crc16(data, crc=0):
    """
    Calculates the (unsigned) 16 bit cyclic redundancy check of a byte
    """
    for char in data:
        crc = (crc << 8) ^ CRC16_MAP[((crc >> 0x08) ^ ord(char)) & 0xff]
    return crc & 0xffff


def crc32(data, crc=0):
    """
    Calculates the (unsigned) 32 bit cyclic redundancy check of a byte
    """
    return _crc32(data, crc) & 0xffffffff


class Modem(object):
    """
    Base modem class.
    """

    def __init__(self, getc, putc):
        self.getc = getc
        self.putc = putc

    def calc_checksum(self, data, checksum=0):
        """
        Calculate the checksum for a given block of data, can also be used to
        update a checksum.
        """
        return (sum(map(ord, data)) + checksum) % 256

    def calc_crc16(self, data, crc=0):
        """
        Calculate the 16 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.
        """
        for char in data:
            crc = crc16(char, crc)
        return crc

    def calc_crc32(self, data, crc=0):
        """
        Calculate the 32 bit Cyclic Redundancy Check for a given block of data,
        can also be used to update a CRC.
        """
        for char in data:
            crc = crc32(char, crc)
        return crc

    def _check_crc(self, data, crc_mode):
        """
        Depending on crc_mode check CRC or checksum on data.
        In case the control code is valid returns data without checksum/CRC,
        or returns False in case of invalid checksum/CRC
        """
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


class XMODEM(Modem):
    """
    XMODEM protocol implementation, expects an object to read from and an
    object to write to.
    """

    # Protocol identifier
    protocol = PROTOCOL_XMODEM

    def abort(self, count=2, timeout=60):
        '''
        Send an abort sequence using CAN bytes.
        '''
        for counter in range(0, count):
            self.putc(CAN, timeout)

    def send(self, stream, retry=16, timeout=60, quiet=0):
        """
        Send a stream via the XMODEM protocol.
        Returns ``True`` upon succesful transmission or ``False`` in case of
        failure.
        """

        # initialize protocol
        error_count = 0
        crc_mode = 0
        cancel = 0
        while True:
            char = self.getc(1)
            if char:
                if char == NAK:
                    crc_mode = 0
                    break
                elif char == CRC:
                    crc_mode = 1
                    break
                elif char == CAN:
                    # We abort if we receive two consecutive <CAN> bytes
                    if cancel:
                        return False
                    else:
                        cancel = 1
                else:
                    log.error(ERROR_EXPECT_NAK_CRC % ord(char))

            error_count += 1
            if error_count >= retry:
                log.error(ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return False

        # Start sending the stream
        return self._send_stream(stream, crc_mode, retry, timeout)

    def recv(self, stream, crc_mode=1, retry=16, timeout=60, delay=1, quiet=0):
        """
        Receive a stream via the XMODEM protocol.
        Returns the number of bytes received on success or ``None`` in case of
        failure.
        """

        # initiate protocol
        error_count = 0
        char = 0
        cancel = 0
        while True:
            # first try CRC mode, if this fails,
            # fall back to checksum mode
            if error_count >= retry:
                log.error(ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry / 2):
                log.debug(DEBUG_TRY_CRC)
                if not self.putc(CRC):
                    time.sleep(delay)
                    error_count += 1
            else:
                log.debug(DEBUG_TRY_CHECKSUM)
                crc_mode = 0
                if not self.putc(NAK):
                    time.sleep(delay)
                    error_count += 1

            char = self.getc(1, timeout)
            if char is None:
                error_count += 1
                continue
            elif char in [SOH, STX]:
                break
            elif char == CAN:
                if cancel:
                    log.error(ABORT_RECV_CAN_CAN)
                    return None
                else:
                    log.debug(DEBUG_RECV_CAN)
                    cancel = 1
            else:
                error_count += 1

        # read data
        error_count = 0
        income_size = 0
        packet_size = 128
        sequence = 1
        cancel = 0
        while True:
            while True:
                if char == SOH:
                    packet_size = 128
                    break
                elif char == EOT:
                    # Acknowledge end of transmission
                    self.putc(ACK)
                    return income_size
                elif char == CAN:
                    # We abort if we receive two consecutive <CAN> bytes
                    if cancel:
                        return None
                    else:
                        cancel = 1
                else:
                    #log.debug(DEBUG_EXPECT_SOH_EOT % ord(char))
                    error_count += 1
                    if error_count >= retry:
                        self.abort()
                        return None

            # read sequence
            error_count = 0
            cancel = 0
            seq1 = ord(self.getc(1))
            seq2 = 0xff - ord(self.getc(1))
            if seq1 == sequence and seq2 == sequence:
                # sequence is ok, read packet
                # packet_size + checksum
                data = self._check_crc(self.getc(packet_size + 1 + crc_mode),
                                       crc_mode)

                # valid data, append chunk
                if data:
                    income_size += len(data)
                    stream.write(data)
                    self.putc(ACK)
                    sequence = (sequence + 1) % 0x100
                    char = self.getc(1, timeout)
                    continue
            else:
                # consume data
                self.getc(packet_size + 1 + crc_mode)
                log.warning(WARNS_SEQUENCE % (sequence, seq1, seq2))

            # something went wrong, request retransmission
            self.putc(NAK)

    def _send_stream(self, stream, crc_mode, retry=16, timeout=0):
        """
        Sends a stream according to the given protocol dialect:
        Return ``True`` on success, ``False`` in case of failure.
        """

        # Get packet size for current protocol
        packet_size = PACKET_SIZE.get(self.protocol, 128)

        # ASSUME THAT I'VE ALREADY RECEIVED THE INITIAL <CRC> OR <NAK>
        # SO START DIRECTLY WITH STREAM TRANSMISSION
        sequence = 1
        error_count = 0

        while True:
            data = stream.read(packet_size)
            # Check if we're done sending
            if not data:
                break

            # Select optimal packet size when using YMODEM
            if self.protocol == PROTOCOL_YMODEM:
                packet_size = (len(data) <= 128) and 128 or 1024

            # Align the packet
            data = data.ljust(packet_size, '\x00')

            # Calculate CRC or checksum
            crc = crc_mode and self.calc_crc16(data) or \
                  self.calc_checksum(data)

            # SENDS PACKET WITH CRC
            if not self._send_packet(sequence, data, packet_size, crc_mode,
                                     crc, error_count, retry, timeout):
                log.error(ERROR_SEND_PACKET)
                return False

            # Next sequence
            sequence = (sequence + 1) % 0x100

        # STREAM FINISHED, SEND EOT
        #log.debug(DEBUG_SEND_EOT)
        if self._send_eot(error_count, retry, timeout):
            return True
        else:
            log.error(ERROR_SEND_EOT)
            return False

    def _send_packet(self, sequence, data, packet_size, crc_mode, crc,
                     error_count, retry, timeout):
        """
        Sends one single packet of data, appending the checksum/CRC. It retries
        in case of errors and wait for the <ACK>.
        Return ``True`` on success, ``False`` in case of failure.
        """
        start_char = SOH if packet_size == 128 else STX
        while True:
            self.putc(start_char)
            self.putc(chr(sequence))
            self.putc(chr(0xff - sequence))
            self.putc(data)
            if crc_mode:
                self.putc(chr(crc >> 8))
                self.putc(chr(crc & 0xff))
            else:
                # Send CRC or checksum
                self.putc(chr(crc))

            # Wait for the <ACK>
            char = self.getc(1, timeout)
            if char == ACK:
                # Transmission of the character was successful
                return True

            if char in [None, NAK]:
                error_count += 1
                if error_count >= retry:
                    # Excessive amounts of retransmissions requested
                    self.error(ABORT_ERROR_LIMIT)
                    self.abort(timeout=timeout)
                    return False
                continue

            # Protocol error
            log.error(ERROR_PROTOCOL)
            error_count += 1
            if error_count >= retry:
                log.error(ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return False

    def _send_eot(self, error_count, retry, timeout):
        """
        Sends an <EOT> code. It retries in case of errors and wait for the
        <ACK>.
        Return ``True`` on success, ``False`` in case of failure.
        """
        while True:
            self.putc(EOT)
            # Wait for <ACK>
            char = self.getc(1, timeout)
            if char == ACK:
                # <EOT> confirmed
                return True
            else:
                error_count += 1
                if error_count >= retry:
                    # Excessive amounts of retransmissions requested,
                    # abort transfer
                    log.error(ABORT_ERROR_LIMIT)
                    return False

    def _wait_recv(self, error_count, timeout):
        """
        Waits for a <NAK> or <CRC> before starting the transmission.
        Return <NAK> or <CRC> on success, ``False`` in case of failure
        """
        # Initialize protocol
        cancel = 0
        retry = 10 # auxi
        # Loop until the first character is a control character (NAK, CRC) or
        # we reach the retry limit
        while True:
            char = self.getc(1)
            if char:
                if char in [NAK, CRC]:
                    return char
                elif char == CAN:
                    # Cancel at two consecutive cancels
                    if cancel:
                        log.error(ABORT_RECV_CAN_CAN)
                        self.abort(timeout=timeout)
                        return False
                    else:
                        log.debug(DEBUG_RECV_CAN)
                        cancel = 1
                else:
                    # Ignore the rest
                    pass

            error_count += 1
            if error_count >= retry:
                self.abort(timeout=timeout)
                return False

    def _recv_stream(self, stream, crc_mode, retry, timeout, delay):
        """
        Receives data and write it on a stream. It assumes the protocol has
        already been initialized (<CRC> or <NAK> sent and optional packet 0
        received).
        On success it exits after an <EOT> and returns the number of bytes
        received. In case of failure returns ``False``.
        """
        # IN CASE OF YMODEM THE FILE IS ALREADY OPEN AND THE PACKET 0 RECEIVED

        error_count = 0
        cancel = 0
        sequence = 1
        income_size = 0
        self.putc(CRC)

        char = self.getc(1, timeout)
        while True:
            if char is None:
                error_count += 1
                if error_count >= retry:
                    log.error(ABORT_ERROR_LIMIT)
                    self.abort(timeout=timeout)
                    return None
                else:
                    continue
            elif char == CAN:
                if cancel:
                    return None
                else:
                    cancel = 1
            elif char in [SOH, STX]:
                packet_size = 128 if char == SOH else 1024
                # Check the requested packet size, only YMODEM has a variable
                # size
                if self.protocol != PROTOCOL_YMODEM and \
                        PACKET_SIZE.get(self.protocol) != packet_size:
                    log.error(ABORT_PACKET_SIZE)
                    self.abort(timeout=timeout)
                    return False

                seq1 = ord(self.getc(1))
                seq2 = 0xff - ord(self.getc(1))

                if seq1 == sequence and seq2 == sequence:
                    data = self.getc(packet_size + 1 + crc_mode)
                    data = self._check_crc(data, crc_mode)

                    if data:
                        # Append data to the stream
                        income_size += len(data)
                        stream.write(data)
                        self.putc(ACK)
                        sequence = (sequence + 1) % 0x100

                        # Waiting for new packet
                        char = self.getc(1, timeout)
                        continue

                # Sequence numbering is off or CRC is incorrect, request new
                # packet
                self.getc(packet_size + 1 + crc_mode)
                self.putc(NAK)
            elif char == EOT:
                # We are done, acknowledge <EOT>
                self.putc(ACK)
                return income_size
            elif char == CAN:
                # Cancel at two consecutive cancels
                if cancel:
                    return False
                else:
                    cancel = 1
                    self.putc(ACK)
                    char = self.getc(1, timeout)
                    continue
            else:
                #log.debug(DEBUG_EXPECT_SOH_EOT % ord(char))
                error_count += 1
                if error_count >= retry:
                    log.error(ABORT_ERROR_LIMIT)
                    self.abort()
                    return False


class YMODEM(XMODEM):
    """
    YMODEM protocol implementation, expects an object to read from and an
    object to write to.
    """

    protocol = PROTOCOL_YMODEM

    def send(self, pattern, retry=16, timeout=60):
        """
        Send one or more files via the YMODEM protocol.
        Returns ``True`` upon succesful transmission or ``False`` in case of
        failure.
        """

        # Get a list of files to send
        filenames = glob.glob(pattern)
        if not filenames:
            return True

        # initialize protocol
        error_count = 0
        crc_mode = 0
        start_char = self._wait_recv(error_count, timeout)
        if start_char:
            crc_mode = 1 if (start_char == CRC) else 0
        else:
            log.error(ABORT_PROTOCOL)
            # Already aborted
            return False

        for filename in filenames:
            # Send meta data packet
            sequence = 0
            error_count = 0
            # REQUIREMENT 1,1a,1b,1c,1d
            data = ''.join([os.path.basename(filename), '\x00'])

            #log.debug(DEBUG_START_FILE % (filename,))
            # Pick a suitable packet length for the filename
            packet_size = 128 if (len(data) < 128) else 1024

            # Packet padding
            data = data.ljust(packet_size, '\0')

            # Calculate checksum
            crc = self.calc_crc16(data) if crc_mode else self.calc_checksum(data)

            # Emit packet
            if not self._send_packet(sequence, data, packet_size, crc_mode,
                                     crc, error_count, retry, timeout):
                self.abort(timeout=timeout)
                return False

            # Wait for <CRC> before transmitting the file contents
            error_count = 0
            if not self._wait_recv(error_count, timeout):
                self.abort(timeout)
                return False

            filedesc = open(filename, 'rb')

            # AT THIS POINT
            # - PACKET 0 WITH METADATA TRANSMITTED
            # - INITIAL <CRC> OR <NAK> ALREADY RECEIVED

            if not self._send_stream(filedesc, crc_mode, retry, timeout):
                log.error(ABORT_SEND_STREAM)
                return False

            # AT THIS POINT
            # - FILE CONTENTS TRANSMITTED
            # - <EOT> TRANSMITTED
            # - <ACK> RECEIVED

            filedesc.close()
            # WAIT A <CRC> BEFORE NEXT FILE
            error_count = 0
            if not self._wait_recv(error_count, timeout):
                log.error(ABORT_INIT_NEXT)
                # Already aborted
                return False

        # End of batch transmission, send NULL file name
        sequence = 0
        error_count = 0
        packet_size = 128
        data = '\x00' * packet_size
        crc = self.calc_crc16(data) if crc_mode else self.calc_checksum(data)

        # Emit packet
        if not self._send_packet(sequence, data, packet_size, crc_mode, crc,
                                 error_count, retry, timeout):
            log.error(ABORT_SEND_PACKET)
            # Already aborted
            return False

        # All went fine
        return True

    def recv(self, basedir, crc_mode=1, retry=16, timeout=60, delay=1):
        """
        Receive some files via the YMODEM protocol and place them under
        ``basedir``::
        Returns the number of files received on success or ``None`` in case of
        failure.
        N.B.: currently there are no control on the existence of files, so they
        will be silently overwritten.
        """
        # Initiate protocol
        error_count = 0
        char = 0
        cancel = 0
        sequence = 0
        num_files = 0
        while True:
            # First try CRC mode, if this fails, fall back to checksum mode
            if error_count >= retry:
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry / 2):
                if not self.putc(CRC):
                    time.sleep(delay)
                    error_count += 1
            else:
                crc_mode = 0
                if not self.putc(NAK):
                    time.sleep(delay)
                    error_count += 1

            # <CRC> or <NAK> sent, waiting answer
            char = self.getc(1, timeout)
            if char is None:
                error_count += 1
                continue
            elif char == CAN:
                if cancel:
                    log.error(ABORT_RECV_CAN_CAN)
                    return None
                else:
                    log.debug(DEBUG_RECV_CAN)
                    cancel = 1
                    continue
            elif char in [SOH, STX]:
                break
            else:
                error_count += 1
                continue

        # Receiver loop
        fileout = None
        while True:
            # Read next file in batch mode
            while True:
                if char is None:
                    error_count += 1
                elif char == CAN:
                    if cancel:
                        log.error(ABORT_RECV_CAN_CAN)
                        return None
                    else:
                        log.debug(DEBUG_RECV_CAN)
                        cancel = 1
                        continue
                elif char in [SOH, STX]:
                    seq1 = ord(self.getc(1))
                    seq2 = 0xff - ord(self.getc(1))

                    if seq1 == sequence and seq2 == sequence:
                        packet_size = 128 if char == SOH else 1024
                        data = self.getc(packet_size + 1 + crc_mode)
                        data = self._check_crc(data, crc_mode)
                        if data:
                            filename = data.split('\x00')[0]
                            if not filename:
                                # No filename, end of batch reception
                                self.putc(ACK)
                                return num_files

                            log.info('Receiving %s to %s' % (filename,
                                                             basedir))
                            fileout = open(os.path.join(basedir,
                                                        os.path.basename(filename)), 'wb')

                            if not fileout:
                                log.error(ABORT_OPEN_FILE)
                                self.putc(NAK)
                                self.abort(timeout=timeout)
                                return False
                            else:
                                self.putc(ACK)
                            break

                    # Request retransmission if something went wrong
                    self.getc(packet_size + 1 + crc_mode)
                    self.putc(NAK)
                    self.getc(1, timeout)
                    continue
                else:
                    error_count += 1

                self.getc(packet_size + 1 + crc_mode)
                self.putc(NAK)
                self.getc(1, timeout)

            stream_size = self._recv_stream(fileout, crc_mode, retry, timeout,
                                            delay)

            if not stream_size:
                log.error(ABORT_RECV_STREAM)
                return False

            log.debug('File transfer done, requesting next')
            fileout.close()
            num_files += 1
            sequence = 0

            # Ask for the next sequence and receive the reply
            self.putc(CRC)
            char = self.getc(1, timeout)
