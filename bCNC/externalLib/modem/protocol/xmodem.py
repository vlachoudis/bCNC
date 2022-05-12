import time
from modem import error
from modem.base import Modem
from modem.const import *
from modem.tools import log


class XMODEM(Modem):
    '''
    XMODEM protocol implementation, expects an object to read from and an
    object to write to.

    >>> def getc(size, timeout=1):
    ...     return data or None
    ...
    >>> def putc(data, timeout=1):
    ...     return size or None
    ...
    >>> modem = XMODEM(getc, putc)

    '''

    # Protocol identifier
    protocol = PROTOCOL_XMODEM

    def abort(self, count=2, timeout=60):
        '''
        Send an abort sequence using CAN bytes.
        '''
        for counter in xrange(0, count):
            self.putc(CAN, timeout)

    def send(self, stream, retry=16, timeout=60, quiet=0):
        '''
        Send a stream via the XMODEM protocol.

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
                    # We abort if we receive two consecutive <CAN> bytes
                    if cancel:
                        return False
                    else:
                        cancel = 1
                else:
                    log.error(error.ERROR_EXPECT_NAK_CRC % ord(char))

            error_count += 1
            if error_count >= retry:
                log.error(error.ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return False

        # Start sending the stream
        return self._send_stream(stream, crc_mode, retry, timeout)

    def recv(self, stream, crc_mode=1, retry=16, timeout=60, delay=1, quiet=0):
        '''
        Receive a stream via the XMODEM protocol.

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
                log.error(error.ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry / 2):
                log.debug(error.DEBUG_TRY_CRC)
                if not self.putc(CRC):
                    time.sleep(delay)
                    error_count += 1
            else:
                log.debug(error.DEBUG_TRY_CHECKSUM)
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
                    log.error(error.ABORT_RECV_CAN_CAN)
                    return None
                else:
                    log.debug(error.DEBUG_RECV_CAN)
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
                    log.debug(error.DEBUG_EXPECT_SOH_EOT % ord(char))
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
                log.warning(error.WARNS_SEQUENCE % (sequence, seq1, seq2))

            # something went wrong, request retransmission
            self.putc(NAK)

    def _send_stream(self, stream, crc_mode, retry=16, timeout=0):
        '''
        Sends a stream according to the given protocol dialect:

            >>> stream = file('/etc/issue', 'rb')
            >>> print modem.send(stream)
            True

        Return ``True`` on success, ``False`` in case of failure.
        '''

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
                log.error(error.ERROR_SEND_PACKET)
                return False

            # Next sequence
            sequence = (sequence + 1) % 0x100

        # STREAM FINISHED, SEND EOT
        log.debug(error.DEBUG_SEND_EOT)
        if self._send_eot(error_count, retry, timeout):
            return True
        else:
            log.error(error.ERROR_SEND_EOT)
            return False

    def _send_packet(self, sequence, data, packet_size, crc_mode, crc,
        error_count, retry, timeout):
        '''
        Sends one single packet of data, appending the checksum/CRC. It retries
        in case of errors and wait for the <ACK>.

        Return ``True`` on success, ``False`` in case of failure.
        '''
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
                    self.error(error.ABORT_ERROR_LIMIT)
                    self.abort(timeout=timeout)
                    return False
                continue

            # Protocol error
            log.error(error.ERROR_PROTOCOL)
            error_count += 1
            if error_count >= retry:
                log.error(error.ABORT_ERROR_LIMIT)
                self.abort(timeout=timeout)
                return False

    def _send_eot(self, error_count, retry, timeout):
        '''
        Sends an <EOT> code. It retries in case of errors and wait for the
        <ACK>.

        Return ``True`` on success, ``False`` in case of failure.
        '''
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
                    log.error(error.ABORT_ERROR_LIMIT)
                    return False

    def _wait_recv(self, error_count, timeout):
        '''
        Waits for a <NAK> or <CRC> before starting the transmission.

        Return <NAK> or <CRC> on success, ``False`` in case of failure
        '''
        # Initialize protocol
        cancel = 0
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
                        log.error(error.ABORT_RECV_CAN_CAN)
                        self.abort(timeout=timeout)
                        return False
                    else:
                        log.debug(error.DEBUG_RECV_CAN)
                        cancel = 1
                else:
                    # Ignore the rest
                    pass

            error_count += 1
            if error_count >= retry:
                self.abort(timeout=timeout)
                return False

    def _recv_stream(self, stream, crc_mode, retry, timeout, delay):
        '''
        Receives data and write it on a stream. It assumes the protocol has
        already been initialized (<CRC> or <NAK> sent and optional packet 0
        received).

        On success it exits after an <EOT> and returns the number of bytes
        received. In case of failure returns ``False``.
        '''
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
                    log.error(error.ABORT_ERROR_LIMIT)
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
                    log.error(error.ABORT_PACKET_SIZE)
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
                log.debug(error.DEBUG_EXPECT_SOH_EOT % ord(char))
                error_count += 1
                if error_count >= retry:
                    log.error(error.ABORT_ERROR_LIMIT)
                    self.abort()
                    return False
