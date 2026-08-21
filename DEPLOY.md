# Putting The Plug online

The app is now an installable PWA. Two things have to go live:
the **site** (static files) and the **API** (`server.py`, which talks to Apify).

---

## 1. Domain

Buy one first, everything else points at it. `theplug.app` is the name used in
the outreach emails. Roughly 60-80 zł/year at OVH, Namecheap or Cloudflare.

Cloudflare is the least annoying: registrar at cost price, DNS and hosting in
one place.

---

## 2. The site (free)

The static half is `index.html`, `assets/`, `manifest.webmanifest`, `sw.js`.

**Cloudflare Pages** (recommended)
1. Put the project in a GitHub repo.
2. Cloudflare dashboard → Workers & Pages → Create → connect the repo.
3. Build command: leave empty. Output directory: `/`.
4. Add your domain in the Pages project.

Netlify and Vercel work the same way. All three are free at this size and give
you HTTPS automatically, which a PWA requires.

**One thing to configure:** routes like `/brand/scuffers` must fall back to
`index.html`. On Cloudflare Pages add a `_redirects` file:

    /api/*  https://YOUR-API-HOST/api/:splat  200
    /*      /index.html                       200

---

## 3. The API (needs a real server)

`server.py` runs the brand detection and image search, so it cannot live on a
static host. Free options that run Python:

| Host | Free tier | Notes |
|---|---|---|
| Render | yes, sleeps when idle | simplest, deploy from GitHub |
| Railway | trial credit | fastest to set up |
| Fly.io | small free allowance | keeps running, more setup |

On Render: New → Web Service → connect repo → Start command `python server.py`.
Set the environment variables from your `.env` (**APIFY_TOKEN**, `APIFY_ACTOR`).
Never commit `.env` itself.

Then point the site at it, either through the `_redirects` rule above or by
replacing the relative `/api/...` calls in index.html with the API host.

---

## 4. Before you send more outreach

- [ ] domain resolves over HTTPS
- [ ] `/brand/adsum` opens directly (not just from the homepage)
- [ ] "Spot from link" returns a real answer on the live site
- [ ] regenerate the emails with the real link: `py make_emails.py 30`

---

## 5. Getting on the stores

**Read this before paying Apple anything.**

Apple rejects apps that are just a website in a wrapper (App Store Review
Guideline 4.2, "Minimum Functionality"). A WebView around theplug.app will be
refused. You also need a Mac with Xcode, or a paid cloud build service, plus
99 USD a year.

The way through is to give the app something a browser cannot do. For this
product the obvious one is a **share extension**: the user taps Share inside
TikTok, picks The Plug, and the fit gets identified. That is a genuine native
feature and it is also the best thing about the product.

Sensible order:

1. **PWA now (done).** Installs from the browser on Android and iOS, free, no
   review. Use it to get the first users.
2. **Google Play next.** 25 USD once. A PWA can be published as-is through a
   Trusted Web Activity (Bubblewrap). Low effort, real store listing.
3. **App Store last**, once there are users and the share extension is built.
   Wrap the PWA with Capacitor, add the share extension and push notifications
   (the restock alerts are already built server-side and give push a real job).

Android install works today: open the site in Chrome → menu → Install app.
On iPhone: Safari → Share → Add to Home Screen.
