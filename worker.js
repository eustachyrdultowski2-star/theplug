/* The site is static; this exists for one job.
 *
 * The browser has to believe the API lives on this same origin, otherwise the
 * session cookie counts as third-party and gets thrown away before it reaches
 * anyone. So /api/* is passed through to Render from here, and everything else
 * is handed back to the static files.
 */
const API = "https://theplug-32x5.onrender.com";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
      const upstream = await fetch(new Request(API + url.pathname + url.search, request));
      // the returned response is immutable, so copy it before handing it on
      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: upstream.headers,
      });
    }

    return env.ASSETS.fetch(request);
  },
};
