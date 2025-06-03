#!/usr/bin/env python3
"""
Configuration for charts panel build system.
Set your Cloudflare Workers proxy URL here to enable CORS proxy functionality.
"""

# ──────────────────────────────────────────────────────────────────────────────
# CLOUDFLARE WORKERS CORS PROXY CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Set this to your Cloudflare Worker URL after deployment
# Example: "https://refinitiv-cors-proxy.your-subdomain.workers.dev"
CLOUDFLARE_PROXY_URL = "https://img-cors-proxy.haining-zha.workers.dev"

# Choose the image handling method:
# - False: Use original URLs (may have CORS issues in PDF generation)
# - True:  Use CORS proxy (Cloudflare Workers + AllOrigins fallback)
USE_CLOUDFLARE_PROXY = True

# ──────────────────────────────────────────────────────────────────────────────
# ADVANTAGES OF EACH METHOD
# ──────────────────────────────────────────────────────────────────────────────

"""
PYTHON SERVER-SIDE FETCHING (USE_CLOUDFLARE_PROXY = False):
✅ No external dependencies once built
✅ Faster page loads (local images)
✅ Works offline
✅ No rate limits
✅ More reliable for production
❌ Requires rebuild when images change
❌ Larger repository size

CLOUDFLARE WORKERS PROXY (USE_CLOUDFLARE_PROXY = True):
✅ Always shows latest images
✅ No local storage needed
✅ Smaller repository size
✅ Dynamic image URLs work
❌ Requires internet connection
❌ Subject to rate limits (100k/day free tier)
❌ External dependency
❌ Slightly slower page loads
"""

# ──────────────────────────────────────────────────────────────────────────────
# QUICK SETUP INSTRUCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def print_setup_instructions():
    """Print instructions for setting up Cloudflare Workers proxy."""
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE WORKERS SETUP INSTRUCTIONS                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Sign up at https://workers.cloudflare.com/                             │
│  2. Create a new Worker with the name 'refinitiv-cors-proxy'                │
│  3. Copy the JavaScript code from the README                               │
│  4. Deploy the worker                                                       │
│  5. Copy your worker URL and set it in config.py:                          │
│                                                                             │
│     CLOUDFLARE_PROXY_URL = "https://your-worker.workers.dev"               │
│     USE_CLOUDFLARE_PROXY = True                                             │
│                                                                             │
│  6. Run: python build.py                                                   │
│                                                                             │
│  Your worker will be available at:                                         │
│  https://refinitiv-cors-proxy.YOUR-SUBDOMAIN.workers.dev                   │
│                                                                             │
│  Free tier includes 100,000 requests/day (100x more than you need!)       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
    """)

def get_proxy_status():
    """Get the current proxy configuration status."""
    if not CLOUDFLARE_PROXY_URL:
        return "Not configured"
    elif USE_CLOUDFLARE_PROXY:
        return f"Active: {CLOUDFLARE_PROXY_URL}"
    else:
        return f"Configured but disabled: {CLOUDFLARE_PROXY_URL}"

if __name__ == "__main__":
    print("Charts Panel Configuration")
    print(f"Cloudflare Proxy: {get_proxy_status()}")
    
    if not CLOUDFLARE_PROXY_URL:
        print_setup_instructions() 