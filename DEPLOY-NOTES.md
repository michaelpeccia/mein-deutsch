# Mein Deutsch: deploy and reminder notes

Keep this note. These are the exact steps.

## Files
- index.html (the whole app)
- manifest.webmanifest, sw.js, icon-192.png, icon-512.png (install, offline, notifications)
- server/push_server.py (daily reminder server, runs on kingdom-ai)
- server/setup.sh (one-command installer for that server)

Live app: https://michaelpeccia.github.io/mein-deutsch/

---

## A. Update the app from your phone (Termux)
Download the new mein-deutsch.zip first. Then:

```
cd ~/mein-deutsch
unzip -o /storage/emulated/0/Download/mein-deutsch.zip
cp -r mein-deutsch/* . && rm -rf mein-deutsch
ls
git add .
git commit -m "update"
git push
```

`ls` should show index.html, sw.js and a server folder.
If the zip name differs (like "mein-deutsch (1).zip"):
`ls /storage/emulated/0/Download | grep -i deutsch`

When you change index.html yourself later, bump the VERSION line in sw.js (v2 to v3, and so on) so the phone picks up the update.

---

## B. Install the reminder server on kingdom-ai (one time)
Wait a minute after step A so GitHub Pages has the new files. Then from Termux:

```
ssh michael777@kingdom-ai
curl -fsSL https://michaelpeccia.github.io/mein-deutsch/server/setup.sh | bash
```

It asks for your server password once. At the end you should see:
`{"ok": true, "subscribers": 0}` and "Reminder server is running on port 8097."

Handy commands on kingdom-ai:
```
sudo systemctl status mein-deutsch-push      # is it running?
journalctl -u mein-deutsch-push -n 30        # recent log lines
sudo systemctl restart mein-deutsch-push     # restart it
curl -s http://localhost:8097/health         # quick check
```

To update the server later (after pushing a new push_server.py to GitHub), just run the same curl setup line again.

---

## C. Add the web address in Cloudflare (one time)
Cloudflare dashboard > Zero Trust > Networks > Tunnels > kingdom-ai-ask > Public hostnames (Routes) > Add:
- Subdomain: `push`
- Domain: `kingdom-life-ministry.com`
- Service: HTTP, `localhost:8097`

Save. Check it from your phone's browser:
https://push.kingdom-life-ministry.com/health

---

## D. Turn on reminders in the app
1. Open the installed Mein Deutsch app (close and reopen it once so it loads the new version).
2. Me > Daily reminder > pick a time > Turn on > Allow notifications.
3. Tap Send test. A notification should pop up.

How it works:
- One reminder a day at your time.
- If you still haven't done a lesson by 9:00 PM, one more "save your streak" nudge.
- Both are skipped on days you've already done a lesson.
- Doing a lesson tells the server automatically.

## Your streak
Me > Carry over your streak lets you type your Duolingo streak and whether you last practiced today or yesterday. The next lesson adds a day to it.

## If you hear no German voice
Phone Settings > search "Text-to-speech" > Speech Services by Google > gear > Install voice data > German.

## Progress
Progress lives on the phone in the app. Clearing the app's site data resets it.
