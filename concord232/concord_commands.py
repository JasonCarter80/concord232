import datetime

"""
List of command codes and handler functions for commands sent to and
from the alarm panel, plus code to tect mappings.
"""

from concord232.concord_helpers import BadMessageException, ascii_hex_to_byte
from concord232.concord_tokens import decode_text_tokens
from concord232.concord_alarm_codes import ALARM_CODES

STAR = 0xa
HASH = 0xb

KEYPRESS_CODES = {
    0x00: '0',
    0x01: '1',
    0x02: '2',
    0x03: '3',
    0x04: '4',
    0x05: '5',
    0x06: '6',
    0x07: '7',
    0x08: '8',
    0x09: '9',
    0x0a: '*',
    0x0b: '#',
    0x0c: 'Police Panic',
    0x0d: 'Aux. Panic',
    0x0e: 'Fire Panic',
    0x10: 'Lights On',
    0x11: 'Lights Off',
    0x12: 'Lights Toggle',
    0x13: 'Keyswitch On',
    0x14: 'Keyswitch Off',
    0x15: 'Keyswitch Toggle (not implemented)',
    # 0x16 -> 0x1b are undefined
    0x1c: 'Fire TP - Acknowledge',
    0x1d: 'Fire TP - Silence',
    0x1e: 'Fire TP - Fire Test',
    0x1f: 'Fire TP - Smoke Reset',
    0x20: 'Keyfob Disarm',
    0x21: 'Keyfob Arm',
    0x22: 'Keyfob Lights',
    0x23: 'Keyfob Star',
    0x24: 'Keyfob Arm/Disarm',
    0x25: 'Keyfob Lights/Star',
    0x26: 'Keyfob Long Lights',
    0x27: 'Keyfob Direct Arm to Level 3',
    0x28: 'Keyfob Direct Arm to Level 2',
    0x29: 'Keyfob Arm/Star',
    0x2a: 'Keyfob Disarm/Lights',
    # No 0x2b
    0x2c: 'TP A Key',
    0x30: 'TP B Key',
    0x2d: 'TP C Key',
    0x33: 'TP D Key',
    0x2e: 'TP E Key',
    0x36: 'TP F Key',
}

# Protocol docs say: "Bit 6 = held for a few seconds"; not sure how to
# interpret that here; I think it means all the keyfob codes, plus TP
# C & E keys.

CAPABILITY_CODES = {
    # Code -> (Description, Optional Data Description)
    0x00: ("Power Supervision", None),
    0x01: ("Access Control", None),
    0x02: ("Analog Snmoke", None),
    0x03: ("Audio Listen-In", None),
    0x04: ("SnapCard Supervision", None),
    0x05: ("Microburst", None),
    0x06: ("Dual Phone Line", None),
    0x07: ("Energy Management", None),
    0x08: ("Input Zones", "Number of inputs"),
    0x09: ("Phast/Automation/System Manager", None),
    0x00: ("Phone Interface", None),
    0x0b: ("Relay Outputs", "Number of outputs"),
    0x0c: ("RF Receiver", None),
    0x0d: ("RF Transmitter", None),
    0x0e: ("Parallel Printer", None),
    0x0f: ("Unknown", None),
    0x10: ("LED Touchpad", None),
    0x11: ("1-Line/2-Line/BLT Touchpad", None),
    0x12: ("GUI Touchpad", None),
    0x13: ("Voice Evacuation", None),
    0x14: ("Pager", None),
    0x15: ("Downloadable Code/Data", None),
    0x16: ("JTECH Premise Pager", None),
    0x17: ("Cryptography", None),
    0x18: ("LED Display", None),
}



PANEL_TYPES = {
    0x14: "Concord",
    0x0b: "Concord Express",
    0x1e: "Concord Express 4",
    0x0e: "Concord Euro",
    
    0x0d: "Advent Commercial Fire 250",
    0x0f: "Advent Home Navigator 132",
    0x10: "Advent Commercial Burg 250",
    0x11: "Advent Home Navigator 250",
    0x15: "Advent Commercial Burg 500",
    0x16: "Advent Commercial Fire 500",
    0x17: "Advent Commercial Fire 132",
    0x18: "Advent Commercial Burg 132",
}

PANEL_TYPES_CONCORD = (0x14, 0x0b, 0x1e, 0x0e)

# Concord zone types only
ZONE_TYPES = {
    0: 'Hardwired',
    1: 'RF',
    2: 'RF Touchpad',
}

NORMAL = 'Normal'
TRIPPED = 'Tripped'
FAULTED = 'Faulted'
ALARM   = 'Alarm'
TROUBLE = 'Trouble'
BYPASSED = 'Bypassed'

ZONE_STATES = {
    0: NORMAL,
    1: TRIPPED,
    2: FAULTED,
    4: ALARM,
    8: TROUBLE,
    10: BYPASSED,
}

# Concord user number values only.
USER_NUMBERS = {
    246: "System Master Code",
    247: "Installer Code",
    248: "Dealer Code",
    249: "AVM Code",
    250: "Quick Arm",
    251: "Key Switch Arm",
    252: "System",
}

ARMING_LEVELS = {
    0: 'Zone Test',
    1: 'Off',
    2: 'Home/Perimeter',
    3: 'Away/Full',
    4: 'Night',
    5: 'Silent',
}

# Concord sources
ALARM_SOURCE_TYPE = {
    0: "Bus Device",
    1: "Local Phone",
    2: "Zone",
    3: "System",
    4: "Remote Phone",
}

# Reverse map of alarm source name to type code
ALARM_SOURCE_NAME = dict((v, k) for k, v in ALARM_SOURCE_TYPE.items())

# Concord touchpad message types
TOUCHPAD_MSG_TYPE = {
    0: 'Normal',
    1: 'Broadcast',
    }
    
# Concord arming levels
ARM_LEVEL = {
    1: 'Off',
    2: 'Stay',
    3: 'Away',
    8: 'Phone Test',
    9: 'Sensor Test',
}

FEAT_STATES = {
    0x01: 'Chime',
    0x02: 'Energy saver',
    0x04: 'No delay',
    0x08: 'Latchkey',
    0x10: 'Silent arming',
    0x20: 'Quick arm',
}

EQPT_LIST_REQ_TYPES = {
    'ALL_DATA': 0x00,
    'ZONE_DATA': 0x03,
    'PART_DATA': 0x04,
    'BUS_DEV_DATA': 0x05,
    'BUS_CAP_DATA': 0x06,
    'OUTPUT_DATA': 0x07,
    'USER_DATA': 0x09,
    'SCHED_DATA': 0x0a,
    'EVENT_DATA': 0x0b,
    'LIGHT_ATTACH': 0x0c,
}


def ck_msg_len(msg, cmd, desired_len, exact_len=True):
    """ 
    *desired_len* is the length value that would be in the 'last
    index' byte at the start of the message; actual number of bytes
    will be +1 to account for the length.

    If *exact_len* is True, message must be exactly the desired
    length, otherwise it must be _at least_ the desired length.
    """
    if not exact_len:
        comp = 'at least'
        bad_len = len(msg) < desired_len + 1
    else:
        comp = 'exactly'
        bad_len = len(msg) != desired_len + 1

    if bad_len:
        raise BadMessageException("Message too short for command %r, expected %s %d but got %d" % \
                                      (cmd, comp, desired_len, len(msg)-1))

def bytes_to_num(data):
    """ *data* must be at least 4 bytes long, big-endian order. """
    assert len(data) >= 4
    num = data[3]
    num += ((data[2] << 8)  &      0xff00)
    num += ((data[1] << 16) &    0xff0000)
    num += ((data[0] << 24) &  0xff000000)
    return num
    
def num_to_bytes(num):
    return [ 0xff & (num >> 24), 0xff & (num >> 16), 0xff & (num >> 8), 0xff & num ]

def cmd_panel_type(self,msg):
    ck_msg_len(msg, 0x01, 0x0b)
    assert msg[1] == 0x01, "Unexpected command type 0x02x" % msg[1]
    panel_type = msg[2]
    d = { 'panel_type': PANEL_TYPES.get(panel_type, "Unknown Panel Type 0x%02x" % panel_type) }
    if panel_type in PANEL_TYPES_CONCORD:
        # Interpret Concord hw/sw revision numbers.
        # Really not sure about this. XXX
        d['is_concord'] = True

        if 0 < msg[3] < 27:
            letter = chr(ord('A')-1+msg[3])
        else:
            letter = '?'
        if 0 <= msg[4] <= 9:
            digit = chr(ord('0')+msg[4])
        else:
            digit = '?'
        hw_rev = letter + digit
        sw_rev = (msg[5] << 8) + msg[6]
    else:
        d['is_concord'] = False
        hw_rev = "%d.%d" % (msg[3], msg[4])
        sw_rev = "%d.%d" % (msg[5], msg[6])

    d['hardware_revision'] = hw_rev
    d['software_revision'] = sw_rev
    d['serial_number'] = bytes_to_num(msg[7:])

    self.panel = d;
    return d

def cmd_automation_event_lost(self,msg):
    """ 
    (From protocol docs) Panel's automation buffer has overflowed.
    Automation modules should respond to this with request for Dynamic
    Data Refresh and Full Equipment List Request.
    """
    return { }

def build_state_list(state_code, state_dict):
    states = 'Unknown'
    if state_code in state_dict:
        return state_dict[state_code];
    return states

def cmd_zone_status(self,msg):
    ck_msg_len(msg, 0x21, 0x07)
    assert msg[1] == 0x21, "Unexpected command type 0x02x" % msg[1]
    d = { 'partition_number': msg[2],
          'area_number': msg[3],
          'zone_number': (msg[4] << 8) + msg[5],
          'zone_state': build_state_list(msg[6], ZONE_STATES)
          }
    #Update the status
    identifier = 'p' + str(d['partition_number']) + 'z' + str(d['zone_number'])
    if identifier not in self.zones:
        z = { 'partition_number': d['partition_number'],
          'area_number': d['area_number'],
          'group_number': '',
          'zone_number': d['zone_number'],
          'zone_type': 'Unknown',
          'zone_state': d['zone_state'],
          'zone_text': '',
          'zone_text_tokens': [ ],
          }    
        self.zones[identifier] = z
    else:
        self.zones[identifier]['zone_state'] = d['zone_state']
    return d;

def cmd_zone_data(self, msg):
    ck_msg_len(msg, 0x03, 0x09, exact_len=False)
    assert msg[1] == 0x03, "Unexpected command type 0x02x" % msg[1]
    d = { 'partition_number': msg[2],
          'area_number': msg[3],
          'group_number': msg[4],
          'zone_number': (msg[5] << 8) + msg[6],
          'zone_type': ZONE_TYPES.get(msg[7], 'Unknown'),
          'zone_state': build_state_list(msg[8], ZONE_STATES),
          'zone_text': '',
          'zone_text_tokens': [ ],
          }
    if len(msg) > 0x09 + 1:
        d['zone_text'] = decode_text_tokens(msg[9:-1])
        d['zone_text_tokens'] = msg[9:-1]
    
    identifier = 'p' + str(d['partition_number']) + 'z' + str(d['zone_number'])
    self.zones[identifier] = d
    return d;
    
def cmd_arming_level(self,msg):
    ck_msg_len(msg, (0x22, 0x01), 0x08)
    assert (msg[1], msg[2]) == (0x22, 0x01), "Unexpected command type"
    d = { 'partition_number': msg[3],
          'area_number': msg[4],
          'is_keyfob': msg[5] > 0,
          'user_number_high': msg[5],
          'user_number_low': msg[6],
          }
    un = msg[6]
    if un in USER_NUMBERS:
        user_num = USER_NUMBERS[un]
    elif un <= 229:
        user_num = 'Regular User %d' % un
    elif 230 <= un <= 237:
        user_num  = 'Partition %d Master Code' % (un - 230)
    elif 238 <= un <= 245:
        user_num = 'Partition %d Duress Code' % (un - 238)
    else:
        user_num = 'Unknown Code'
        
    d['user_info'] = user_num
    d['arming_level'] = ARMING_LEVELS.get(msg[7], 'Unknown Arming Level')
    d['arming_level_code'] = msg[7]

    if  d['partition_number'] in self.partitions:
        rd = self.partitions[d['partition_number']] 
        rd['user_info'] = user_num
        rd['arming_level'] = ARMING_LEVELS.get(msg[7], 'Unknown Arming Level')
        rd['arming_level_code'] = msg[7]
        self.partitions[d['partition_number']] = rd

    return d

def decode_alarm_type(gen_code, spec_code):
    if gen_code not in ALARM_CODES:
        return 'Unknown', 'Unknown'
    gen_type, spec_type_dict = ALARM_CODES[gen_code]
    return gen_type, spec_type_dict.get(spec_code, 'Unknown')


def cmd_entry_exit_delay(self,msg):
    assert (msg[1], msg[2]) == (0x22, 0x03), "Unexpected command type"
    ck_msg_len(msg, (0x22, 0x03), 0x08)
    d = { 'partition_number': msg[3],
          'area_number': msg[4],
          'delay_seconds': bytes_to_num([0, 0, msg[6], msg[7]]),
          }
    flags = msg[5]
    bits54 = (flags >> 4) & 0x3 
    bit6 = (flags >> 5) & 1
    bit7 = (flags >> 6) & 1
    v = [ ]
    if bits54 == 0:
        v.append('standard')
    elif bits54 == 1:
        v.append('extended')
    elif bits54 == 2:
        v.append('twice extended')
    if bit6 == 1:
        v.append('exit delay')
    else:
        v.append('entry delay')
    if bit7 == 1:
        v.append('end delay')
    else:
        v.append('start delay')

    d['delay_flags'] = v
    return d;

def cmd_alarm_trouble(self,msg):
    assert (msg[1], msg[2]) == (0x22, 0x02), "Unexpected command type"
    ck_msg_len(msg, (0x22, 0x02), 0x0d)
    d = { 'partition_number': msg[3],
          'area_number': msg[4],
          'source_type': ALARM_SOURCE_TYPE.get(msg[5], 'Unknown Source'),
          'source_number': bytes_to_num([0, msg[6], msg[7], msg[8]]),
          'alarm_general_type_code': msg[9],
          'alarm_specific_type_code': msg[10],
          'event_specific_data': (msg[11] << 8) + msg[12],
    }

    # Get text descriptions
    gen_type, spec_type = decode_alarm_type(msg[9], msg[10])
    d['alarm_general_type'] = gen_type
    d['alarm_specific_type'] = spec_type
    
    return d

def build_cmd_alarm_trouble(partition, source_type, source_number, general_type, specific_type, event_data=0):
    assert source_type in ALARM_SOURCE_NAME
    source_code = ALARM_SOURCE_NAME[source_type]
    msg = [ 0x0d, 0x22, 0x02, partition, 0, source_code ] + \
        num_to_bytes(source_number)[1:] + \
        [ general_type, specific_type ] + \
        num_to_bytes(event_data)[2:]
    assert len(msg) == 0x0d
    return msg

def cmd_touchpad(self,msg):
    assert (msg[1], msg[2]) == (0x22, 0x09), "Unexpected command type"
    ck_msg_len(msg, (0x22, 0x09), 0x06, exact_len=False)
    d = { 'partition_number': msg[3],
          'area_number': msg[4],
          'message_type': TOUCHPAD_MSG_TYPE.get(msg[5], 'Unknown Message Type'),
          'display_text': '',
          'timestamp': datetime.datetime.now(),
          }
    if d['partition_number'] > 1:
        return

    if len(msg) > 0x06:
        d['display_text'] = decode_text_tokens(msg[6:-1])
       
    self.display_messages.append(d)
    return d

def cmd_siren_sync(self,msg):
    return { }

def cmd_partition_data(self,msg):
    assert msg[1] == 0x04, "Unexpected command type"
    ck_msg_len(msg, 0x04, 0x05, exact_len=False)
    d = { 'partition_number': msg[2],
          'area_number': msg[3],
          'arming_level': ARM_LEVEL.get(msg[4], 'Unknown Arming Level'),
          'arming_level_code': msg[4],
          'partition_text': '',
    }
    if len(msg) > 0x05:
        d['partition_text'] = decode_text_tokens(msg[5:-1])

    
    if  d['partition_number'] not in self.zones:
        self.partitions[d['partition_number']] = d        
    else:
        rd = self.partitions[d['partition_number']]
        rd['partition_number'] = msg[2]
        rd['area_number'] =  msg[3]
        rd['arming_level' ] =  ARM_LEVEL.get(msg[4], 'Unknown Arming Level')
        rd['arming_level_code'] = msg[4]
        rd['partition_text'] = ''
        self.partitions[d['partition_number']] = rd 
   
    return d

def bcd_decode(chars):
    val = 0
    for c in chars:
        val = 100*val + 10*((c >> 4) & 0xF) + (c & 0xf)
    return val

def cmd_user_data(self,msg):
    assert msg[1] == 0x09, "Unexpected command type"
    ck_msg_len(msg, 0x09, 0x04, exact_len=False)
    d = { 'user_number': msg[3],
          'user_code': 'Not supplied',
        }
    if len(msg) >= 8:
        d['user_code'] = '%04d' % bcd_decode(msg[5:6])
    return d
    
def cmd_sched_data(self,msg):
    return { }

def cmd_sched_event_data(self,msg):
    return { }

def cmd_light_attach(self,msg):
    return { }

def cmd_siren_setup(self,msg):
    return { }

def cmd_siren_go(self,msg):
    return { }

def cmd_siren_stop(self,msg):
    return { }

def cmd_feat_state(self,msg):
    assert (msg[1], msg[2]) == (0x22, 0x0c), "Unexpected command type"
    ck_msg_len(msg, (0x22, 0x0c), 0x06)
    d = { 'partition_number': msg[3],
          'area_number': msg[4],
          'feature_state': build_state_list(msg[5], FEAT_STATES),
          }
    return d;


def cmd_temp(self,msg):
    return { }

def cmd_time_and_date(self,msg):
    return { }

def cmd_lights_state(self,msg):
    return { }

def cmd_user_lights(self,msg):
    return { }

def cmd_keyfob(self,msg):
    return { }

def cmd_clear_image(self,msg):
    """
    (From protocol docs) This command is sent on panel power up
    initialization and when a communication failure restoral with the
    Automation Module occurs. The Concord will also send this command
    when user or installer programming mode is exited.  This is done
    instead of sending a message for each item as it is changed (user
    code deleted, etc.). The Automation Device should perform an
    Equipment List and Refresh when the Clear Image command is
    received.
    """
    return { }

def cmd_eqpt_list_done(self,msg):
    return { }

def cmd_superbus_dev_data(self,msg):
    return { }

def cmd_superbus_dev_cap(self,msg):
    return { }

def cmd_output_data(self,msg):
    return { }

def build_cmd_equipment_list(request_type=0):
    assert request_type in EQPT_LIST_REQ_TYPES.values()
    if request_type == 0:
        return [ 0x2, 0x2 ]
    else:
        return [ 0x3, 0x2, request_type ]

def build_dynamic_data_refresh():
    return [ 0x02, 0x20 ]

def build_keypress(keys, partition=1, area=0, no_check=False):
    assert len(keys) < 55
    if not no_check:
        for k in keys:
            assert k in KEYPRESS_CODES
    data = [ 4+len(keys), 0x40, partition, area ]
    data.extend(keys)
    return data
    

# These are commands sent by the panel and received by the automation
# device (that is, this software).  Some of these may be send
# autonomously by the panel, and some are sent in response to requests
# from the automation device (e.g. equipment list information).
RX_COMMANDS = {
    # Command code -> (command ID, command display name, command parser)
    0x01: ('PANEL_TYPE', "Panel Type", cmd_panel_type),
    0x02: ('EVENT_LOST', "Automation Event Lost", cmd_automation_event_lost),

    # Following are received in response to equipment list requests.
    0x03: ('ZONE_DATA',    "Zone Data", cmd_zone_data),
    0x04: ('PART_DATA',    "Partition Data", cmd_partition_data),
    0x05: ('BUS_DEV_DATA', "SuperBus Device Data", cmd_superbus_dev_data),
    0x06: ('BUS_CAP_DATA', "SuperBus Device Capabilities Data", cmd_superbus_dev_cap),
    0x07: ('OUTPUT_DATA',  "Output Data", cmd_output_data),

    # 0x08 is sent after all 0x03 and 0x05 (zone & SuperBus device)
    # commands have been sent in response to an equipment list
    # request.
    0x08: ('EQPT_LIST_DONE', "Equipment List Complete", cmd_eqpt_list_done),

    0x09: ('USER_DATA',    "User Data", cmd_user_data),
    0x0a: ('SCHED_DATA',   "Schedule Data", cmd_sched_data),
    0x0b: ('EVENT_DATA',   "Scheduled Event Data", cmd_sched_event_data),
    0x0c: ('LIGHT_ATTACH', "Light to Sensor Attachment", cmd_light_attach),
    # End of equipment list responses.

    0x20: ('CLEAR_IMAGE', "Clear Automation Image", cmd_clear_image),

    0x21: ('ZONE_STATUS',        "Zone Status", cmd_zone_status),
    (0x22, 0x01): ('ARM_LEVEL',  "Arming Level", cmd_arming_level),
    (0x22, 0x02): ('ALARM',      "Alarm/Trouble",  cmd_alarm_trouble),
    (0x22, 0x03): ('DELAY',      "Entry/Exit Delay", cmd_entry_exit_delay),
    (0x22, 0x04): ('SIREN_SETUP', "Siren Setup", cmd_siren_setup),
    (0x22, 0x05): ('SIREN_SYNC',  "Siren Synchronize", cmd_siren_sync),
    (0x22, 0x06): ('SIREN_GO',    "Siren Go", cmd_siren_go),

    (0x22, 0x09): ('TOUCHPAD', "Touchpad Display", cmd_touchpad),

    (0x22, 0x0b): ('SIREN_STOP', "Siren Stop", cmd_siren_stop),

    (0x22, 0x0c): ('FEAT_STATE', "Feature State", cmd_feat_state),
    (0x22, 0x0d): ('TEMP', "Temperature", cmd_temp),
    (0x22, 0x0e): ('TIME', "Time and Date", cmd_time_and_date),

    (0x23, 0x01): ('LIGHTS_STATE', "Lights State Command", cmd_lights_state),
    (0x23, 0x02): ('USER_LIGHTS',  "User Lights Command", cmd_user_lights),
    (0x23, 0x03): ('KEYFOB_CMD',   "Keyfob Command", cmd_keyfob),
}

TX_COMMANDS = {
    # Command code -> (command name, command construction function)
    0x02: ("Full Equipment List Request", build_cmd_equipment_list),
    (0x02, 0x03): ("Single Equipment List Request/Zone Data", build_cmd_equipment_list),
    (0x02, 0x04): ("Single Equipment List Request/Partition Data", build_cmd_equipment_list),
    (0x02, 0x05): ("Single Equipment List Request/Superbus Device Data", build_cmd_equipment_list),
    (0x02, 0x06): ("Single Equipment List Request/Superbus Device Capabilities Data", build_cmd_equipment_list),
    (0x02, 0x07): ("Single Equipment List Request/Output Data", build_cmd_equipment_list),
    # No 0x02 / 0x08
    (0x02, 0x09): ("Single Equipment List Request/User Data", build_cmd_equipment_list),
    (0x02, 0x0a): ("Single Equipment List Request/Schedule Data", build_cmd_equipment_list),
    (0x02, 0x0b): ("Single Equipment List Request/Scheduled Event Data", build_cmd_equipment_list),
    (0x02, 0x0c): ("Single Equipment List Request/Light to Sensor Attachment", build_cmd_equipment_list),
    0x20: ("Dynamic Data Refresh Request", build_dynamic_data_refresh),
    0x40: ("Keypress", build_keypress),
}
