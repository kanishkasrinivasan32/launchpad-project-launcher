"""Prevent a second backend from modifying the same active session database."""
import os

from backend.config import settings


def acquire_instance_lock():
    stream = (settings.storage / 'backend.lock').open('a+b')
    try:
        stream.seek(0)
        stream.write(b'0')
        stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return stream
    except OSError:
        stream.close()
        raise RuntimeError('A dashboard backend is already using this data directory. Use the existing dashboard or stop it first.') from None
