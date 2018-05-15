"""
    Run as:
    nohup python melwin.py >> spyne.log 2>&1&

"""

from spyne import rpc, srpc, ServiceBase, ComplexModel, Iterable,\
    Integer, Unicode, Boolean, Date, DateTime, Array, \
    AnyXml, AnyDict, Mandatory, Application

# from spyne.util.simple import wsgi_soap_application
from spyne.server.wsgi import WsgiApplication
from spyne.protocol.soap import Soap11

import logging
import dateutil.parser
import requests
import api
import passbuy

from lxml import etree
class ClubsPayment(ComplexModel):
    ClubId = Integer
    PaymentStatus = Integer
    Active = Boolean

class Activity(ComplexModel):
    ClubId = Integer
    Name = Unicode
    OrgId = Integer
    OrgTypeId = Integer
    OrgTypeName = Unicode
    IsPassive = Boolean
    FunctionId = Integer

# print(spyne._version)PersonID, Etternavn, Fornavn, fødselsdato ,kjønn, epost, mobiltelefon Postadresse, postnummer
# Takes the return and transforms to
class Person(ComplexModel):
    Id = Integer
    MelwinId = Integer
    FullName = Unicode
    BirthDate = DateTime
    GenderId = Integer
    GenderText = Unicode
    Email = Unicode
    Phone = Unicode
    Address = Unicode
    PostNumber = Unicode
    City = Unicode
    Updated = DateTime
    Created = DateTime
    MongoId = Unicode

    IsActive = Boolean
    ClubId = Integer
    PaymentStatus = Integer

    Gren = Array(Activity)
    activities = Array(Activity)
    clubs_payment = Array(ClubsPayment)
    #clubs = Array(Integer)


class MelwinUpdated(ComplexModel):
    status = Unicode
    status_code = Integer
    PersonId = Integer
    MelwinId = Integer

class LoginResponse(ComplexModel):
    Status = Unicode
    StatusCode = Integer
    Message = Unicode
    MelwinId = Integer
    PersonId = Integer

class Org(ComplexModel):
    Address = Unicode
    BrregOrgNo = Unicode
    City = Unicode
    County = Unicode
    CountyId = Integer
    Email = Unicode
    Id = Integer
    Name = Unicode
    NameDescr = Unicode
    OrgType = Unicode
    OrgTypeId = Integer
    Url = Unicode
    Zip = Unicode
    _down = Array(Integer)
    _up = Array(Integer)
    _updated = DateTime
    _created = DateTime
    _etag = Unicode
    _id = Unicode

class PasswordModel(Unicode):
    #__namespace__ = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
    pass

class WSSEAuth(ComplexModel):
    #__namespace__ = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
    Username = Unicode
    Password = Unicode

class WSSE(ComplexModel):
    #__namespace__ = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd#UsernameToken'
    UsernameToken = WSSEAuth

class UsernameToken(ComplexModel):
    UsernameToken = WSSEAuth

class Security(ComplexModel):
    #__namespace__ = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
    UsernameToken = WSSEAuth


key = 'NjEzM2Q5Y2VjYmE1NDQ5NDg5ZGJjNzhjYzIwY2FmNGE6'


def get_api_key():
    return 'Basic %s' % api.key


def get_api_url():
    return 'https://medlem.nlf.no/api/v1/ka'


def get_api_headers():
    return {
        'Authorization': get_api_key(),
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br'
    }

def get_club_id(kl_id):

    club_resp = requests.get('%s/clubs/?where={"NifOrganisationNumber":"%s"}' % (get_api_url(), kl_id),
                             headers=get_api_headers())

    if club_resp.status_code != 200:
        return -1
    else:
        clubs = club_resp.json()['_items']
        if len(clubs) == 1:
            return int(club_resp.json()['_items'][0]['Id'])
        else:
            return -1

def authenticate(ctx):
    wss_password = ''
    wss_username = ''
    for ngh in ctx.in_header_doc[0].iterdescendants():

        try:
            key = ngh.tag.split('}')[1]

            if key == 'Password':
                wss_password = ngh.text
            elif key == 'Username':
                wss_username = ngh.text
        except:
            pass

    if wss_username == api.username and wss_password == api.password:
        return True

    return False

def get_credentials(ctx):
    wss_password = ''
    wss_username = ''

    for ngh in ctx.in_header_doc[0].iterdescendants():

        try:
            key = ngh.tag.split('}')[1]

            if key == 'Password':
                wss_password = ngh.text
            elif key == 'Username':
                wss_username = ngh.text
        except:
            pass

    return wss_username, wss_password

def get_melwin_id(person_id):

    r = requests.get('%s/members/%s?projection={"Id":1, "MelwinId": 1}'
                     % (get_api_url(), person_id),
                     headers=get_api_headers())
    if r.status_code == 200:
        print(r.json())
        return r.json()['MelwinId']
        # data = r.json()
        # return data['Id'], data['MelwinId']

    else:
        return None

class MelwinService(ServiceBase):

    __in_header__ = Security



    @rpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(ctx, name, numbers):
        """
        Say hello!
        <b>Hello hello</b>
        @param name the name to say hello to
        @param numbers the number of times
        @return the completed array
        """
        print('HEADERS')
        a = [txt.strip() for txt in ctx.in_header_doc[0].itertext()]
        print(a)
        print('Auth result: %s' % authenticate(ctx))
        print('/HEADERS')
        #root = etree.fromstring(ctx.in_header_doc)
        #etree.tostring(root)

        return u'Hello, %s' % name

    @srpc(Unicode, Unicode, Integer, Array(Integer), Integer, _returns=Iterable(Person))
    def get_members(ApiKey, ClubId, MelwinId=0, PaymentStatus=[], IsActive=0):
        """
        Members by KL number and if MelwinId or not
        @param ApiKey secret API key String, mandatory
        @param ClubId the club KL number String, mandatory
        @param MelwinId get users with (1), without (-1) or all (0) MelwinId, defaults to 0
        @param PaymentStatus array of integers to include, defaults to all
        @param IsActive integer 1=True, -1=False, 0=all
        @return
        """

        if ApiKey == api.key:

            club_id = get_club_id(ClubId)
            melwin_query = ''

            if IsActive == 0 or IsActive is None:
                melwin_query = '"$or":[{"clubs_active": {"$in": [%s]}},{"clubs_inactive": {"$in": [%s]}}]' % (
                    club_id, club_id)
            elif IsActive < 0:
                melwin_query = '"clubs_inactive": {"$in": [%s]}' % (
                    club_id)
            elif IsActive > 0:
                melwin_query = '"clubs_active": {"$in": [%s]}' % (
                    club_id)


            if MelwinId is None:
                pass
            elif MelwinId < 0:
                melwin_query = '%s,"MelwinId":null' % melwin_query
            elif MelwinId > 0:
                melwin_query = '%s,"MelwinId":{"$ne":null}' % melwin_query
            else:
                pass

            if PaymentStatus is not None and isinstance(PaymentStatus, list) and len(PaymentStatus) > 0:
                melwin_query = '%s,\
                "$and": [{"clubs_payment": {"$elemMatch": {"ClubId": %s}}}, {"clubs_payment": {"$elemMatch": {"PaymentStatus": {"$in": [%s]}}}}]' % (melwin_query, club_id, ','.join(str(x) for x in PaymentStatus))
                #$and: [{"clubs_payment": {"$elemMatch": {"ClubId": %s}}}, {"clubs_payment": {"$elemMatch": {"PaymentStatus": {"$in": [%s]}}}}]' % (melwin_query, club_id, ','.join(str(x) for x in PaymentStatus))

            # old melwin_query = '%s,"$and": [{"clubs_payment.ClubId": %s}, {"clubs_payment.PaymentStatus": {"$in": [%s]}}]' % \

            # Corrected example:
            # {"$or": [{"clubs_active": {"$in": [22976]}}, {"clubs_inactive": {"$in": [22976]}}],
            # "$and": [{"clubs_payment.ClubId": 22976}, {"clubs_payment.PaymentStatus": {"$in": [0]}}]}
            if club_id > 0:
                member_resp = requests.get('%s/members/?where={%s}' %
                                           (get_api_url(), melwin_query),
                                           headers=get_api_headers())

                if member_resp.status_code != 200:
                    return [{}]
                else:
                    # print(member_resp.json()['_items'][0])

                    m = member_resp.json()['_items']
                    for key, value in enumerate(m):  # strptime(modified, '%Y-%m-%dT%H:%M:%S.000Z')
                        m[key]['BirthDate'] = dateutil.parser.parse(m[key]['BirthDate'])
                        m[key]['Updated'] = dateutil.parser.parse(m[key]['_updated'])
                        m[key]['Created'] = dateutil.parser.parse(m[key]['_created'])
                        m[key]['MongoId'] = m[key]['_id']

                        # Assign new virtual
                        m[key]['ClubId'] = club_id

                        # Activities!!!
                        if 'activities' in m[key]:

                            if 'Gren' not in m[key]:
                                m[key]['Gren'] = []

                            for a in m[key]['activities']:
                                #print(a['ClubId'])
                                if int(a['ClubId']) == int(club_id) and int(a['OrgTypeId']) == 14:
                                    m[key]['Gren'].append({'ClubId': a['ClubId'],
                                                           'Name': a['ShortName'],
                                                           'OrgId': a['OrgId'],
                                                           'OrgTypeId': a['OrgTypeId'],
                                                           'OrgTypeName': a['OrgTypeName'],
                                                           'IsPassive': a['IsPassive'],
                                                           'FunctionId': a['FunctionId']})

                        #IsActive = Boolean
                        #ClubId = Integer
                        #PaymentStatus = Integer
                        if club_id in m[key]['clubs_active']:
                            m[key]['IsActive'] = True
                        elif club_id in m[key]['clubs_inactive']:
                            m[key]['IsActive'] = False

                        if 'clubs_payment' in m[key]:
                            for k, v in enumerate(m[key]['clubs_payment']):
                                if int(v['ClubId']) == int(club_id):
                                    m[key]['PaymentStatus'] = v['PaymentStatus']
                                    break
                                    # print(m[key])
                        # exit(0)
                    return m
            else:
                return {'status': 'ERR', 'status_code': 404}
        else:
            return {'status': 'ERR', 'status_code': 403}

    @srpc(Unicode, Unicode, Integer, _returns=MelwinUpdated)
    def set_melwin_id(ApiKey, PersonId, MelwinId):
        """
        Set MelwinId for Person
        @Param ApiKey
        @param PersonId
        @param MelwinId
        @return
        """

        if ApiKey == api.key:

            user_resp = requests.get('%s/members/%s' % (get_api_url(), PersonId),
                                     headers=get_api_headers())

            if user_resp.status_code == 200:
                user = user_resp.json()

                user_header = get_api_headers()
                user_header.update({'If-Match': user['_etag']})

                update_resp = requests.patch('%s/members/%s' % (get_api_url(), user['_id']),
                                             json={'MelwinId': MelwinId},
                                             headers=user_header)

                #print(update_resp.text)
                #print(update_resp.status_code)
                if update_resp.status_code == 200:
                    return {'status': 'OK', 'status_code': update_resp.status_code, 'PersonId': PersonId,
                            'MelwinId': MelwinId}
                else:
                    return {'status': 'ERR', 'status_code': user_resp.status_code, 'PersonId': PersonId,
                            'MelwinId': MelwinId}

            else:
                return {'status': 'ERR', 'status_code': user_resp.status_code, 'PersonId': PersonId,
                        'MelwinId': MelwinId}
        else:
            return {'status': 'ERR', 'status_code': 403}

    @srpc(Unicode, Integer, Unicode, _returns=Iterable(Org))
    def get_grener(ApiKey, ClubId, Direction='up'):
        """
        Set MelwinId for Person
        @Param ApiKey Unicode mandatory
        @param ClubId Integer mandatory
        @param Direction up or down, default 'up', 'up'|'down'
        @return
        """

        if ApiKey == api.key:

            if Direction in ['up', 'down']:

                if Direction == 'up':
                    Direction = 'down'
                else:
                    Direction = 'up'

                #, "OrgType": "Gruppe for særidrett"
                url = '%s/orgs?where={"_%s": {"$in": [%s]}}' % (
                get_api_url(), Direction, ClubId)

                resp = requests.get(url, headers=get_api_headers())

                if resp.status_code == 200:
                    ret = resp.json()['_items']
                    r = []
                    for k, v in enumerate(ret):
                        if '_links' in v:
                            del ret[k]['_links']
                    #from pprint import pprint
                    #pprint(ret)
                    return ret
                else:
                    return {'status': 'ERR', 'status_code': resp.status_code, 'Message': resp.text}
            else:
                return {'status': 'ERR', 'status_code': 422}
        else:
            return {'status': 'ERR', 'status_code': 403}


    @srpc(Unicode, Unicode, Unicode, Unicode, _returns=LoginResponse)
    def login_simple(ApiKey, Username, Password, Realm='mi.nif.no'):
        """
        Login via NIF Buypass
        @Param ApiKey Unicode mandatory
        @param Username Integer mandatory
        @param Password
        @return
        """

        person_id = None
        melwin_id = None

        pb = passbuy.passbuy(realm=Realm, username=Username, password=Password)
        try:
            fed_cookie = pb.login()
        except AttributeError:
            return {'Message': 'Wrong password or user', 'Status': 'ERR', 'StatusCode': 401}
        except Exception as e:
            return {'Message': 'Wrong password or user', 'Status': 'ERR', 'StatusCode': 401}

        if fed_cookie:
            if isinstance(fed_cookie, requests.cookies.RequestsCookieJar):
                person_id = pb.get_id_from_profile()
                melwin_id = get_melwin_id(person_id)
                return {'Message': 'Success', 'Status': 'OK', 'StatusCode': 200, 'MelwinId': melwin_id, 'PersonId': person_id}
            else:
                return {'Message': 'Success', 'Status': 'OK', 'StatusCode': 200, 'MelwinId': None,
                            'PersonId': None}

    @rpc(Unicode, Unicode, _returns=LoginResponse)
    def login(ctx, ApiKey, Realm='mi.nif.no'):
        """
        Login via NIF Buypass WSSE header
        @Param ApiKey Unicode mandatory
        @return
        """
        Username, Password = get_credentials(ctx)
        pb = passbuy.passbuy(realm=Realm, username=Username, password=Password)

        try:
            fed_cookie = pb.login()
        except AttributeError:
            return {'Message': 'Wrong password or user', 'Status': 'ERR', 'StatusCode': 401}
        except Exception as e:
            return {'Message': 'Wrong password or user', 'Status': 'ERR', 'StatusCode': 401}

        if fed_cookie:
            if isinstance(fed_cookie, requests.cookies.RequestsCookieJar):
                return {'Message': 'Success', 'Status': 'OK', 'StatusCode': 200}

if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    #wsgi_app = wsgi_soap_application([MelwinService], 'spyne.melwin.soap')
    app = Application([MelwinService], tns='spyne.melwin.soap', in_protocol=Soap11(validator='lxml'), out_protocol=Soap11())
    wsgi_app = WsgiApplication(app)
    server = make_server('127.0.0.1', 8000, wsgi_app)
    server.serve_forever()