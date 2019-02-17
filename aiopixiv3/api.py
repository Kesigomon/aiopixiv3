# -*- coding:utf-8 -*-

import os
import sys
import shutil
import json
import aiohttp

from .utils import PixivError, JsonDict


class BasePixivAPI(object):
    client_id = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
    client_secret = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'

    access_token = None
    user_id = 0
    refresh_token = None

    def __init__(self, **requests_kwargs):
        """initialize requests kwargs if need be"""
        self.requests = aiohttp.ClientSession()
        self.requests_kwargs = requests_kwargs
    
    async def __aenter__(self): 
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False
    
    async def close(self):
        await self.requests.close()

    def parse_json(self, json_str):
        """parse str into JsonDict"""

        def _obj_hook(pairs):
            """convert json object to python object"""
            o = JsonDict()
            for k, v in pairs.items():
                o[str(k)] = v
            return o

        return json.loads(json_str, object_hook=_obj_hook)

    def require_auth(self):
        if self.access_token is None:
            raise PixivError('Authentication required! Call login() or set_auth() first!')

    async def requests_call(self, method, url, headers={}, params=None, data=None, stream=False):
        """ requests http/https call for Pixiv API """
        try:
            return await self.requests.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                **self.requests_kwargs
            )
        except Exception as e:
            raise PixivError('requests %s %s error: %s' % (method, url, e))

        raise PixivError('Unknow method: %s' % method)

    def set_auth(self, access_token, refresh_token=None):
        self.access_token = access_token
        self.refresh_token = refresh_token

    async def login(self, username, password):
        return await self.auth(username=username, password=password)

    def set_client(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    async def auth(self, username=None, password=None, refresh_token=None):
        """Login with password, or use the refresh_token to acquire a new bearer token"""

        url = 'https://oauth.secure.pixiv.net/auth/token'
        headers = {
            'User-Agent': 'PixivAndroidApp/5.0.64 (Android 6.0)',
        }
        data = {
            'get_secure_url': 1,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        if (username is not None) and (password is not None):
            data['grant_type'] = 'password'
            data['username'] = username
            data['password'] = password
        elif (refresh_token is not None) or (self.refresh_token is not None):
            data['grant_type'] = 'refresh_token'
            data['refresh_token'] = refresh_token or self.refresh_token
        else:
            raise PixivError('[ERROR] auth() but no password or refresh_token is set.')

        r = await self.requests_call('POST', url, headers=headers, data=data)
        if (r.status not in [200, 301, 302]):
            if data['grant_type'] == 'password':
                raise PixivError('[ERROR] auth() failed! check username and password.\nHTTP %s: %s' % (r.status, await r.text()), header=r.headers, body=await r.text())
            else:
                raise PixivError('[ERROR] auth() failed! check refresh_token.\nHTTP %s: %s' % (r.status, await r.text()), header=r.headers, body=await r.text())

        token = None
        try:
            # get access_token
            token = self.parse_json(await r.text())
            self.access_token = token.response.access_token
            self.user_id = token.response.user.id
            self.refresh_token = token.response.refresh_token
        except:
            raise PixivError('Get access_token error! Response: %s' % (token), header=r.headers, body=await r.text())

        # return auth/token response
        return token

    async def download(self, url, referer='https://app-api.pixiv.net/'):
        """Download image to file (use 6.0 app-api)"""
        resp = await self.requests_call('GET', url, headers={ 'Referer': referer }, stream=True)
        async with resp:
            return await resp.read()
