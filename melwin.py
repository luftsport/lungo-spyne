from spyne import rpc, srpc, ServiceBase, ComplexModel, Iterable, Integer, Unicode, Boolean, Date, DateTime

from spyne.util.simple import wsgi_soap_application

import logging
import dateutil.parser
import requests
import api

# print(spyne._version)PersonID, Etternavn, Fornavn, fødselsdato ,kjønn, epost, mobiltelefon Postadresse, postnummer
# Takes the return and transforms to
class Person(ComplexModel):
    Id = Integer
    MelwinId = Integer
    Name = Unicode
    BirthDate = DateTime
    GenderId = Integer
    GenderText = Unicode
    Email = Unicode
    Phone = Unicode
    Address = Unicode
    PostNumber = Unicode
    City = Unicode
    MemberFeeStatus = Integer
    Updated = DateTime
    Created = DateTime
    MongoId = Unicode

class MelwinUpdated(ComplexModel):
    status = Unicode
    status_code = Integer
    PersonId = Integer
    MelwinId = Integer


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

class MelwinService(ServiceBase):



    @srpc(Unicode, Integer, _returns=Iterable(Unicode))
    def say_hello(name, numbers):
        """
        Docstrings for service methods appear as documentation in the wsdl
        <b>what fun</b>
        @param name the name to say hello to
        @param numbers the number of times
        @return the completed array
        """

        return u'Hello, %s' % name

    @srpc(Unicode, Boolean, _returns=Iterable(Person))
    def members(ClubId, MelwinId=False):
        """
        Members by KL number and if MelwinId or not
        @param ClubId
        @param MelwinId
        @return
        """
        club_resp = requests.get('%s/clubs/?where={"NifOrganisationNumber":"%s"}' % (get_api_url(), ClubId),
                            headers=get_api_headers())
        if club_resp.status_code != 200:
            return [{}]
        else:
            clubs = club_resp.json()['_items']

            print(clubs)

            if len(clubs) == 1:
                club_id = clubs[0]['Id']

        member_resp = requests.get('%s/members/?where={"clubs":{"$in":[%s]}}' % (get_api_url(), club_id),
                                 headers=get_api_headers())


        if member_resp.status_code != 200:
            return [{}]
        else:
            #print(member_resp.json()['_items'][0])

            m = member_resp.json()['_items']
            for key, value in enumerate(m): # strptime(modified, '%Y-%m-%dT%H:%M:%S.000Z')
                m[key]['BirthDate'] = dateutil.parser.parse(m[key]['BirthDate'])
                m[key]['Updated'] = dateutil.parser.parse(m[key]['_updated'])
                m[key]['Created'] = dateutil.parser.parse(m[key]['_created'])
                m[key]['MongoId'] = m[key]['_id']
                #print(m[key])
                #exit(0)
            return m

    @srpc(Integer, Integer, _returns=MelwinUpdated)
    def set_melwin_id(PersonId, MelwinId):

        user_resp = requests.get('%s/members/%s' % (get_api_url(), PersonId),
                                   headers=get_api_headers())

        if user_resp.status_code == 200:
            user = user_resp.json()

            user_header = get_api_headers()
            user_header.update({'If-Match': user['_etag']})

            update_resp = requests.patch('%s/members/%s' % (get_api_url(), user['_id']),
                                         json={'MelwinId': MelwinId},
                                   headers=user_header)

            print(update_resp.text)
            print(update_resp.status_code)

            return {'status': 'OK', 'status_code': update_resp.status_code, 'PersonId': PersonId, 'MelwinId': MelwinId}

        else:
            return {'status': 'ERR', 'status_code': user_resp.status_code, 'PersonId': PersonId, 'MelwinId': MelwinId}


if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    wsgi_app = wsgi_soap_application([MelwinService], 'spyne.melwin.soap')
    server = make_server('127.0.0.1', 8000, wsgi_app)
    server.serve_forever()
