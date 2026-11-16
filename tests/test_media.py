import socket

import pytest

from app import media
from app.media import validate_url

PUBLIC_IP = '93.184.216.34'


def resolver(*ips):
    def getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port)) for ip in ips]
    return getaddrinfo


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(media.socket, 'getaddrinfo', resolver(PUBLIC_IP))


@pytest.mark.parametrize('url', [
    'https://youtube.com/watch?v=test',
    'https://www.youtube.com/watch?v=test',
    'https://m.youtube.com/watch?v=test',
    'https://youtu.be/test',
    'https://vimeo.com/1',
    'https://x.com/a/status/1',
    'https://twitter.com/a/status/1',
    'https://youtube.com:443/watch?v=test',
])
def test_allowed_hosts_pass(url):
    validate_url(url)


@pytest.mark.parametrize('url', [
    'http://youtube.com/watch?v=test',
    'https://user:pw@youtube.com/watch?v=test',
    'https://user@youtube.com/watch?v=test',
    'https://youtube.com:8443/watch?v=test',
    'ftp://youtube.com/watch?v=test',
    'https:///watch?v=test',
])
def test_scheme_credentials_and_port_rejected(url):
    with pytest.raises(ValueError, match='public HTTPS'):
        validate_url(url)


@pytest.mark.parametrize('url', [
    'https://notyoutube.com/',
    'https://youtube.com.evil.example/',
    'https://example.com/',
])
def test_hosts_outside_allow_list_rejected(url):
    with pytest.raises(ValueError, match='YouTube, Vimeo, or X'):
        validate_url(url)


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.5', '::1'])
def test_private_addresses_rejected(monkeypatch, ip):
    monkeypatch.setattr(media.socket, 'getaddrinfo', resolver(ip))
    with pytest.raises(ValueError, match='Private network links are not supported.'):
        validate_url('https://youtube.com/watch?v=test')


def test_any_private_address_among_results_rejected(monkeypatch):
    monkeypatch.setattr(media.socket, 'getaddrinfo', resolver(PUBLIC_IP, '10.0.0.5'))
    with pytest.raises(ValueError, match='Private network links are not supported.'):
        validate_url('https://youtube.com/watch?v=test')


def test_empty_resolution_rejected(monkeypatch):
    monkeypatch.setattr(media.socket, 'getaddrinfo', resolver())
    with pytest.raises(ValueError, match='Private network links are not supported.'):
        validate_url('https://youtube.com/watch?v=test')


def test_resolution_failure_reports_unreachable_host(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror('no such host')
    monkeypatch.setattr(media.socket, 'getaddrinfo', fail)
    with pytest.raises(ValueError, match='Could not reach that video host.'):
        validate_url('https://youtube.com/watch?v=test')
