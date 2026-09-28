"""Select bindable loopback ports and adapt known development-server commands."""
import errno
import json
import os
from pathlib import Path
import re
import socket
from urllib.parse import urlsplit, urlunsplit


def url_port(url):
    parsed = urlsplit(url)
    return parsed.port or (443 if parsed.scheme == 'https' else 80)


def with_port(url, port):
    parsed = urlsplit(url)
    host = f'[{parsed.hostname}]' if ':' in parsed.hostname else parsed.hostname
    return urlunsplit(parsed._replace(netloc=f'{host}:{port}'))


def port_available(port):
    """Bind, rather than just connect: also catches reserved and bound-only ports."""
    sockets = []
    try:
        for family, address in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
            if family == socket.AF_INET6 and not socket.has_ipv6:
                continue
            try:
                sock = socket.socket(family, socket.SOCK_STREAM)
                sockets.append(sock)
                if os.name == 'nt':
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                sock.bind((address, port))
            except OSError as exc:
                if family == socket.AF_INET6 and exc.errno in (errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL, 10047, 10049):
                    continue  # IPv6 is disabled on this machine.
                return False
        return True
    finally:
        for sock in sockets:
            sock.close()


def choose_port(preferred=3000, reserved=()):
    reserved = set(reserved)
    start = max(1024, min(int(preferred), 65535))
    # Wrap at 65535 and bound work if a firewall excludes large port ranges.
    for offset in range(4096):
        port = 1024 + (start - 1024 + offset) % (65536 - 1024)
        if port not in reserved and port_available(port):
            return port
    raise RuntimeError('Could not find a free local port. Check Windows port exclusions and try again.')


def _tokens(command):
    return [token.strip('"\'') for token in re.findall(r'"[^"\n]*"|\'[^\'\n]*\'|[^\s]+', command)]


def _server(command):
    tokens = _tokens(command)
    if not tokens or re.search(r'[&|<>;]', command):
        return None
    executable = re.split(r'[/\\]', tokens[0])[-1].lower()
    executable = re.sub(r'\.(?:exe|cmd|bat)$', '', executable)
    if executable in ('python', 'python3', 'py') and '-m' in tokens:
        index = tokens.index('-m') + 1
        executable = tokens[index] if index < len(tokens) else ''
    elif executable == 'npx' and len(tokens) > 1:
        executable = tokens[1]
    if executable in ('vite', 'next', 'uvicorn', 'streamlit', 'flask', 'http.server', 'react-scripts'):
        return executable
    return None


def _flag(command, names, value):
    pattern = r'(?<!\S)(' + '|'.join(re.escape(name) for name in names) + r')(?:\s+|=)(?:"\d+"|\'\d+\'|\d+)(?=\s|$)'
    updated, count = re.subn(pattern, lambda match: f'{match.group(1)} {value}', command)
    return updated, bool(count)


def command_for_port(command, folder, port):
    """Never rewrite project files or guess at arbitrary application's source code."""
    env = {'PORT': str(port), 'LAUNCHPAD_PORT': str(port), 'UVICORN_PORT': str(port),
           'STREAMLIT_SERVER_PORT': str(port), 'FLASK_RUN_PORT': str(port), 'BROWSER': 'none'}
    if '{port}' in command:
        return command.replace('{port}', str(port)), env
    if re.search(r'[&|<>;]', command):
        return command, env  # Explicit template or PORT is needed for shell pipelines.
    server = _server(command)
    npm = re.match(r'^\s*npm(?:\.cmd)?\s+(?:run(?:-script)?\s+([\w:.-]+)|(start))(?=\s|$)', command, re.I)
    if npm:
        try:
            package = json.loads((Path(folder) / 'package.json').read_text(encoding='utf-8-sig'))
            server = _server(package.get('scripts', {}).get(npm.group(1) or 'start', ''))
        except (OSError, ValueError):
            server = None
        # Only forward flags where the script's CLI is known to accept them.
        if server not in ('vite', 'next'):
            return command, env
    if server == 'react-scripts':
        return command, env  # CRA reads PORT and does not take --port.
    if server == 'http.server':
        return re.sub(r'(?<!\S)http\.server(?:\s+\d+(?=\s|$))?', f'http.server {port}', command, count=1), env
    flags = ('--server.port',) if server == 'streamlit' else ('--port', '-p')
    command, replaced = _flag(command, flags, port)
    if not replaced and server:
        if npm and not re.search(r'\s--(?:\s|$)', command):
            command += ' --'
        command += f' {flags[0]} {port}'
    if server == 'vite' and '--strictPort' not in command:
        command += ' --strictPort'
    return command, env
