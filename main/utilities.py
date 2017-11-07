import maya.cmds as cmds
import re

def log(inString=None):
    debug = False
    if debug: print '# Render Setup Utility: %s' % inString

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def addChars(c,n):
    l = []
    for _ in xrange(n):
        l.append(c)
    return(''.join(l))


def getIndex(a, b):
    return [i+1 for i, item in enumerate(a) if item in set(b)]


def natsort(inList, filterOn=False):
    def try_int(s):
        try: return int(s)
        except: return s
    def natsort_key(s):
        import re
        return map(try_int, re.findall(r'(\d+|\D+)', s))
    def natcmp(a, b):
        return (natsort_key(a) > natsort_key(b)) - (natsort_key(a) < natsort_key(b))
    def natcasecmp(a, b):
        return natcmp(a.lower(), b.lower())
    def natsort(seq, cmp = natcmp, reverse = False):
        if reverse:
            seq.sort(cmp, reverse = True)
        else:
            seq.sort(cmp)
    def natsorted(seq, cmp = natcmp, reverse = False):
        import copy
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
