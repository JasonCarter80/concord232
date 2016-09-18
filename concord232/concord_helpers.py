

class BadMessageException(Exception):
    pass

def ascii_hex_to_byte(ascii_bytes):
    """ 
    Returns integer value, which is encoded as hexadecimal in first
    two characters (ascii bytes) of input; assumes *ascii_bytes* is a
    string or array of characters.

    Raises ValueError if there was a problem parsing the hex value.
    """
    assert len(ascii_bytes) >= 2
    return int(ascii_bytes[0] + ascii_bytes[1], 16)
    


def total_secs(td):
    """ *td* is a timedelta object """
    return td.days*3600*24 + td.seconds + td.microseconds/1.0e6


