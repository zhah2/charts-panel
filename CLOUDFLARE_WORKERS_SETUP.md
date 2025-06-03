# Cloudflare Workers CORS Proxy Setup

This guide shows you how to set up a **free** Cloudflare Workers CORS proxy to solve the Refinitiv image loading issue in your financial dashboard.

## 🎯 **Why Cloudflare Workers?**

- ✅ **100,000 requests/day** on free tier (100x more than you need)
- ✅ **Global edge network** (super fast worldwide)
- ✅ **Zero maintenance** (fully managed)
- ✅ **Built-in security** and DDoS protection
- ✅ **Easy deployment** (5 minutes setup)

## 📋 **Step-by-Step Setup**

### **Step 1: Create Cloudflare Account**

1. Go to [https://workers.cloudflare.com/](https://workers.cloudflare.com/)
2. Click **"Start building"**
3. Sign up with your email
4. Choose the **Free plan** (no credit card required)

### **Step 2: Create the Worker**

1. Click **"Create a Worker"**
2. Choose a name like `refinitiv-cors-proxy`
3. **Replace all the default code** with this:

```javascript
export default {
  async fetch(request, env, ctx) {
    // Handle preflight OPTIONS requests
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 200,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
          'Access-Control-Max-Age': '86400',
        }
      });
    }
    
    try {
      // Get the target URL from query parameter
      const url = new URL(request.url);
      const targetUrl = url.searchParams.get('url');
      
      if (!targetUrl) {
        return new Response('Missing "url" parameter', { 
          status: 400,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }
      
      // Validate URL to prevent abuse
      if (!targetUrl.startsWith('https://refini.tv/') && 
          !targetUrl.startsWith('https://refinitiv.com/')) {
        return new Response('Only Refinitiv URLs are allowed', { 
          status: 403,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }
      
      console.log(`Proxying request to: ${targetUrl}`);
      
      // Fetch the target URL
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: {
          'User-Agent': 'Cloudflare-Worker-CORS-Proxy/1.0',
          'Accept': 'image/*,*/*;q=0.8',
        },
      });
      
      if (!response.ok) {
        return new Response(`Target server error: ${response.status}`, {
          status: response.status,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }
      
      // Create new response with CORS headers
      const corsResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          ...response.headers,
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
          'Access-Control-Expose-Headers': 'Content-Length, Content-Type',
        }
      });
      
      return corsResponse;
      
    } catch (error) {
      console.error('Proxy error:', error);
      return new Response(`Proxy error: ${error.message}`, {
        status: 500,
        headers: { 'Access-Control-Allow-Origin': '*' }
      });
    }
  }
};
```

4. Click **"Save and Deploy"**

### **Step 3: Get Your Worker URL**

After deployment, your worker will be available at:
```
https://refinitiv-cors-proxy.YOUR-SUBDOMAIN.workers.dev
```

Copy this URL - you'll need it for configuration.

### **Step 4: Test Your Worker**

1. Open `test-cloudflare-proxy.html` in your browser
2. Paste your worker URL in the configuration section
3. Click **"Test Proxy Service"**
4. If successful, you should see the Refinitiv image load
5. Click **"Generate PDF"** to verify PDF generation works

### **Step 5: Configure Your Dashboard**

1. Open `config.py`
2. Set your worker URL:
```python
CLOUDFLARE_PROXY_URL = "https://refinitiv-cors-proxy.YOUR-SUBDOMAIN.workers.dev"
USE_CLOUDFLARE_PROXY = True
```

3. Rebuild your dashboard:
```bash
python build.py
```

## 🔧 **How It Works**

```
Browser Request → Cloudflare Worker → Refinitiv Server → Cloudflare Worker → Browser
                   (adds CORS headers)                    (with CORS headers)
```

1. **Browser** requests image via proxy: `https://your-worker.workers.dev?url=https://refini.tv/abc123`
2. **Cloudflare Worker** fetches the image from Refinitiv
3. **Worker** adds CORS headers and returns the image
4. **Browser** receives image with proper CORS headers ✅
5. **PDF generation** works because canvas is no longer "tainted" ✅

## 📊 **Free Tier Limits**

| Resource | Free Tier | Your Usage | Status |
|----------|-----------|------------|--------|
| Requests/day | 100,000 | ~1,000 | ✅ 100x headroom |
| CPU time/request | 10ms | ~1ms | ✅ 10x headroom |
| Memory | 128MB | ~1MB | ✅ 128x headroom |

**You'll use less than 1% of the free tier limits!**

## 🔒 **Security Features**

- ✅ **URL validation**: Only allows Refinitiv domains
- ✅ **DDoS protection**: Built into Cloudflare
- ✅ **Rate limiting**: Automatic protection
- ✅ **Global CDN**: Fast worldwide performance

## 🆚 **Comparison: Python vs Cloudflare**

| Feature | Python Server-Side | Cloudflare Workers |
|---------|-------------------|-------------------|
| **Setup** | ✅ Already working | ⚠️ 5 min setup |
| **Speed** | ✅ Very fast (local) | ✅ Fast (global CDN) |
| **Reliability** | ✅ No dependencies | ✅ 99.9% uptime |
| **Maintenance** | ✅ Zero | ✅ Zero |
| **Cost** | ✅ Free | ✅ Free |
| **Real-time updates** | ❌ Rebuild needed | ✅ Always latest |
| **Offline use** | ✅ Works offline | ❌ Needs internet |
| **Repository size** | ❌ Large (images) | ✅ Small |
| **External dependency** | ✅ None | ⚠️ Cloudflare |

## 🚀 **Quick Start Commands**

```bash
# Test current configuration
python config.py

# Build with Python method (default)
python build.py

# Switch to Cloudflare proxy
# 1. Edit config.py:
#    USE_CLOUDFLARE_PROXY = True
#    CLOUDFLARE_PROXY_URL = "your-worker-url"
# 2. Rebuild:
python build.py
```

## 🔍 **Troubleshooting**

### **Worker not found error**
- ✅ Check the worker URL is correct
- ✅ Ensure worker is deployed (not just saved)
- ✅ Test worker directly: `https://your-worker.workers.dev?url=https://refini.tv/4gm0WdA`

### **403 Forbidden error**
- ✅ Ensure you're only using Refinitiv URLs
- ✅ Check URL encoding is correct

### **PDF still blank**
- ✅ Test with `test-cloudflare-proxy.html` first
- ✅ Check browser console for errors
- ✅ Verify worker logs in Cloudflare dashboard

### **Rate limit exceeded**
- ✅ You're unlikely to hit this (100k requests/day)
- ✅ Consider upgrading to paid plan if needed

## 📈 **Monitoring**

1. Go to [Cloudflare Workers dashboard](https://dash.cloudflare.com/)
2. Click on your worker
3. View real-time metrics:
   - Request count
   - Error rate
   - CPU usage
   - Response time

## 🎁 **Bonus: Advanced Features**

### **Custom Domain**
You can use your own domain instead of `workers.dev`:
1. Add a custom domain in the worker settings
2. Update `CLOUDFLARE_PROXY_URL` to use your domain

### **Analytics**
Enable detailed analytics to track usage patterns and performance.

### **Caching**
Add caching headers to improve performance:
```javascript
headers: {
  ...response.headers,
  'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
  'Access-Control-Allow-Origin': '*',
}
```

---

**🎉 That's it!** Your Cloudflare Workers CORS proxy is now solving your Refinitiv image loading issues with enterprise-grade infrastructure for free! 