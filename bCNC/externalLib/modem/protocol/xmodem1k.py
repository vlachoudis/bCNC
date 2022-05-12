from modem import error
from modem.const import *
from modem.tools import log
from modem.protocol.xmodem import XMODEM


class XMODEM1K(XMODEM):
    '''
    XMODEM1K protocol implementation, expects an object to read from and an
    object to write to.
    '''

    protocol = PROTOCOL_XMODEM1K

    def send(self, stream, retry=16, timeout=60):
        '''
        Send a stream via the XMODEM1K protocol.

            >>> stream = file('/etc/issue', 'rb')
            >>> print modem.send(stream)
            True

        Returns ``True`` upon succesful transmission or ``False`` in case of
        failure.
        '''

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
                    if cancel:
                        log.debug(error.DEBUG_RECV_CAN)
                        return False
                    else:
                        log.error(error.ABORT_RECV_CAN_CAN)
                        cancel = 1
                else:
                    log.error(error.ERROR_EXPECT_NAK_CRC % ord(char))

            error_count += 1
            if error_count >= retry:
                self.abort(timeout=timeout)
                return False

        if self._send_stream(stream, crc_mode, retry, timeout):
            return True
        else:
            log.error(error.ABORT_SEND_STREAM)
            return False

    def recv(self, stream, crc_mode=1, retry=16, timeout=60, delay=1):
        '''
        Receive a stream via the XMODEM1K protocol.

            >>> stream = file('/etc/issue', 'wb')
            >>> print modem.recv(stream)
            2342

        Returns the number of bytes received on success or ``None`` in case of
        failure.
        '''

        # initiate protocol
        error_count = 0
        char = 0
        cancel = 0
        while True:
            # first try CRC mode, if this fails,
            # fall back to checksum mode
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

            char = self.getc(1, timeout)
            if char is None:
                error_count += 1
                continue
            elif char == SOH:
                #crc_mode = 0
                break
            elif char in [STX, CAN]:
                break
            elif char == CAN:
                if cancel:
                    return None
                else:
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
                elif char == STX:
                    packet_size = 1024
                    break
                elif char == EOT:
                    # SEND LAST <ACK>
                    self.putc(ACK)
                    return income_size
                elif char == CAN:
                    # cancel at two consecutive cancels
                    if cancel:
                        log.error(error.ABORT_RECV_CAN_CAN)
                        return None
                    else:
                        log.debug(error.DEBUG_RECV_CAN)
                        cancel = 1
                else:
                    log.error(error.ERROR_EXPECT_SOH_EOT % ord(char))
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
                data = self.getc(packet_size + 1 + crc_mode)
                data = self._check_crc(data, crc_mode)
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
                log.debug(error.ERROR_INVALID_SEQ)

            # something went wrong, request retransmission
            self.putc(NAK)
