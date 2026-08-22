/* Cloudflare Pages function: hand /api/* straight to the Render API.
 *
 * The browser must believe the API lives on this same origin, otherwise the
 * session cookie is a third-party cookie and gets dropped — which is exactly
 * what Netlify's _redirects proxy was doing for us before.
 */
const API = "https://theplug-32x5.onrender.com";

export async function onRequest({ request }) {
  const url = new URL(request.url);
  const target = API + url.pathname + url.search;

  // carry the method, headers and body across untouched; the cookie rides in
  // the headers and Set-Cookie rides back out the same way
  const forwarded = new Request(target, request);
  forwarded.headers.set("Host", new URL(API).host);

  const res = await fetch(forwarded);
  // the response is immutable as returned; copy it so nothing downstream trips
  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: res.headers,
  });
}
