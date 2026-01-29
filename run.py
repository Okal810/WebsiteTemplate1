from app import create_app

app = create_app()

if __name__ == '__main__':
    # SSL Configuration
    import os
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        print("Running with HTTPS...")
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
    else:
        print("Running with HTTP (No certificates found)...")
        app.run(host='0.0.0.0', port=5000, debug=True)
