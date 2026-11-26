# Mein Deutsch: put it online (GitHub Pages)

Keep this note. These are the exact steps.

## Files in this folder
- index.html (the whole app: lessons, words, streaks, XP)
- manifest.webmanifest (lets your phone install it like an app)
- sw.js (makes it work offline)
- icon-192.png, icon-512.png (app icon)

## One-time setup
1. On github.com, make a new PUBLIC repo named `mein-deutsch` (no README).
2. In Termux:

```
cd ~
mkdir -p mein-deutsch && cd mein-deutsch
cp /storage/emulated/0/Download/mein-deutsch/* .
git init
git branch -M main
git add .
git commit -m "Mein Deutsch v1"
git remote add origin https://github.com/michaelpeccia/mein-deutsch.git
git push -u origin main
```

3. On GitHub: repo > Settings > Pages > Source: Deploy from a branch > Branch: main, folder: / (root) > Save.
4. After a minute it is live at: https://michaelpeccia.github.io/mein-deutsch/

## Install on your Razr
Open the link in Chrome > three-dot menu > Add to Home screen (or Install app).

## Optional: your own address
To use german.kingdom-life-ministry.com instead:
1. Cloudflare DNS: add CNAME `german` -> `michaelpeccia.github.io`, grey cloud (DNS only).
2. GitHub repo > Settings > Pages > Custom domain: `german.kingdom-life-ministry.com` > Save, then tick Enforce HTTPS when it appears.

## Updating later
After changing index.html:
1. Open sw.js and bump the version, for example `mein-deutsch-v1` to `mein-deutsch-v2`.
2. In Termux:

```
cd ~/mein-deutsch
git add .
git commit -m "update"
git push
```

## If you hear no German voice
Phone Settings > search "Text-to-speech" > Preferred engine: Speech Services by Google > tap the gear > Install voice data > German. Then use Me > Test voice in the app.

## Your progress
Progress lives on the phone in that browser. Clearing Chrome's site data resets it.
