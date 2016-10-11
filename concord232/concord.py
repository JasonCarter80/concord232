from datetime import datetime
import sys
import time
import traceback


is_py2 = sys.version[0] == '2'
if is_py2:
    import Queue as Queue
else:
    import queue as Queue

import serial


from concord232.concord_commands import RX_COMMANDS, \
    build_cmd_equipment_list, EQPT_LIST_REQ_TYPES, \
    build_dynamic_data_refresh, build_keypress, \
    build_cmd_alarm_trouble, KEYPRESS_CODES

from concord232.concord_helpers import ascii_hex_to_byte, total_secs

CONCORD_MAX_ZONE = 6

CONCORD_BAUD     = 9600
CONCORD_BYTESIZE = serial.EIGHTBITS
CONCORD_STOPBITS = serial.STOPBITS_ONE
CONCORD_PARITY   = serial.PARITY_ODD

CONCORD_MAX_LEN = 58 # includes last-index (length) byte but not checksum

MSG_START = chr(0x0A) # line feed
ACK       = chr(0x06)
NAK       = chr(0x15)

CTRL_CHARS = (ACK, NAK)

# Timeout within which sender expects to receive ACKs, in seconds.
#   inbound = message from us to panel
#   outbound = message from panel to us
ACK_TIMEOUT_INBOUND  = 1.0
ACK_TIMEOUT_OUTBOUND = 2.0 
MAX_RESENDS = 3

STOP = 'STOP'

class CommException(Exception):
    pass

class TimeoutException(CommException):
    pass

class BadEncoding(CommException):
    pass

class BadChecksum(CommException):
    pass

class SerialInterface(object):
    def __init__(self, dev_name, timeout_secs, control_char_cb, logger):
        """ 
        *dev_name* is string name of the device e.g. /dev/cu.usbserial
        *timeout_secs* in fractional seconds; e.g. 0.25 = 250 milliseconds
        """
        self.control_char_cb = control_char_cb
        self.logger = logger
        self.logger.debug("SerialInterface Starting")
        # Ugly debugging hack
        if dev_name == 'fake':
            return
        self.serdev = serial.serial_for_url(dev_name, baudrate=CONCORD_BAUD,
                                    bytesize=CONCORD_BYTESIZE, parity=CONCORD_PARITY,
                                    stopbits=CONCORD_STOPBITS, timeout=timeout_secs,
                                    xonxoff=False, rtscts=False, dsrdtr=False)

    def message_chars_maybe_available(self):
        return self.serdev.inWaiting() > 0

    def wait_for_message_start(self):
        """ 
        Read from the serial port until the message-start character is
        received, discarding other characters.  Special control
        characters are handled with the previously provided handler as
        they are encountered.
        
        Returns MSG_START when that character is read from the port;
        if there is a timeout, returns None.
        """

        byte_read = None
        while byte_read != MSG_START:
            byte_read = self._read1()
            if byte_read == '':
                # Timeout
                return None
            #self.logger.debug("Wait for message start, byte_read=%r" % byte_read)
            if byte_read in CTRL_CHARS:
                self.control_char_cb(byte_read)
            # Discard the unrecognized character
    
        return MSG_START

    def _read1(self):
        c = self.serdev.read(size=1).decode('utf-8')
        return c

    def _try_to_read(self, n):
        """ 
        Try to read *n* message chars from the serial port; if there is a
        timeout raise an exception.  Returns tuple of (message chars, control chars).
        """
        ctrl_chars = [ ]
        chars_read = [ ]
        while len(chars_read) < n:
            one_char = self._read1()
            if one_char == '':
                raise TimeoutException("Timeout in the middle of reading message from the panel")
            if one_char in CTRL_CHARS:
                ctrl_chars.append(one_char)
            else:
                chars_read.append(one_char)
        return chars_read, ctrl_chars
        
    def read_next_message(self):
        """
        Read the next message from the serial port, assuming the
        message-start character has just been read.
        
        Returned message is array of bytes.
        
        It is decoded from the ASCII representation, and includes the
        checksum on the end, and the length byte at the start.  The
        checksum is NOT validated.
        
        A valid message will have at 2 bytes for length & checksum,
        plus at least a single byte for the command code, so 3 or more
        bytes in total.
        
        This function will read as many length bytes as are indicated at
        the start of the message, which may *not* be a valid message, and
        so the message returned from here may be as short as only one byte
        (the length byte).
        
        May raise TimeoutException if there is a timeout while reading the
        message.
        
        If any special control character is encountered while reading the
        message, control_char_cb will be called with that character.
        """
        # Read length; this is is encoded as a hex string with two ascii
        # bytes; the length includes the single checksum byte at the end,
        # which is also encoded as a hex string.
        len_bytes, ctrl_chars = self._try_to_read(2)
        try:
            msg_len = ascii_hex_to_byte(len_bytes)
        except ValueError:
            raise BadEncoding("Invalid length encoding: 0x%x 0x%x" % \
                                  (len_bytes[0], len_bytes[1]))
    
        # Read the rest of the message, including checksum.
        msg_ascii = [' '] * (msg_len + 1) * 2
        msg_ascii[0:2] = len_bytes
        msg_bytes, ctrl_chars2 = self._try_to_read(msg_len * 2)
        msg_ascii[2:] = msg_bytes
        ctrl_chars.extend(ctrl_chars2)
    
        # Handle any control characters; we are assuming it's ok to wait
        # until the end of the message to deal with them, since they can
        # be sent asynchronously with respect to other messages sent by
        # the panel e.g. an ACK to one of our sent messages
        for cc in ctrl_chars:
            self.control_char_cb(cc)
    
        # Decode from ascii hex representation to binary.
        msg_bin = [ 0 ] * (msg_len + 1)
        try:
            for i in range(msg_len + 1):
                msg_bin[i] = ascii_hex_to_byte(msg_ascii[2*i:2*i+2])
        except ValueError:
            raise BadEncoding("Invalid message encoding: %r" % msg_ascii)
    
        return msg_bin

    def write_message(self, msg):
        """ 
        *msg* is a message in binary format, with a valid checksum,
        but no leading message-start character.  This method writes an
        ASCII_encoded message to the port preceded by the
        message-start linefeed character.
        """
        framed_msg = MSG_START + encode_message_to_ascii(msg) 
        #self.logger.debug("write_message: %r" % framed_msg)
        self.serdev.write(framed_msg.encode())
        

    def write(self, data):
        """ Write raw *data* to the serial port. """
        self.serdev.write(data)

    def close(self):
        self.serdev.close()

def compute_checksum(bin_msg):
    """ Compute checksum over all of *bin_msg*. """
    assert len(bin_msg) > 0
    cksum = 0
    for b in bin_msg:
        cksum += b
    return cksum % 256    

def validate_message_checksum(bin_msg):
    """
    *bin_msg* is an array of bytes that have already been decoded from
    the Automation Module ascii format, e.g. an array like [ 0x2A,
    0xF9 ] rather than [ '2', 'A', 'F', '9' ].  *bin_msg* must include
    the checksum on the end and last-index (length) byte at the start,
    but not the message-start linefeed.

    Returns True if checksum is as expected, else False.
    """
    assert len(bin_msg) >= 2
    return compute_checksum(bin_msg[:-1]) == bin_msg[-1]

def update_message_checksum(bin_msg):
    assert len(bin_msg) >= 2
    bin_msg[-1] = compute_checksum(bin_msg[:-1])

def encode_message_to_ascii(bin_msg):
    s = ''
    for b in bin_msg:
        s += '%02x' % b
    return s

def decode_message_from_ascii(ascii_msg):
    n = len(ascii_msg)
    if n % 2 != 0:
        raise BadEncoding("ASCII message has uneven number of characters.")
    b = [ 0 ] * (n/2)
    for i in range(n/2):
        b[i] = ascii_hex_to_byte(ascii_msg[2*i:2*i+2])
    return b


class AlarmPanelInterface(object):
    def __init__(self, dev_name, timeout_secs, logger):
        self.serial_interface = SerialInterface(dev_name, timeout_secs, \
                                                    self.ctrl_char_cb, logger)
        self.timeout_secs = timeout_secs
        self.logger = logger
        self.logger.debug("Starting")
        self.panel = {}
        self.partitions = {}
        self.zones  = {}
        self.users = {}
        self.master_pin = '0520'
     
        self.display_messages = [];
        # Messages on the transmit queue are in binary format with a
        # valid checksum.
        self.tx_queue = Queue.Queue()

        # This queue hold "fake" synthetic messages that the client
        # can send to itself.  If the panel interface seem messages on
        # this queue, it will 'receive' them.
        self.fake_rx_queue = Queue.Queue()

        self.reset_pending_tx()

        self.message_handlers = { } # Command ID -> list of message handlers for that ID.
        for command_code, (command_id, command_name, parser_fn) \
                in RX_COMMANDS.items():
            self.message_handlers[command_id] = [ ]
        

    def register_message_handler(self, command_id, handler_fn):
        """ 
        *handler_fn* will be passed a dict that is the result of
        parsing the message for the specificed command ID.

        Note: these handlers will be called from in the message loop
        thread, NOT the main thread.
        """
        if command_id not in self.message_handlers:
            raise KeyError("No such command ID %r" % command_id)
        self.message_handlers[command_id].append(handler_fn)

    def ctrl_char_cb(self, cc):
        #self.logger.debug("Ctrl char %r" % cc)
        if cc == ACK:
            if self.tx_pending is None:
                self.logger.debug("Spurious ACK")

            self.reset_pending_tx()
        elif cc == NAK:
            if self.tx_pending is None:
                self.logger.debug("Spurious NAK")
            else:
                self.logger.debug("Possible NAK")
                self.maybe_resend_message("NAK")
        else:
            self.logger.info("Unknown control char 0x%02x" % cc)

    def tx_timeout_exceded(self):
        assert self.tx_pending is not None
        elapsed = datetime.now() - self.tx_time
        return total_secs(elapsed) > ACK_TIMEOUT_INBOUND

    def reset_pending_tx(self):
        self.tx_time = None
        self.tx_pending = None
        self.tx_num_attempts = 0
    
    def send_message(self, msg, retry=False):
        """ 
        Send a message directly to the serial port.  Update pending TX
        state.  If *retry* is True, increment the attempts count,
        otherwise reset it to first attempt.
        """
        self.tx_pending = msg
        if retry:
            self.tx_num_attempts += 1
            self.logger.warn("Resending message, attempt %d: %r" % \
                                  (self.tx_num_attempts, encode_message_to_ascii(msg)))
        else:
            self.tx_num_attempts = 1
            self.logger.debug("Sending message (retry=%d) %r" % \
                     (self.tx_num_attempts, encode_message_to_ascii(msg)))
        self.tx_time = datetime.now()
        self.serial_interface.write_message(msg)

    def maybe_resend_message(self, reason):
        if self.tx_num_attempts >= MAX_RESENDS:
            self.logger.error("Unable to send message (%s), too many attempts (%d): %r" % \
                                  (reason, MAX_RESENDS, encode_message_to_ascii(self.tx_pending)))
            self.reset_pending_tx()
        else:
            self.send_message(self.tx_pending, retry=True)

    # XXX include length bytes in the front?  YES
    def enqueue_msg_for_tx(self, msg):
        """
        Put *msg* on the transmit queue, and append a checksum; *msg*
        is modified.

        This method may be called by the main thread; messages
        enqueued here will be consumed and transmitted by the
        background event-loop thread.
        """
        msg.append(compute_checksum(msg))
        self.tx_queue.put(msg)

    def enqueue_synthetic_msg_for_rx(self, msg):
        """
        Put *msg* on the 'fake' receive queue; it will be 'received'
        by this panel interface object.  The checksum will be
        calculated and appended, but the length byte is required at
        the start of the message. *msg* is modified.
        """
        msg.append(compute_checksum(msg))
        self.fake_rx_queue.put(msg)
        

    def stop_loop(self):
        self.tx_queue.put(STOP)

    def message_loop(self):
        self.logger.debug("Message Loop Starting")        
        #self.request_partitions();
        #time.sleep(1)
        self.request_zones();        
        #time.sleep(1)
        #self.request_users();
        #time.sleep(1)
        self.request_dynamic_data_refresh();
        loop_start_at = datetime.now()
        loop_last_print_at = datetime.now()

        while True:
            # Two parts to loop body: 1) look for and handle any
            # incoming messages, and 2) send out any outgoing
            # messages.

            # Hacky flag variables to avoid spinning fast if there is
            # nothing coming in and nothing going out (the common
            # case...)
            no_inputs = True
            no_outputs = True

            # 
            # Handle any synthetic messages and loop them back to us.
            #
            if not self.fake_rx_queue.empty():
                no_inputs = False
                msg = self.fake_rx_queue.get()
                self.logger.debug("Received synthetic message")
                # Don't need to confirm checksum as we computed it
                # ourselves!
                self.handle_message(msg)

            # 
            # Handle incoming messages.
            #
            # Two part test: the first part will fail right away if
            # there no characters, regardless of the timeout, so we
            # minimize time waiting on messages that won't arrive.
            if self.serial_interface.message_chars_maybe_available() \
                    and self.serial_interface.wait_for_message_start() == MSG_START:
                no_inputs = False

                msg_ok = True
                try:
                    msg = self.serial_interface.read_next_message()
                    #self.logger.debug(msg)
                except CommException as ex:
                    self.send_nak()
                    self.logger.error(repr(ex))
                    continue

                msg_time = datetime.now()

                if len(msg) < 3:
                    # Message too short, need at least length byte,
                    # command byte, and checksum byte.
                    self.send_nak()
                    self.logger.error("Message too short: %r" % encode_message_to_ascii(msg))

                if validate_message_checksum(msg):
                    self.send_ack()
                    self.handle_message(msg)
                else:
                    # Bad checksum
                    self.send_nak()
                    self.logger.error("Bad checksum for message %r" % encode_message_to_ascii(msg))

            # TODO: check here if there is pending input and handle it
            # by looping again, before worrying about sending out any
            # commands.

            #
            # If there is a pending message awaiting ack, see if it needs
            # to be resent.  If there is no pending message (or the
            # pending message timed-out), send what's on the transmit
            # queue.
            #
            if self.tx_pending is not None and self.tx_timeout_exceded():
                no_outputs = False
                self.maybe_resend_message("timeout")
            if self.tx_pending is None and not self.tx_queue.empty():
                no_outputs = False
                msg = self.tx_queue.get()
                if msg == STOP:
                    # Close the serial port once all the pending
                    # messages have been sent.  Because we close it,
                    # we can't rerun message_loop(); we have to create
                    # a new AlarmPanelInterface instance.
                    self.serial_interface.close()
                    return
                self.send_message(msg)

            # If there was nothing to do on this pass through the
            # loop, take a nap...
            if no_inputs and no_outputs:
                time.sleep(self.timeout_secs)

            secs_since_print = total_secs(datetime.now() - loop_last_print_at)
            if secs_since_print > 20:
                self.logger.debug("Looping %d" % \
                                              total_secs(datetime.now() - loop_start_at))
                loop_last_print_at = datetime.now()


    def handle_message(self, msg):
        # Assume we have a good message here.  Command code will
        # either be one or two bytes at offset 1.
        cmd1 = msg[1]
        cmd2 = None
        if len(msg) > 3:
            cmd2 = msg[2]

        # self.log("Handle message %r" % encode_message_to_ascii(msg))

        if cmd1 in RX_COMMANDS:
            command = cmd1
            cmd_str = "0x%02x" % command
        elif (cmd1, cmd2) in RX_COMMANDS:
            command = (cmd1, cmd2)
            cmd_str = "0x%02x/0x%02x" % (command[0], command[1])
        else:
            self.logger.error("Unknown command for message %r" % encode_message_to_ascii(msg))
            return

        command_id, command_name, command_parser = RX_COMMANDS[command]
        if command_parser is None:
            self.logger.debug("No parser for command %s %s" % (command_name, command_id))
            return

        #if command_id in ['SIREN_SYNC','TOUCHPAD']:
        #    return

        if command_id in ('SIREN_SYNC','SIREN_SETUP','SIREN_GO','LIGHTS_STATE'):
            return

        if command_id not in ('TOUCHPAD'):
            self.logger.debug("Handling command %s %s, %s" % \
                                      (cmd_str, command_id, command_parser.__name__))
        

        try:
            decoded_command = command_parser(self,msg)
            if not decoded_command:
                return

            decoded_command['command_id'] = command_id
            
            if 'action' in decoded_command:
                try:
                    #self.logger.info('Try to execute: %r' % decoded_command['action'])
                    func = getattr(self, decoded_command['action'], None)
                    if func is not None:
                        func(decoded_command)
                    else:
                        self.logger.info('Counld not execute: %r' % decoded_command['action'])
                except AttributeError as e:
                    self.logger.info(decoded_command['action'] + ' does not exists')
                    self.logger.info(e)
            
            self.logger.debug(repr(decoded_command))
            for handler in self.message_handlers[command_id]:
                self.logger.debug("Calling handler %r" % handler)
        
        except Exception as ex:
            self.logger.error("Problem handling command %r\n%r" % \
                                  (ex, encode_message_to_ascii(msg)))
            self.logger.error(traceback.format_exc())


    def send_the_master_code(self, msg):
        if self.master_pin is not None:
            keys = []
            for k in self.master_pin:
                self.logger.debug("Adding Key: " + k)
                keys.append(0x00+int(k))
            self.send_keypress(keys)

    def send_nak(self):       
        self.serial_interface.write(NAK.encode())

    def send_ack(self):
        self.serial_interface.write(ACK.encode())

    def request_all_equipment(self):
        msg = build_cmd_equipment_list(request_type=0)
        self.enqueue_msg_for_tx(msg)

    def request_zones(self):
        req = EQPT_LIST_REQ_TYPES['ZONE_DATA']
        msg = build_cmd_equipment_list(request_type=req)
        self.enqueue_msg_for_tx(msg)

    def request_partitions(self):
        req = EQPT_LIST_REQ_TYPES['PART_DATA']
        msg = build_cmd_equipment_list(request_type=req)
        self.enqueue_msg_for_tx(msg)

    def request_users(self):
        req = EQPT_LIST_REQ_TYPES['USER_DATA']
        msg = build_cmd_equipment_list(request_type=req)
        self.enqueue_msg_for_tx(msg)

    def request_dynamic_data_refresh(self):
        msg = build_dynamic_data_refresh()
        self.enqueue_msg_for_tx(msg)

    def send_keypress(self, keys, partition=1, no_check=False):
        msg = build_keypress(keys, partition, area=0, no_check=True)
        self.enqueue_msg_for_tx(msg)
        
    def arm_stay(self):
        self.send_keypress([0x21])

    def send_keys(self, keys, group):
        msg = []
        for k in keys:
            a = list(KEYPRESS_CODES.keys())[list(KEYPRESS_CODES.values()).index(str(k))]
            if group:               
                msg.append(a)
            else:
                self.logger.info("Sending key: %r" % msg)
                self.send_keypress([a])        

        if group:
            self.logger.info("Sending group of keys: %r" % msg)
            self.send_keypress(msg)    
       

    def disarm(self,master_pin):
        self.master_pin = master_pin
        self.send_keypress([0x20])
        
    def inject_alarm_message(self, partition, general_type, specific_type, event_data=0):
        msg = build_cmd_alarm_trouble(partition, "System", 1,
                                      general_type, specific_type)
        self.enqueue_synthetic_msg_for_rx(msg)
        
                
                

