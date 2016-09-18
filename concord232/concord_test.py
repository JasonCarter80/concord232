"""
Test code for interfacing to the Concord panel.

Can be run from the command line.
"""

import sys
import threading
import time

import concord


class FakeSerial(object):
    def __init__(self, msg_list_):
        self.msg_list = msg_list_
        self.curr_msg_idx = 0
        self.curr_char_idx = 0

    def ck_msg_avail(self):
        if self.curr_msg_idx >= len(self.msg_list):
            raise StopIteration("No more fake messages to send")

    def write(self, c):
        print "WROTE: %r" % c

    # Dummy for testing, will make sure panel driver code always tries
    # to read to end of available fake messages.
    def inWaiting(self):
        return 1

    def read1(self):
        self.ck_msg_avail()
        curr_msg = self.msg_list[self.curr_msg_idx]
        while len(curr_msg) == 0:
            self.curr_msg_idx += 1
            self.curr_char_idx = 0
            self.ck_msg_avail()
            curr_msg = self.msg_list[self.curr_msg_idx]
        b = curr_msg[self.curr_char_idx]
        self.curr_char_idx += 1
        if self.curr_char_idx >= len(curr_msg):
            self.curr_char_idx = 0
            self.curr_msg_idx += 1
        return b

    def read(self, size=1):
        b = '';
        for i in range(size):
            b += self.read1()
        return b

    def close(self):
        pass

class FakeLog(object):
    def __init__(self, f):
        self.f = f
    def log(self, s):
        self.f.write(s + "\n")
    def error(self, s): self.log(s)
    def warn(self, s): self.log(s)
    def info(self, s): self.log(s)
    def debug(self, s): self.log(s)
    def debug_verbose(self, s): self.log(s)

def run_test():
    """ 
    Run some fake messages through the code to make sure there are no
    obviously broken items.
    """
    messages = [
        '\n020204',
        '\n037a9b18', # not a real command, but checksum example from docs
        ]

    # These messages have blank checksums that need to be updated (00
    # at end) plus linefeeds need to be prepended.
    messages2 = [
        '082201040000500300',  # Arming level
        '0721050000a71900', # Zone status
        '0d22020600020102030409050600', # Alarm/trouble
        '090304001100ff020400', # zone data, no zone text
        '0c0304001100ff02046e574600', # zone data, with zone text
        '0b0114030202040000000700', # ???
        '0b0114040716690003834575', # Jesse's system -- Panel type command
        ]

    for m in messages2:
        bin_msg = concord.decode_message_from_ascii(m)
        concord.update_message_checksum(bin_msg)
        ascii_msg = concord.encode_message_to_ascii(bin_msg)
        messages.append('\n' + ascii_msg)

    # fake test mode
    panel = concord.AlarmPanelInterface("fake", 0.010, FakeLog(sys.stdout))
    panel.serial_interface.serdev = FakeSerial(messages)
    try:
        panel.message_loop()
    except StopIteration:
        print "No more fake messages"


def main():

    # No args: run basic smoke-test code.
    if len(sys.argv) == 1:
        run_test()
        return

    # Otherwise first argument is serial port device name, run message
    # loop ad accept basic commands from the terminal so user can poke
    # at the panel.
    dev_name = sys.argv[1]

    panel = concord.AlarmPanelInterface(dev_name, 0.1, FakeLog(sys.stdout))
    
    t = threading.Thread(target=panel.message_loop)
    t.start()
    
    try:
        while True:
            l = sys.stdin.readline()
            l = l.strip()
            if len(l) < 1:
                continue
            cmd = l[0]
            if cmd == 'x':
                try: 
                    # * token is 0x2F -- but keypress is 0x0a
                    msg = concord.decode_message_from_ascii(l[1:])
                    panel.send_keypress(msg, partition=1, no_check=True)
                except Exception, ex:
                    print "Problem sending keypresses: %r" % ex
                continue
            x = 1
            if len(l) > 1:
                try:
                    x = int(l[1:])
                except ValueError:
                    print "Bad extra param"
            if cmd == '*':
                print "SEND * part=%d" % x
                # Can't actually send the '*' key to any partitions...
                panel.send_keypress([0x0a], partition=x)
            elif cmd == 'c':
                print "SEND CHIME part=%d" % x
                # Partitions > 1 work for this
                panel.send_keypress([7, 1], partition=x)
            elif cmd == 'r':
                print "SEND REFRESH"
                panel.request_dynamic_data_refresh()
            elif cmd == 'l':
                print "SEND REQUEST ALL EQUIPMENT LIST"
                panel.request_all_equipment()
            elif cmd == 'z':
                print "SEND REQUEST ZONES"
                panel.request_zones()
            elif cmd == 'u':
                print "SEND REQUEST USERS"
                panel.request_users()
            elif cmd == 'q':
                break # Quit!
            else:
                print "???? %r" % cmd
    except KeyboardInterrupt:
        print "CAUGHT ^C, exiting"
    
    panel.stop_loop()
    t.join()


if __name__ == '__main__':
    main()
