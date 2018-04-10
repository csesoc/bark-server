import ldap

class LDAPService():
    def __init__(self, ldap_host):
        self._ldap_host = ldap_host

    def authenticate(self, username, password):
        try:
            l = ldap.initialize(self._ldap_host)
            upn = username + '@ad.unsw.edu.au'
            l.bind_s(upn, password)

            baseDN = "OU=IDM_People,OU=IDM,DC=ad,DC=unsw,DC=edu,DC=au"
            searchScope = ldap.SCOPE_SUBTREE
            retrieveAttributes = ['cn', 'displayNamePrintable', 'givenName', 'sn', 'mail']
            searchFilter = "cn=" + username

            ldap_result = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
            result_type, result_data = l.result(ldap_result, 0)

            user_dn, attr_results = result_data[0]

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

class DummyLDAPService():
    """
    A dummy LDAP service that always returns success for the given user.
    """
    def authenticate(self, username, password):
        return dict(
            first_name='Dummy',
            last_name='User',
            email='{}@bark-server.com'.format(username),
        )

def create_ldap_service(config):
    if config.USE_FAKE_SERVICES:
        return DummyLDAPService()
    else:
        return LDAPService(ldap_host=config.LDAP_HOST)


if __name__ == '__main__':
    import getpass
    username = raw_input('zID: ')
    password = getpass.getpass()
    ldap_service = LDAPService()
    user = ldap_service.authenticate(username, password)
    print user
