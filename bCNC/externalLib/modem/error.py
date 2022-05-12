from gettext import gettext as _

ABORT                = _('Aborting transfer')
ABORT_WHY            = _('Aborting transfer; %s')
ERROR                = _('Error')
ERROR_WHY            = _('Error; %s')
WARNS                = _('Warning')
WARNS_WHY            = _('Warnings; %s')

ABORT_ERROR_LIMIT    = ABORT_WHY % _('error limit reached')
ABORT_EXPECT_NAK_CRC = ABORT_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ABORT_EXPECT_SOH_EOT = ABORT_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ABORT_INIT_NEXT      = ABORT_WHY % _('initialisation of next failed')
ABORT_OPEN_FILE      = ABORT_WHY % _('error opening file')
ABORT_PACKET_SIZE    = ABORT_WHY % _('incompatible packet size')
ABORT_PROTOCOL       = ABORT_WHY % _('protocol error')
ABORT_RECV_CAN_CAN   = ABORT_WHY % _('second <CAN> received')
ABORT_RECV_PACKET    = ABORT_WHY % _('packet recv failed')
ABORT_RECV_STREAM    = ABORT_WHY % _('stream recv failed')
ABORT_SEND_PACKET    = ABORT_WHY % _('packet send failed')
ABORT_SEND_STREAM    = ABORT_WHY % _('stream send failed')

DEBUG_RECV_CAN       = _('First <CAN> received')
DEBUG_SEND_CAN       = _('First <CAN> sent')
DEBUG_START_FILENAME = _('Start sending "%s"')
DEBUG_TRY_CRC        = _('Try CRC mode')
DEBUG_TRY_CHECKSUM   = _('Try check sum mode')

ERROR_EXPECT_NAK_CRC = ERROR_WHY % _('expected <NAK>/<CRC>, got "%02x"')
ERROR_EXPECT_SOH_EOT = ERROR_WHY % _('expected <SOH>/<EOT>, got "%02x"')
ERROR_PROTOCOL       = ERROR_WHY % _('protocol error')
ERROR_SEND_EOT       = ERROR_WHY % _('failed sending <EOT>')
ERROR_SEND_PACKET    = ERROR_WHY % _('failed to send packet')

WARNS_SEQUENCE       = WARNS_WHY % \
    _('invalid sequence; expected %02x got %02x/%02x')
