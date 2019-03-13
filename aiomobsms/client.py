import asyncio
import json
import logging

import aiohttp

logger = logging.getLogger(__name__)


class MobSmsClient:
    class TimeoutError(Exception):
        pass

    class SmsBizException(Exception):

        message_mappings = {
            200: '验证成功',
            405: 'AppKey为空',
            406: 'AppKey无效',
            456: '国家代码或手机号码为空',
            457: '手机号码格式错误',
            466: '请求校验的验证码为空',
            467: '请求校验验证码频繁（5分钟内同一个appkey的同一个号码最多只能校验三次）',
            468: '验证码错误',
            474: '没有打开服务端验证开关',
        }

        def __init__(self, code=None, message=None):
            self.code = code
            if message:
                self.message = message
            else:
                self.message = self.message_mappings.get(code)

        def __str__(self):
            return 'Mob Sms Error code: {}, message {}'.format(self.code, self.message)

    VERIFY_URL = 'https://webapi.sms.mob.com/sms/verify'

    def __init__(self, app_key, timeout=5):
        conn = aiohttp.TCPConnector(limit=1024)
        self._session = aiohttp.ClientSession(
            connector=conn,
            skip_auto_headers={'Content-Type'},
        )
        self.app_key = app_key
        self.timeout = timeout

    async def verify(self, phone, zone, code):
        try:
            params = {
                'appkey': self.app_key,
                'phone': phone,
                'zone': zone,
                'code': code,
            }
            async with self._session.get(self.VERIFY_URL, params=params,
                                         timeout=self.timeout) as resp:
                if resp.status != 200:
                    raise self.SmsBizException(resp.status)
                body = await resp.text()
        except asyncio.TimeoutError:
            raise self.TimeoutError()

        result = json.loads(body)
        if result.get('status') != 200:
            logger.error('aiomobsms error, result: %s', body)
            raise self.SmsBizException(
                code=result.get('status'),
            )
        return json.loads(body)

    def __del__(self):
        if not self._session.closed:
            if self._session._connector is not None \
                    and self._session._connector_owner:
                self._session._connector.close()
            self._session._connector = None
