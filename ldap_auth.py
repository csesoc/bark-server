import ldap

def authenticate(username, password):
    try:
        l = ldap.open("ad.unsw.edu.au")
        #l = ldap.open("localhost")
        l.protocol_version = ldap.VERSION3

        upn = username + '@ad.unsw.edu.au'

        l.bind_s(upn, password)

        baseDN = "OU=IDM_People,OU=IDM,DC=ad,DC=unsw,DC=edu,DC=au"
        searchScope = ldap.SCOPE_SUBTREE
        retrieveAttributes = ['cn', 'displayNamePrintable', 'givenName', 'sn', 'mail']
        searchFilter = "cn=" + username

        ldap_result = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        result_type, result_data = l.result(ldap_result, 0)

        user_dn,attr_results = result_data[0]

        first_name = attr_results['givenName'][0]
        last_name = attr_results['sn'][0]
        email = attr_results['mail'][0]

        return {
            'first_name': first_name,
            'last_name': last_name,
            'email': email
        }

    except ldap.LDAPError, e:
        return None

if __name__ == '__main__':
    import getpass
    username = raw_input('zID: ')
    password = getpass.getpass()

    user = authenticate(username, password)
    print user
