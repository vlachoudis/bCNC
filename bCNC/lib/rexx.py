#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# Please consult the flair documentation for the license
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#
# Author:   Vasilis.Vlachoudis@cern.ch
# Date:     14-May-2004

import string

__author__ = "Vasilis Vlachoudis"
__email__ = "Vasilis.Vlachoudis@cern.ch"


_letters_digits = string.ascii_letters + string.digits
_letters_digits_symbol = _letters_digits + "_."


# abbrev
def abbrev(information, info, mlngt=0):
    """
    return true if the info is an abbreviation of information
    with minimum length mlngt
    """
    if mlngt > 0:
        length = mlngt
    else:
        length = len(info)

    cond1 = len(information) >= len(info)
    cond2 = len(info) >= length
    cond3 = information[: len(info)] == info
    return cond1 and cond2 and cond3


# center
def center(s, lngt, pad=" "):
    if lngt <= 0:
        return ""

    i = lngt - len(s)
    if i == 0:
        return s
    elif i < 0:
        i = -i
        a = i // 2
        return s[a:a + lngt]
    else:
        a = i // 2
        return f"{pad * a}{s}{pad * (i - a)}"


# datatype
def datatype(str_, check="N"):
    """rexx datatype function"""

    try:
        if len(str_) == 0:
            return check == "X" or check == "B"
    except Exception:
        return check == "X" or check == "B"

    if check == "N":
        return _isnum(str_)

    if check == "A":
        return verify(str_, _letters_digits) == -1
    elif check == "L":
        return verify(str_, string.ascii_lowercase) == -1
    elif check == "M":
        return verify(str_, string.ascii_letters) == -1
    elif check == "U":
        return verify(str_, string.ascii_uppercase) == -1
    elif check == "O":
        return verify(str_, string.octdigits) == -1
    elif check == "X":
        return verify(str_, string.hexdigits) == -1
    elif check == "S":
        return (str_[0] in string.ascii_letters) and (
            verify(str_[1:], _letters_digits_symbol) == -1
        )
    else:
        return _isnum(str_)


# insert
def insert(new, target, n, pad=" "):
    """
    insert new string to target as position n padded with pad characters
    """
    if n == 0:
        return new + target
    elif n > len(target):
        return target + pad * (n - len(target)) + new

    return target[0:n] + new + target[n:]


# left
def left(str_, length, pad=" "):
    """return left of string str_ of length padded with pad chars"""
    if length < len(str_):
        return str_[0:length]
    else:
        return str_ + (pad * (length - len(str_)))


# translate
def translate(str_, tableo=None, tablei=None, pad=" "):
    """translate string"""
    # If neither input nor output tables, uppercase.
    if tableo is None and tablei is None:
        return str_.upper()

    if tableo is None:
        tableo = xrange(0, 255)

    if tablei is None:
        tablei = xrange(0, 255)

    # The input table defaults to all characters.
    dl = len(tablei) - len(tableo)
    if dl > 0:
        tableo += pad * dl
    else:
        tablei += pad * (-dl)

    tbl = string.maketrans(tablei, tableo)
    return str_.translate(tbl)


# reverse
def reverse(str_):
    """reverse string"""
    return str_[::-1]


# verify
def verify(str_, ref, match=0, start=0):
    """
    return the index of the first character in string that
    is not also in reference. if "Match" is given, then return
    the result index of the first character in string that is in reference
    """

    if start < 0:
        start = 0
    if start >= len(str_):
        return -1

    for i in range(start, len(str_)):
        found = ref.find(str_[i]) == -1
        if found ^ match:
            return i
    return -1


# xrange
def xrange(start, stop):
    return "".join([chr(x) for x in range(start, stop + 1)])


# isnum - return true if string is number
def _isnum(str_):
    str_ = str_.strip()

    # accept one sign
    i = 0
    lngte = len(str_)

    if lngte == 0:
        return False

    if str_[i] == "-" or str_[i] == "+":
        i += 1

    # skip spaces after sign
    while i < lngte and str_[i].isspace():
        i += 1

    # accept many digits
    if i < lngte and "0" <= str_[i] <= "9":
        i += 1
        F = 1
        while i < lngte and "0" <= str_[i] <= "9":
            i += 1
    else:
        F = 0

    # accept one dot
    if i < lngte and str_[i] == ".":
        i += 1

        # accept many digits
        if i < lngte and "0" <= str_[i] <= "9":
            while i < lngte and "0" <= str_[i] <= "9":
                i += 1
        else:
            if not F:
                return False
    else:
        if not F:
            return False

    # accept one e/E/d/D
    if (i < lngte
            and (str_[i] == "e"
                 or str_[i] == "E"
                 or str_[i] == "d"
                 or str_[i] == "D")):
        i += 1
        # accept one sign
        if i < lngte and (str_[i] == "-" or str_[i] == "+"):
            i += 1

        # accept many digits
        if i < lngte and "0" <= str_[i] <= "9":
            while i < lngte and "0" <= str_[i] <= "9":
                i += 1
        else:
            return False

    if i != lngte:
        return False

    return True


if __name__ == "__main__":
    from .log import say

    say("abbrev")
    assert abbrev("information", "info", 4)
    assert abbrev("information", "", 0)
    assert not abbrev("information", "Info", 4)
    assert not abbrev("information", "info", 5)
    assert not abbrev("information", "info ")
    assert abbrev("information", "info", 3)
    assert not abbrev("info", "information", 3)
    assert not abbrev("info", "info", 5)

    say("center")
    assert center("****", 0, "-") == ""
    assert center("****", 8, "-") == "--****--"
    assert center("****", 7, "-") == "-****--"
    assert center("*****", 8, "-") == "-*****--"
    assert center("*****", 7, "-") == "-*****-"
    assert center("12345678", 4, "-") == "3456"
    assert center("12345678", 5, "-") == "23456"
    assert center("1234567", 4, "-") == "2345"
    assert center("1234567", 5, "-") == "23456"

    say("datatype")
    assert not datatype("")
    assert not datatype("foobar")
    assert not datatype("foo bar")
    assert not datatype("123.456.789")
    assert datatype("123.456")
    assert not datatype("DeadBeef")
    assert not datatype("Dead Beef")
    assert not datatype("1234ABCD")
    assert datatype("01001101")
    assert not datatype("0110 1101")
    assert not datatype("0110 101")
    assert datatype("1324.1234")
    assert datatype("123")
    assert datatype("12.3")
    assert datatype("123.123")
    assert datatype("123.123E3")
    assert datatype("123.0000003")
    assert datatype("123.0000004")
    assert datatype("123.0000005")
    assert datatype("123.0000006")
    assert datatype(" 23")
    assert datatype(" 23 ")
    assert datatype("23 ")
    assert datatype("123.00")
    assert datatype("123000E-2")
    assert datatype("123000E+2")
    assert not datatype("A B C")
    assert not datatype("123ABC")
    assert not datatype("123AHC")
    assert datatype("0.000E-2")
    assert datatype("0.000E-1")
    assert datatype("0.000E0")
    assert datatype("0.000E1")
    assert datatype("0.000E2")
    assert datatype("0.000E3")
    assert datatype("0.000E4")
    assert datatype("0.000E5")
    assert datatype("0.000E6")
    assert datatype("0E-1")
    assert datatype("0E0")
    assert datatype("0E1")
    assert datatype("0E2")
    assert not datatype("+.")
    assert not datatype("++0")

    say("insert")
    assert insert("abc", "def", 2) == "deabcf"
    assert insert("abc", "def", 3) == "defabc"
    assert insert("abc", "def", 5) == "def  abc"
    assert insert("abc", "def", 5, "*") == "def**abc"

    say("translate")
    assert translate("Foo Bar", "", "") == "Foo Bar"
    assert translate("Foo Bar", xrange(1, 255)) == "Gpp!Cbs"
    assert translate("", "klasjdf", "woieruw") == ""
    assert translate("foobar", "abcdef", "fedcba") == "aooefr"

    say("verify")
    assert verify("foobar", "barfo", 0, 0) == -1
    assert verify("foobar", "barfo", 1, 0) == 0
    assert verify("", "barfo") == -1
    assert verify("foobar", "") == 0
    assert verify("foobar", "barf", 0, 2) == 2
    assert verify("foobar", "barf", 0, 3) == -1
    assert verify("", "") == -1

    say("All Test passed")
