from flask import Flask, jsonify, request
import socket
import sys
from datetime import datetime

app = Flask(__name__)

@app.route('/data')
def get_data():
    """
    This endpoint is ONLY accessible from within the Docker backend network.
    External requests cannot reach this service.
    """
    return jsonify({
        'message': 'This is internal data - only accessible from backend network',
        'service': 'internal-api',
        'hostname': socket.gethostname(),
        'python_version': sys.version.split()[0],
        'timestamp': datetime.now().isoformat(),
        'network': 'backend (internal only)',
        'proxy_headers': {
            'x_proxy_name': request.headers.get('X-Proxy-Name'),
            'x_forwarded_for': request.headers.get('X-Forwarded-For'),
            'x_forwarded_proto': request.headers.get('X-Forwarded-Proto'),
            'host': request.headers.get('Host')
        },
        'secret_data': {
            'database_host': 'db.internal',
            'cache_server': 'redis.internal',
            'api_key': 'internal-secret-key-12345'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'internal-api'
    })

@app.route('/')
def index():
    """Root endpoint with service information"""
    return jsonify({
        'service': 'Internal API Service',
        'description': 'This service is only accessible within the backend network',
        'endpoints': {
            '/data': 'Get internal data',
            '/health': 'Health check'
        },
        'network_note': 'This service is NOT exposed to external traffic'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
