from flask import Flask, jsonify, request
import os
import socket
import sys
from datetime import datetime

app = Flask(__name__)

if sys.version_info < (3, 14):
    raise RuntimeError("Python 3.14+ is required")

INSTANCE_NAME = os.getenv("INSTANCE_NAME", "External-Web")
INSTANCE_COLOR = os.getenv("INSTANCE_COLOR", "#9775FA")


@app.route("/")
def root():
    return jsonify(
        {
            "service": INSTANCE_NAME,
            "description": "Separate compose project service on shared external frontend network",
            "endpoints": ["/info", "/health"],
        }
    )


@app.route("/info")
def info():
    return jsonify(
        {
            "service": INSTANCE_NAME,
            "hostname": socket.gethostname(),
            "color": INSTANCE_COLOR,
            "python_version": sys.version.split()[0],
            "timestamp": datetime.now().isoformat(),
            "network_note": "This service runs in a separate Compose project but joins the same frontend network",
            "proxy_headers": {
                "x_proxy_name": request.headers.get("X-Proxy-Name"),
                "x_forwarded_for": request.headers.get("X-Forwarded-For"),
                "x_forwarded_proto": request.headers.get("X-Forwarded-Proto"),
                "host": request.headers.get("Host"),
            },
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": INSTANCE_NAME})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
