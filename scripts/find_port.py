"""Find a likely free localhost port for Nova without killing other processes."""
import socket

for candidate in range(8000, 8100):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", candidate))
        except OSError:
            continue
        print(candidate)
        break
else:
    raise SystemExit("No free port available in the range 8000-8099.")
