import glob
import os
from modem.const import *
from modem.tools import log
from modem.protocol.xmodem import XMODEM


class YMODEM(XMODEM):
    '''
    YMODEM protocol implementation, expects an object to read from and an
    object to write to.
    '''

    protocol = PROTOCOL_YMODEM

    def send(self, pattern, retry=16, timeout=60):
        '''
        Send one or more files via the YMODEM protocol.

            >>> print modem.send('*.txt')
            True

        Returns ``True`` upon succesful transmission or ``False`` in case of
        failure.
        '''

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
            log.error(error.ABORT_PROTOCOL)
            # Already aborted
            return False

        for filename in filenames:
            # Send meta data packet
            sequence = 0
            error_count = 0
            # REQUIREMENT 1,1a,1b,1c,1d
            data = ''.join([os.path.basename(filename), '\x00'])

            log.debug(error.DEBUG_START_FILE % (filename,))
            # Pick a suitable packet length for the filename
            packet_size = 128 if (len(data) < 128) else 1024

            # Packet padding
            data = data.ljust(packet_size, '\0')

            # Calculate checksum
            crc = self.calc_crc(data) if crc_mode else self.calc_checksum(data)

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
                log.error(error.ABORT_SEND_STREAM)
                return False

            # AT THIS POINT
            # - FILE CONTENTS TRANSMITTED
            # - <EOT> TRANSMITTED
            # - <ACK> RECEIVED

            filedesc.close()
            # WAIT A <CRC> BEFORE NEXT FILE
            error_count = 0
            if not self._wait_recv(error_count, timeout):
                log.error(error.ABORT_INIT_NEXT)
                # Already aborted
                return False

        # End of batch transmission, send NULL file name
        sequence = 0
        error_count = 0
        packet_size = 128
        data = '\x00' * packet_size
        crc = self.calc_crc(data) if crc_mode else self.calc_checksum(data)

        # Emit packet
        if not self._send_packet(sequence, data, packet_size, crc_mode, crc,
            error_count, retry, timeout):
            log.error(error.ABORT_SEND_PACKET)
            # Already aborted
            return False

        # All went fine
        return True

    def recv(self, basedir, crc_mode=1, retry=16, timeout=60, delay=1):
        '''
        Receive some files via the YMODEM protocol and place them under
        ``basedir``::

            >>> print modem.recv(basedir)
            3

        Returns the number of files received on success or ``None`` in case of
        failure.

        N.B.: currently there are no control on the existence of files, so they
        will be silently overwritten.
        '''
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
                    log.error(error.ABORT_RECV_CAN_CAN)
                    return None
                else:
                    log.debug(error.DEBUG_RECV_CAN)
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
                        log.error(error.ABORT_RECV_CAN_CAN)
                        return None
                    else:
                        log.debug(debug.DEBUG_RECV_CAN)
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
                                log.error(error.ABORT_OPEN_FILE)
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
                log.error(error.ABORT_RECV_STREAM)
                return False

            log.debug('File transfer done, requesting next')
            fileout.close()
            num_files += 1
            sequence = 0

            # Ask for the next sequence and receive the reply
            self.putc(CRC)
            char = self.getc(1, timeout)
