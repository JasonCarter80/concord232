GE Concord 4 RS232 Automation Module Interface Library and Server
==================================================================

This is a tool to let you interact with your GE Concord 4 alarm panel via
the RS232 Automation module.

To install::

 # pip install concord232

The server must be run on a machine with connectivity to the panel,
which can be a local serial port

 # nx584_server --serial /dev/ttyS0 


Once that is running, you should be able to do something like this::

 $ concord232_client summary
 +------+-----------------+--------+--------+
 | Zone |       Name      | Bypass | Status |
 +------+-----------------+--------+--------+
 |  1   |    FRONT DOOR   |   -    | False  |
 |  2   |   GARAGE DOOR   |   -    | False  |
 |  3   |     SLIDING     |   -    | False  |
 |  4   | MOTION DETECTOR |   -    | False  |
 +------+-----------------+--------+--------+
 Partition 1 armed

 # Arm for stay with auto-bypass
 $ concord2332_client arm-stay

 # Arm for exit (requires tripping an entry zone)
 $ concord232_client arm-exit

 # Auto-arm (no bypass, no entry zone trip required)
 $ concord232_client arm-auto

 # Disarm
 $ concord232_client disarm --master 1234

