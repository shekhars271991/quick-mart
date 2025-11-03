#!/usr/bin/env python3
"""
Simple script to test Aerospike Cloud connection
Run this on the client machine to verify connectivity
"""

import aerospike
import os
import sys

# Configuration
AEROSPIKE_HOST = os.getenv("AEROSPIKE_HOST", "ea16c08d-aa99-4b7c-bc41-2467b24b8e58.aerospike.internal")
AEROSPIKE_PORT = int(os.getenv("AEROSPIKE_PORT", "4000"))
AEROSPIKE_USE_TLS = os.getenv("AEROSPIKE_USE_TLS", "true").lower() in ("true", "1", "yes")
AEROSPIKE_TLS_CAFILE = os.getenv("AEROSPIKE_TLS_CAFILE", "ascloud.ca")
AEROSPIKE_TLS_NAME = os.getenv("AEROSPIKE_TLS_NAME", "ea16c08d-aa99-4b7c-bc41-2467b24b8e58.aerospike.internal")
AEROSPIKE_USERNAME = os.getenv("AEROSPIKE_USERNAME", "adminas")
AEROSPIKE_PASSWORD = os.getenv("AEROSPIKE_PASSWORD", "admin12345")
AEROSPIKE_NAMESPACE = os.getenv("AEROSPIKE_NAMESPACE", "churnprediction")

def test_connection():
    """Test Aerospike Cloud connection"""
    print("=" * 70)
    print("Aerospike Cloud Connection Test")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Host: {AEROSPIKE_HOST}")
    print(f"  Port: {AEROSPIKE_PORT}")
    print(f"  TLS Enabled: {AEROSPIKE_USE_TLS}")
    print(f"  TLS CA File: {AEROSPIKE_TLS_CAFILE} (exists: {os.path.exists(AEROSPIKE_TLS_CAFILE)})")
    print(f"  TLS Name (SNI): {AEROSPIKE_TLS_NAME}")
    print(f"  Username: {AEROSPIKE_USERNAME}")
    print(f"  Namespace: {AEROSPIKE_NAMESPACE}")
    
    # Build configuration
    # For Aerospike Cloud, try disabling peer discovery to use only seed node
    config = {
        'hosts': [(AEROSPIKE_HOST, AEROSPIKE_PORT)],
        'policies': {
            'write': {'key': aerospike.POLICY_KEY_SEND},
            'timeout': 30000,  # 30 second timeout
            'max_retries': 3,
            'sleep_between_retries': 1000  # 1 second between retries
        }
    }
    
    # Try to disable peer discovery - this might help with Aerospike Cloud
    # Some versions support this parameter to avoid cluster discovery issues
    try:
        # Use direct connection without cluster discovery
        config['use_services_alternate'] = False
    except:
        pass
    
    # Add TLS configuration
    if AEROSPIKE_USE_TLS:
        tls_config = {}
        if AEROSPIKE_TLS_CAFILE and os.path.exists(AEROSPIKE_TLS_CAFILE):
            tls_config['cafile'] = os.path.abspath(AEROSPIKE_TLS_CAFILE)
            print(f"\n✅ Using CA file: {os.path.abspath(AEROSPIKE_TLS_CAFILE)}")
        else:
            print(f"\n❌ CA file not found: {AEROSPIKE_TLS_CAFILE}")
            return False
        
        if AEROSPIKE_TLS_NAME:
            tls_config['name'] = AEROSPIKE_TLS_NAME
            print(f"✅ Using SNI: {AEROSPIKE_TLS_NAME}")
        
        if tls_config:
            config['tls'] = tls_config
        else:
            print("\n❌ TLS enabled but no valid CA file provided")
            return False
    
    # Add authentication
    if AEROSPIKE_USERNAME and AEROSPIKE_PASSWORD:
        config['auth'] = {
            'username': AEROSPIKE_USERNAME,
            'password': AEROSPIKE_PASSWORD
        }
        print(f"✅ Using authentication: {AEROSPIKE_USERNAME}")
    
    # Test DNS resolution
    print(f"\n🔍 Testing DNS resolution...")
    try:
        import socket
        ip_addresses = socket.gethostbyname_ex(AEROSPIKE_HOST)[2]
        print(f"✅ DNS resolved to: {', '.join(ip_addresses)}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    
    # Test TCP connectivity
    print(f"\n🔍 Testing TCP connectivity to {AEROSPIKE_HOST}:{AEROSPIKE_PORT}...")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((AEROSPIKE_HOST, AEROSPIKE_PORT))
        sock.close()
        if result == 0:
            print(f"✅ TCP connection successful")
        else:
            print(f"❌ TCP connection failed (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ TCP test failed: {e}")
        return False
    
    # Test Aerospike connection
    print(f"\n🔗 Attempting Aerospike connection...")
    print(f"   Config: hosts={config['hosts']}")
    if 'tls' in config:
        print(f"   TLS: cafile={config['tls'].get('cafile')}, name={config['tls'].get('name')}")
    if 'auth' in config:
        print(f"   Auth: username={config['auth']['username']}")
    
    try:
        client = aerospike.client(config)
        print("✅ Client created successfully")
        
        print("   Connecting...")
        client.connect()
        print("✅ Connected to Aerospike!")
        
        # Test cluster info
        print("\n📊 Retrieving cluster information...")
        info = client.info_all("build")
        print(f"✅ Retrieved info from {len(info)} node(s)")
        for node, data in list(info.items())[:3]:  # Show first 3 nodes
            print(f"   Node {node}: {data[:50]}...")
        
        # Test namespace access
        print(f"\n📦 Testing namespace '{AEROSPIKE_NAMESPACE}'...")
        ns_info = client.info_all(f"namespace/{AEROSPIKE_NAMESPACE}")
        print(f"✅ Namespace '{AEROSPIKE_NAMESPACE}' is accessible")
        
        client.close()
        
        print("\n" + "=" * 70)
        print("🎉 SUCCESS! All connection tests passed!")
        print("=" * 70)
        return True
        
    except aerospike.exception.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print(f"   Error details: {type(e).__name__}")
        if hasattr(e, 'code'):
            print(f"   Error code: {e.code}")
        if hasattr(e, 'msg'):
            print(f"   Error message: {e.msg}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

