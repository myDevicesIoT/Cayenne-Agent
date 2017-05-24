from myDevices.requests_futures.sessions import FuturesSession
from concurrent.futures import ThreadPoolExecutor
import json
from myDevices.utils.logger import error, exception

class CayenneApiClient:
    def __init__(self, host):
        self.host = host
        self.auth = None
        self.session = FuturesSession(executor=ThreadPoolExecutor(max_workers=1))

    def sendRequest(self, method, uri, body=None):
        if self.session is not None:
            headers = {}
            request_url = self.host + uri
            future = None
            self.session.headers['Content-Type'] = 'application/json'
            self.session.headers['Accept'] = 'application/json'
            if self.auth is not None:
                self.session.headers['Authorization'] = self.auth
            try:
                if method == 'GET':
                    future = self.session.get(request_url)
                if method == 'POST':
                    future = self.session.post(request_url, data=body)
                if method == 'PUT':
                    future = self.session.put(request_url, data=body)
                if method == 'DELETE':
                    future = self.session.delete(request_url)
            except Exception as ex:
                error('sendRequest exception: ' + str(ex))
                return None
            try:
                response = future.result()
            except:
                return None
            return response
        exception("No data received")

    def authenticate(self, inviteCode):
        body = json.dumps({'id': inviteCode})
        url = '/things/key/authenticate'
        return self.sendRequest('POST', url, body)

    def activate(self, inviteCode):
        body = json.dumps({'id': inviteCode})
        url = '/things/key/activate'
        return self.sendRequest('POST', url, body)

    def getId(self, content):
        if content is None:
            return None
        body = content.decode("utf-8")
        if body is None or body is "":
            return None
        return json.loads(body)['id']

    def loginDevice(self, inviteCode):
        response = self.authenticate(inviteCode)
        if response and response.status_code == 200:
            return self.getId(response.content)
        if not response or response.status_code == 412:
            response = self.activate(inviteCode)
            if response and response.status_code == 200:
                return self.getId(response.content)
        return None
