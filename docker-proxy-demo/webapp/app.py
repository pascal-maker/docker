from flask import Flask, render_template, jsonify, request
import os
import sys
import socket
import requests
from datetime import datetime

app = Flask(__name__)

# Get instance information from environment variables
INSTANCE_NAME = os.getenv('INSTANCE_NAME', 'Unknown')
INSTANCE_COLOR = os.getenv('INSTANCE_COLOR', '#6C757D')

@app.route('/')
def index():
    """Main page showing which instance is serving the request"""
    hostname = socket.gethostname()
    proxy_context = {
        'proxy_name': request.headers.get('X-Proxy-Name', 'not-set'),
        'forwarded_for': request.headers.get('X-Forwarded-For', 'not-set'),
        'forwarded_proto': request.headers.get('X-Forwarded-Proto', 'not-set'),
    }
    
    # Try to get data from internal API
    internal_data = None
    try:
        response = requests.get('http://internal-api:5000/data', timeout=2)
        if response.status_code == 200:
            internal_data = response.json()
    except Exception as e:
        internal_data = {'error': str(e)}
    
    return render_template('index.html', 
                         instance_name=INSTANCE_NAME,
                         instance_color=INSTANCE_COLOR,
                         hostname=hostname,
                         timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                         internal_data=internal_data,
                         proxy_context=proxy_context)

@app.route('/api/info')
def api_info():
    """API endpoint returning instance information"""
    return jsonify({
        'instance': INSTANCE_NAME,
        'hostname': socket.gethostname(),
        'timestamp': datetime.now().isoformat(),
        'color': INSTANCE_COLOR,
        'python_version': sys.version.split()[0],
        'proxy_headers': {
            'x_proxy_name': request.headers.get('X-Proxy-Name'),
            'x_forwarded_for': request.headers.get('X-Forwarded-For'),
            'x_forwarded_proto': request.headers.get('X-Forwarded-Proto')
        }
    })

@app.route('/api/proxy-context')
def api_proxy_context():
    """Shows headers injected by the reverse proxy"""
    return jsonify({
        'proxy_name': request.headers.get('X-Proxy-Name'),
        'x_real_ip': request.headers.get('X-Real-IP'),
        'x_forwarded_for': request.headers.get('X-Forwarded-For'),
        'x_forwarded_proto': request.headers.get('X-Forwarded-Proto'),
        'host': request.headers.get('Host')
    })

@app.route('/api/dual-access-demo')
def dual_access_demo():
    """Demonstrates accessing the same service via two different routes"""
    results = {
        'direct_access': {'url': 'http://host.docker.internal:5050/info'},
        'proxied_access': {'url': 'http://proxy:80/external-project/info'}
    }
    
    # Fetch from direct host port (external-web published port)
    try:
        response = requests.get('http://host.docker.internal:5050/info', timeout=2)
        results['direct_access']['status'] = response.status_code
        results['direct_access']['data'] = response.json()
    except Exception as e:
        results['direct_access']['error'] = str(e)
    
    # Fetch via proxy route
    try:
        response = requests.get('http://proxy:80/external-project/info', timeout=2)
        results['proxied_access']['status'] = response.status_code
        results['proxied_access']['data'] = response.json()
    except Exception as e:
        results['proxied_access']['error'] = str(e)
    
    return jsonify(results)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'instance': INSTANCE_NAME})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
