"""Servidor HTTPS para desarrollo local (solo pruebas en la LAN).

`getUserMedia` (escáner QR, RF-04.1) sólo existe en "contextos seguros"; el
móvil que entra por `https://192.168.x.x` necesita que este backend también
responda por HTTPS y con un certificado aceptado por el teléfono.

Se implementa directamente sobre `runserver` (ASGI/Daphne + `ssl.SSLContext`)
en lugar de `django-sslserver`, que usa `ssl.wrap_socket` (eliminado en
Python 3.12) y no arranca en las versiones actuales.

Uso (desde `backend/`, con el entorno virtual activo):

    python manage.py runhttps 0.0.0.0:8000
    python manage.py runhttps 0.0.0.0:8000 --certfile cert.pem --keyfile key.pem

Sin `--certfile` se genera un certificado autofirmado (incluye la IP local para
que el móvil pueda validarlo una vez que instala/acepta el certificado).
"""

import functools
import ipaddress
import os
import socket
import ssl
import subprocess
import tempfile

from django.core.management.commands.runserver import Command as RunserverCommand
from django.core.servers.basehttp import ThreadedWSGIServer


def _lan_ip():
    """IP de la laptop en la red WiFi (sin enviar tráfico real)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.168.1.1", 80))
            return sock.getsockname()[0]
    except OSError:
        return "192.168.1.27"


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _openssl_certificate(directory, hosts):
    """Genera cert.pem/key.pem con openssl (sin dependencias adicionales)."""
    certfile = os.path.join(directory, "cert.pem")
    keyfile = os.path.join(directory, "key.pem")
    san = ",".join(
        f"IP:{host}" if _is_ip(host) else f"DNS:{host}" for host in hosts
    )
    subprocess.run(
        [
            "openssl", "req", "-x509", "-nodes", "-days", "365", "-newkey", "rsa:2048",
            "-keyout", keyfile, "-out", certfile,
            "-subj", "/CN=SIGACU desarrollo",
            "-addext", f"subjectAltName={san}",
        ],
        check=True,
        capture_output=True,
    )
    return certfile, keyfile


def build_ssl_context(certfile=None, keyfile=None):
    """Devuelve (SSLContext, ruta_certificado)."""
    if not certfile:
        directory = os.path.join(tempfile.gettempdir(), "sigacu-certs")
        os.makedirs(directory, exist_ok=True)
        certfile, keyfile = _openssl_certificate(
            directory, ["localhost", "127.0.0.1", _lan_ip()]
        )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context, certfile


class SecureWSGIServer(ThreadedWSGIServer):
    """Servidor de desarrollo que envuelve el socket con TLS.

    `ssl_context` se inyecta con `functools.partial` (ver `init_https`):
    `runserver` instancia `server_cls(addr, handler, ipv6=…)` y Daphne reutiliza
    esa misma clase a través de su adaptador WSGI→ASGI.
    """

    def __init__(self, *args, ssl_context=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket = ssl_context.wrap_socket(self.socket, server_side=True)


def init_https(certfile=None, keyfile=None):
    """Genera el contexto TLS y devuelve el `server_cls` listo para runserver."""
    context, cert = build_ssl_context(certfile, keyfile)
    return functools.partial(SecureWSGIServer, ssl_context=context), cert


class Command(RunserverCommand):
    help = "runserver sobre HTTPS con certificado local (solo desarrollo)."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--certfile", help="Certificado PEM (por defecto autofirmado).")
        parser.add_argument("--keyfile", help="Clave privada PEM (por defecto autofirmada).")

    def handle(self, *args, **options):
        self.server_cls, certfile = init_https(
            options.get("certfile"), options.get("keyfile")
        )
        self.stdout.write(self.style.SUCCESS(f"Certificado: {certfile}"))
        self.stdout.write(
            self.style.WARNING(
                "HTTPS local: acepte el aviso de 'conexión no privada' en el móvil "
                "para que la cámara funcione."
            )
        )
        return super().handle(*args, **options)
