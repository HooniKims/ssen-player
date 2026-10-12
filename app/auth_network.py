"""Native Qt transport: fixed server, system proxy/CAs, no redirects, bounded replies."""
import ssl
from email.utils import parsedate_to_datetime
from PySide6.QtCore import QObject, QUrl, QByteArray, QTimer
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkRequest, QNetworkProxyFactory,
                              QSslConfiguration, QSslCertificate, QSsl, QSslSocket)

BASE = 'https://ssenbox.lovable.app/api/public/v1'
PATHS = {p: 'GET' for p in ('/keys', '/status')}
PATHS.update({p: 'POST' for p in ('/challenge', '/auth/otp/send', '/auth/otp/verify',
    '/devices/register', '/devices/deactivate', '/trial/start', '/license/token',
    '/license/redeem', '/edu/reverify/send', '/edu/reverify')})
HEADERS = {'Authorization', 'X-Ssen-Reg', 'X-Ssen-Nonce', 'X-Ssen-Signature', 'X-Ssen-Old-Signature'}

def validate_request(request):
    path, method = request.get('path'), request.get('method')
    if not isinstance(path, str) or path not in PATHS or method != PATHS[path]: raise ValueError('API_NOT_ALLOWED')
    headers = request.get('headers', {})
    if not isinstance(headers, dict): raise ValueError('BAD_OPERATION')
    for key, value in headers.items():
        if key not in HEADERS or not isinstance(value, str) or len(value) > 4096 or '\r' in value or '\n' in value:
            raise ValueError('BAD_OPERATION')
    body = request.get('body', '')
    if not isinstance(body, str) or len(body.encode('utf-8')) > 1024 * 1024: raise ValueError('BAD_OPERATION')
    return path, method, headers, body.encode('utf-8')

class AuthNetwork(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        QNetworkProxyFactory.setUseSystemConfiguration(True)
        self.manager = QNetworkAccessManager(self)
        self.tls = QSslConfiguration.defaultConfiguration()
        self.tls.setProtocol(QSsl.TlsV1_2OrLater)
        self.tls.setPeerVerifyMode(QSslSocket.VerifyPeer)
        # Explicitly import the Windows enterprise roots for OpenSSL-backed Qt builds.
        certificates = self.tls.caCertificates()
        for name in ('ROOT', 'CA'):
            for raw, encoding, trust in ssl.enum_certificates(name):
                if encoding == 'x509_asn' and (trust is True or '1.3.6.1.5.5.7.3.1' in trust):
                    certificates.extend(QSslCertificate.fromData(QByteArray(raw), QSsl.Der))
        self.tls.setCaCertificates(certificates)

    def request(self, data, done):
        try: path, method, headers, body = validate_request(data)
        except ValueError as error:
            done({'bridgeError': str(error)})
            return
        request = QNetworkRequest(QUrl(BASE + path))
        request.setSslConfiguration(self.tls)
        request.setTransferTimeout(20000)
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        for key, value in dict({'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Ssen-Spec': '5.0.0'}, **headers).items():
            request.setRawHeader(key.encode('ascii'), value.encode('utf-8'))
        reply = self.manager.get(request) if method == 'GET' else self.manager.post(request, body)
        deadline = QTimer(reply)
        deadline.setSingleShot(True)
        deadline.timeout.connect(reply.abort)
        deadline.start(20000)
        received = bytearray()
        oversized = False
        def read():
            nonlocal oversized
            received.extend(bytes(reply.readAll()))
            if len(received) > 1024 * 1024:
                oversized = True
                received.clear()
                reply.abort()
        def finish():
            deadline.stop()
            read()
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            if oversized: result = {'bridgeError': 'NETWORK', 'netCause': 'TOO_LARGE', 'netVia': 'qt-system'}
            elif not status:
                result = {'bridgeError': 'NETWORK', 'netCause': reply.error().name, 'netVia': 'qt-system'}
            elif 300 <= status < 400:
                result = {'bridgeError': 'NETWORK', 'netCause': 'REDIRECT', 'netVia': 'qt-system'}
            else:
                try: date = int(parsedate_to_datetime(bytes(reply.rawHeader('Date')).decode('ascii')).timestamp())
                except Exception: date = 0
                result = {'status': status, 'body': received.decode('utf-8', errors='replace'), 'serverTime': date,
                          'spec': bytes(reply.rawHeader('x-ssen-spec')).decode('ascii', errors='replace')}
            reply.deleteLater()
            done(result)
        reply.readyRead.connect(read)
        reply.finished.connect(finish)
