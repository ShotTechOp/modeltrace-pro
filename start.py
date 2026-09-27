from __future__ import annotations

import os
import sys
import threading
import webbrowser

sys.dont_write_bytecode = True

from app import app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Only open browser if running locally interactively (not in Railway/Docker/headless)
    if os.environ.get("RAILWAY_ENVIRONMENT") is None and os.environ.get("DOCKER_CONTAINER") is None and not os.environ.get("PORT"):
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        
    print(f"Starting ModelTrace Server on http://{host}:{port} ...")
    app.run(host=host, port=port, debug=False)
