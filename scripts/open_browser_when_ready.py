"""Open Nova only after the selected local server answers HTTP."""
import sys
import time
import urllib.error
import urllib.request
import webbrowser

port = int(sys.argv[1])
url = f"http://127.0.0.1:{port}/"
for _ in range(60):
    try:
        request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=1) as response:
            if response.status == 200:
                body = response.read().decode("utf-8", errors="replace")
                if "inline-chat-fallback-20261026" in body:
                    webbrowser.open(url)
                    raise SystemExit(0)
    except (OSError, urllib.error.URLError, TimeoutError):
        pass
    time.sleep(0.5)
raise SystemExit("Nova did not respond with the updated UI within 30 seconds.")
