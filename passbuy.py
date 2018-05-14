import hashlib, requests
from bs4 import BeautifulSoup
import base64
import json

class passbuy:

    def __init__(self, username, password):

        self.username = username
        self.password = password

        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:59.0) Gecko/20100101 Firefox/59.0'
        self.accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        self.accept_encoding = 'gzip, deflate, br'
        self.accept_language = 'en-US,en;q=0.5'

        self.signin = None


    def get_nif_signin(self):

        signin_url = 'https://sts.nif.no/Account/SignIn?ReturnUrl=https%3a%2f%2fsts.nif.no%2fissue%2fwsfed%3fwa%3dwsignin1.0%26wtrealm%3dhttps%253a%252f%252fka.nif.no%252f%26wctx%3drm%253d0%2526id%253dpassive%2526ru%253d%252f'
        self.signin = requests.get(signin_url, headers={'Accept': self.accept,
                                                   'Accept-Encoding': self.accept_encoding,
                                                   'Cache-Control': 'max-age=0',
                                                   'User-Agent': self.user_agent,
                                                   'Referer': 'https://ka.nif.no/',
                                                   'Cookie': 'cookieconsent=yes',
                                                   'Host': 'sts.nif.no',
                                                   'Upgrade-Insecure-Requests': '1'
                                                   }
                              )

        self.signin.cookies.update({'cookieconsent': 'yes'})

        #return self.signin.cookies

    def get_nif_login(self):

        self.get_nif_signin()

        login_url = 'https://sts.nif.no/Account/BuypassLogin?returnUrl=https%3a%2f%2fsts.nif.no%2fissue%2fwsfed%3fwa%3dwsignin1.0%26wtrealm%3dhttps%253a%252f%252fka.nif.no%252f%26wctx%3drm%253d0%2526id%253dpassive%2526ru%253d%252f'
        login = requests.get(login_url, cookies=self.signin.cookies, headers={'User-Agent': self.user_agent})

        login_html = BeautifulSoup(login.text, 'lxml')
        login_action = login_html.find('form', attrs={'id': 'idForm'}).get_attribute_list('action')[0]
        PSE = login_html.find('input', attrs={'id': 'PSE'}).get_attribute_list('value')[0]
        E = login_html.find('input', attrs={'id': 'E'}).get_attribute_list('value')[0]
        M = login_html.find('input', attrs={'id': 'M'}).get_attribute_list('value')[0]
        op = login_html.find('input', attrs={'name': 'op'}).get_attribute_list('value')[0]

        return PSE, E, M, op

    def post_buypass_form(self):

        PSE, E, M, op = self.get_nif_login()

        bp_form_url = 'https://secure.buypass.no/wips/service'
        bp_form = requests.post(bp_form_url, data={'PSE': PSE, 'E': E, 'M': M, 'op': op},
                                headers={
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Encoding': 'gzip, deflate, br',
                                    'Host': 'secure.buypass.no',
                                    'Referer': 'https://sts.nif.no/Account/BuypassLogin?returnUrl=https%253a%252f%252fsts.nif.no%252fissue%252fwsfed%253fwa%253dwsignin1.0%2526wtrealm%253dhttps%25253a%25252f%25252fka.nif.no%25252f%2526wctx%253drm%25253d0%252526id%25253dpassive%252526ru%25253d%25252f',
                                    'Upgrade-Insecure-Requests': '1',
                                    'User-Agent': self.user_agent})

        bp_form_html = BeautifulSoup(bp_form.text, 'lxml')
        bp_form_action = 'https://secure.buypass.no%s' % \
                         bp_form_html.find('form', attrs={'id': 'otpform'}).get_attribute_list('action')[0]
        bp_form_ch = bp_form_html.find('input', attrs={'id': 'ch'}).get_attribute_list('value')[0]

        return bp_form_action, bp_form_ch, bp_form

    def post_buypass_auth(self):

        bp_form_action, bp_form_ch, bp_form = self.post_buypass_form()

        hpwdhash = hashlib.sha1(self.password.encode('utf-8'))
        stotal = "%s%s" % (bp_form_ch, hpwdhash.hexdigest().upper())
        hhash = hashlib.sha1(stotal.encode('utf-8'))
        hhash.hexdigest().upper()

        bp_auth = requests.post(bp_form_action,
                                data={'ch': bp_form_ch,
                                      'flag': None,
                                      'password': hhash.hexdigest().upper(),
                                      'passwordinput': '',
                                      'username': '%s' % self.username},
                                      # cookies=bp_form.cookies,
                                headers={  # 'Cookie': 'JSESSIONID=%s' % bp_form.cookies['JSESSIONID'],
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Encoding': 'gzip, deflate, br',
                                    'Host': 'secure.buypass.no',
                                    'Referer': 'https://secure.buypass.no/wips/service',
                                    'Upgrade-Insecure-Requests': '1',
                                    'User-Agent': self.user_agent})

        bp_auth_html = BeautifulSoup(bp_auth.text, 'lxml')
        bp_auth_action = bp_auth_html.find('form', attrs={'id': 'fwForm'}).get_attribute_list('action')[0]
        bp_auth_PE = bp_auth_html.find('input', attrs={'name': 'PE'}).get_attribute_list('value')[0]

        # Remove jsessionid - again
        t = bp_form_action.split(';jsessionid=%s' % bp_form.cookies['JSESSIONID'])
        bp_form_action = '%s%s' % (t[0], t[1])

        return bp_auth_action, bp_form_action, bp_auth_PE

    def post_id_response(self):
        bp_auth_action, bp_form_action, bp_auth_PE = self.post_buypass_auth()

        id_response = requests.post(bp_auth_action,
                                    cookies=self.signin.cookies,
                                    headers={  # 'Cookie': cookie,
                                        'Accept': self.accept,
                                        'Accept-Encoding': self.accept_encoding,
                                        'Host': 'sts.nif.no',
                                        'Referer': bp_form_action,
                                        'Upgrade-Insecure-Requests': '1',
                                        'User-Agent': self.user_agent
                                    },
                                    data={'PE': bp_auth_PE},
                                    allow_redirects=False
                                    )


        id_response.cookies.update(self.signin.cookies)

        return id_response, bp_form_action

    def get_ws_fed(self):

        id_response, bp_form_action = self.post_id_response()

        ws_fed = requests.get(id_response.headers['location'],
                              cookies=id_response.cookies,
                              headers={'Accept': self.accept,
                                       'Accept-Encoding': self.accept_encoding,
                                       'Host': 'sts.nif.no',
                                       'Referer': bp_form_action,
                                       'Upgrade-Insecure-Requests': '1',
                                       'User-Agent': self.user_agent
                                       },
                              allow_redirects=False
                              )

        ws_fed.cookies.update(id_response.cookies)

        ws_fed_html = BeautifulSoup(ws_fed.text, 'lxml')
        ws_fed_action = ws_fed_html.find('form', attrs={'name': 'hiddenform'}).get_attribute_list('action')[0]
        ws_fed_wa = ws_fed_html.find('input', attrs={'name': 'wa'}).get_attribute_list('value')[0]
        ws_fed_wctx = ws_fed_html.find('input', attrs={'name': 'wctx'}).get_attribute_list('value')[0]
        ws_fed_wresult = ws_fed_html.find('input', attrs={'name': 'wresult'}).get_attribute_list('value')[0]

        return ws_fed.cookies, ws_fed_action, ws_fed_wa, ws_fed_wctx, ws_fed_wresult, id_response.headers['location']

    def post_fed(self):
        ws_fed_cookies, ws_fed_action, ws_fed_wa, ws_fed_wctx, ws_fed_wresult, id_response_location = self.get_ws_fed()

        ka = requests.post(ws_fed_action,
                           cookies=ws_fed_cookies,
                           data={'wa': ws_fed_wa,
                                 'wctx': ws_fed_wctx,
                                 'wresult': ws_fed_wresult
                                 },
                           headers={'Accept': self.accept,
                                    'Accept-Encoding': self.accept_encoding,
                                    'Host': 'ka.nif.no',
                                    'Referer': id_response_location,
                                    'Upgrade-Insecure-Requests': '1',
                                    'User-Agent': self.user_agent
                                    },
                           allow_redirects=False
                           )

        return ka.cookies

    def login(self):

        return self.post_fed()