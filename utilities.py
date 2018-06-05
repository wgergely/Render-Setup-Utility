"""
Collection of utility functions.
"""

import copy
import re

import maya.cmds as cmds


def log(inString=None):
    """ Custom logger.
    """
    debug = False
    if debug:
        print '# Render Setup Utility: %s' % inString


def find_nth(haystack, needle, n):
    """ Find nth items.
    """
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start


def addChars(c, n):
    """ Add n number of characters to string.
    """
    l = []
    for _ in xrange(n):
        l.append(c)
    return ''.join(l)


def getIndex(a, b):
    return [i + 1 for i, item in enumerate(a) if item in set(b)]


def natsort(inList, filterOn=False):
    """ Custom natural sorting for lists.
    """
    def try_int(s):
        """ Is it an integer? """
        try:
            return int(s)
        except:
            return s

    def natsort_key(s):
        """"""
        return map(try_int, re.findall(r'(\d+|\D+)', s))

    def natcmp(a, b):
        """"""
        return (natsort_key(a) > natsort_key(b)) - (natsort_key(a) < natsort_key(b))

    def natcasecmp(a, b):
        """"""
        return natcmp(a.lower(), b.lower())

    def natsort(seq, cmp=natcmp, reverse=False):
        """"""
        if reverse:
            seq.sort(cmp, reverse=True)
        else:
            seq.sort(cmp)

    def natsorted(seq, cmp=natcmp, reverse=False):
        """"""
        temp = copy.copy(seq)
        natsort(temp, cmp, reverse)
        return temp

    # Custom:
    first = []
    second = []
    for s in inList:
        if s[:1] == ' ':
            first.append(s)
        else:
            second.append(s)
    if filterOn is True:
        return natsorted(first) + natsorted(second)
    else:
        return natsorted(inList)
