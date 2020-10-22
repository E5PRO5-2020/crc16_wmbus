from binascii import hexlify
from struct import pack


def crc16_wmbus(message: bytes) -> bytes:
    """
    CRC16 EN 13757 for wm-bus
    ________________
    CRC16 uses a generator polynomial, g(x), described in EN 13757-4.
    See p. 42 for data-link layer CRC, and an example with a C1 telegram on p. 84.
    See p. 58 for transport layer CRC polynomial.

    g(x) = x^16 + x^13 + x^12 + x^11 + x^10 + x^8 + x^6 + x^5 + x^2 + 1

    In binary (excluding x^16 as it is shifted out anyway), this g(x) is represented as
    0011 1101 0110 0101   ->   0x3D65
    ^                 ^
    x^15             x^0 = 1

    See EN 13757-4, table 43, p. 50 for expected structure of ELL for a CI=0x8D telegram.
    PayloadCRC is included in the encrypted part of telegram.

    Rules:
    ______
    Treats data most-significant bit first
    Final CRC shall be complemented
    Multi-byte data is transmitted LSB first
    CRC is transmitted MSB first

    Math:
    _____
    CRC uses a finite field F=[0, 1], so we do subtraction using XOR.
    CRC is the final remainder from repeated long division of message by polynomial,
    when no further division is possible.
    The outout CRC is complemented by XOR with 0xFFFF.

    Algorithm:
    _________
    The implemented algorithm uses Python's ability for 'infinite' width of integers.
    That is inefficient, and can't be ported to C code on an embedded device.
    But it is significantly easier to understand than byte-wise algorithms or lookup tables.

    Janus Bo Andersen, October 2020

    """

    crc_bits = 16
    hex_radix = 16

    g = 0x3d65                                  # Generator polynomial, g(x)
    m = int(message, hex_radix) << crc_bits     # Message, m(x), shifted to make space for 16-bit CRC
    crc = m                                     # Start with m(x)<<16 (initial crc=remainder is 0x0000)

    m_bitlen = len(bin(m)[2:])                  # Hacky method to get number of bits req. to represent m(x)
    g_bitlen = crc_bits                         # Poly is 16 bits

    # Loop over each bit, from highest to lowest
    # Continue while remainder is larger than polynomial (i.e. still divisions to perform)
    for n in range(m_bitlen - 1, g_bitlen - 1, -1):
        # Step 1 Check if most significant bit is 1
        if crc & (1 << n):
            # If yes, perform division and subtract to get remainder (XOR)
            g_shift = g << (n - g_bitlen)     # Shift polynomial
            crc = (crc ^ g_shift) % 2**n      # mod 2^n is to emulate << 1 (but Py doesn't shift out to the left)
        else:
            # If not, move on to next
            pass

        # Repeat

    # Perform final complement
    crc = crc ^ 0xFFFF

    # Return as little-endian 16-bit to match how CRC16's are stored in telegrams
    crc_hex = hexlify(pack('<H', crc))

    return crc_hex


if __name__ == '__main__':

    # Example from p. 84
    expected_crc = b'c57a'   # Reverse order of example
    data = b'1444AE0C7856341201078C2027780B13436587'
    assert crc16_wmbus(data) == expected_crc

    # From actual telegram, payload CRC
    expected_crc = b'bb52'
    data = b'79138C7976CE000000000000000400000000000000'
    assert crc16_wmbus(data) == expected_crc

    # Another example from captured real OmniPower telegram
    expected_crc = b'1170'
    data = b'79138C4491CE000000000000000300000000000000'
    assert crc16_wmbus(data) == expected_crc
