from datetime import datetime
import re
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib

UDB_URL = 'https://cgi.cse.unsw.edu.au/~csesoc/udb/'
UDB_USER = 'udb'
UDB_PASS = os.environ['UDB_PASSWORD']

class UDBError(Exception):
    pass

def cmp_usernames(a, b):
    if re.match(r'^[a-z]+$', a):
        return 1
    elif re.match(r'^[a-z]+$', b):
        return -1

    return cmp(a, b)

def get_data(user):
    # TODO: validate username
    r = requests.get(UDB_URL + '?user=' + urllib.quote(user),
                     auth=HTTPBasicAuth(UDB_USER, UDB_PASS))

    if r.status_code != 200:
        return None

    return r.content

def get_user(user):
    try:
        output = get_data(user)
    except:
        raise UDBError('Error while communicating with UDB')

    if output is None:
        #raise UDBError("Student not found in CSE's database")
        return None

    select_keys = {
        'givenname': 'given_names',
        'surname': 'surname'
    }
    data = {key: None for key in select_keys.values()}

    # add their usernames
    usernames_str = re.search(r'uid = \d+ name=([^\s]*)', output).group(1)
    usernames = [s.split('.', 1)[1] for s in usernames_str.split('|')]
    zid = [username for username in usernames if re.match(r'^z[0-9]+$', username)][0]
    usernames = [s for s in usernames if s != zid]
    usernames.sort(cmp=cmp_usernames, reverse=True)

    data['usernames'] = usernames
    data['username'] = usernames[0] if len(usernames) else zid
    data['zid'] = zid

    expiries = []

    # get classes
    degrees = []
    courses = []
    classes = []
    for expiry_ts, name in re.findall(r'<\d+ \(\d+ \d+\) (\d+)> ([^ ]+)', output):
        expiry_ts = int(expiry_ts)
        expiry = datetime.fromtimestamp(expiry_ts).date()

        expiries.append(expiry)

        match = re.match('^(\d{4})_Student$', name)
        if match:
            # it's a degree
            degrees.append({
                'code': match.group(1),
                'expiry': expiry
            })
            continue

        match = re.match('^([A-Z]{4}\d{4})_Student$', name)
        if match:
            # it's a course
            courses.append({
                'code': match.group(1),
                'expiry': expiry
            })
            continue

        # if we're still here, it's a misc class, e.g. tutoring
        classes.append({
            'name': name,
            'expiry': expiry
        })

    # put newest (i.e. expiring latest?) classes first
    class_sort = lambda x: sorted(x, key=lambda y: y['expiry'], reverse=True)

    data['degrees'] = class_sort(degrees)
    data['courses'] = class_sort(courses)
    data['classes'] = class_sort(classes)

    data['expiry'] = max(expiries)

    # get data from strings
    for value, keys in re.findall(r'<\d+:([^>]*)> ([^\n]*)\n', output, re.DOTALL):
        keys = keys.split('|')
        for key in keys:
            if key in select_keys:
                data[select_keys[key]] = value

    return data

if __name__ == '__main__':
    import sys
    print repr(get_user(sys.argv[1]))
