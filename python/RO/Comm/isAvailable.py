import socket

__all__ = ["isAvailable"]

def isAvailable(port, family=socket.AF_INET, sockType=socket.SOCK_STREAM):
    """Return True if the specified socket is available, False otherwise
    """
    s = socket.socket(family, sockType)
    try:
        s.connect(("localhost", port))
        s.close()
        return False
    except Exception:
        return True
