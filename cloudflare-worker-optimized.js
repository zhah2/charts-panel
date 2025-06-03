export default {
  async fetch(request, env, ctx) {
    // Handle preflight OPTIONS requests quickly
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
    
    const startTime = Date.now();
    
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
      
      // Validate URL to prevent abuse (faster validation)
      if (!targetUrl.includes('refini.tv') && !targetUrl.includes('refinitiv.com')) {
        return new Response('Only Refinitiv URLs are allowed', { 
          status: 403,
          headers: { 'Access-Control-Allow-Origin': '*' }
        });
      }
      
      console.log(`[${Date.now() - startTime}ms] Proxying request to: ${targetUrl}`);
      
      // Create cache key
      const cacheKey = new Request(targetUrl, {
        method: 'GET',
        headers: {
          'User-Agent': 'Cloudflare-Worker-CORS-Proxy/2.0',
          'Accept': 'image/*,*/*;q=0.8',
        }
      });
      
      // Try to get from cache first
      const cache = caches.default;
      let response = await cache.match(cacheKey);
      
      if (response) {
        console.log(`[${Date.now() - startTime}ms] Cache HIT for ${targetUrl}`);
        
        // Clone response and add CORS headers
        const corsResponse = new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: {
            ...response.headers,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
            'Access-Control-Expose-Headers': 'Content-Length, Content-Type',
            'X-Cache': 'HIT',
            'X-Response-Time': `${Date.now() - startTime}ms`,
          }
        });
        
        return corsResponse;
      }
      
      console.log(`[${Date.now() - startTime}ms] Cache MISS, fetching from origin`);
      
      // Fetch the target URL with optimized settings
      response = await fetch(targetUrl, {
        method: 'GET',
        headers: {
          'User-Agent': 'Cloudflare-Worker-CORS-Proxy/2.0',
          'Accept': 'image/*,*/*;q=0.8',
          'Accept-Encoding': 'gzip, deflate, br',
        },
        // Use Cloudflare's fetch optimizations
        cf: {
          // Always cache at the edge
          cacheEverything: true,
          // Cache for 1 hour
          cacheTtl: 3600,
          // Use Cloudflare's image optimization if available
          image: {
            fit: "scale-down",
            quality: 85,
            format: "auto"
          }
        }
      });
      
      const fetchTime = Date.now() - startTime;
      console.log(`[${fetchTime}ms] Fetch completed with status: ${response.status}`);
      
      if (!response.ok) {
        return new Response(`Target server error: ${response.status}`, {
          status: response.status,
          headers: { 
            'Access-Control-Allow-Origin': '*',
            'X-Response-Time': `${fetchTime}ms`,
          }
        });
      }
      
      // Create optimized response with CORS headers
      const corsResponse = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: {
          // Preserve important original headers
          'Content-Type': response.headers.get('Content-Type') || 'image/png',
          'Content-Length': response.headers.get('Content-Length') || '',
          'Last-Modified': response.headers.get('Last-Modified') || '',
          'ETag': response.headers.get('ETag') || '',
          
          // Add CORS headers
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
          'Access-Control-Expose-Headers': 'Content-Length, Content-Type',
          
          // Add performance headers
          'X-Cache': 'MISS',
          'X-Response-Time': `${Date.now() - startTime}ms`,
          'X-Fetch-Time': `${fetchTime}ms`,
          
          // Add caching headers for browser
          'Cache-Control': 'public, max-age=3600, s-maxage=7200',
          'Vary': 'Accept-Encoding',
        }
      });
      
      // Store in cache for next time (don't await, let it happen in background)
      ctx.waitUntil(cache.put(cacheKey, corsResponse.clone()));
      
      console.log(`[${Date.now() - startTime}ms] Response sent with CORS headers`);
      return corsResponse;
      
    } catch (error) {
      const errorTime = Date.now() - startTime;
      console.error(`[${errorTime}ms] Proxy error:`, error);
      
      return new Response(`Proxy error: ${error.message}`, {
        status: 500,
        headers: { 
          'Access-Control-Allow-Origin': '*',
          'X-Response-Time': `${errorTime}ms`,
          'X-Error': error.message,
        }
      });
    }
  }
}; 