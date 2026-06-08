# Running a safe, realistic lab exercise

The tool itself runs fully offline (tracking server on localhost, no outbound
email). To make a demo feel realistic without touching any real accounts:

## Minimal setup (single machine)

1. Start the tracking server:
   ```bash
   python -m phishing_sim.cli --db campaign.sqlite3 serve --i-accept-lab-only-terms
   ```
2. Create a campaign with your own test email addresses:
   ```bash
   python -m phishing_sim.cli --db campaign.sqlite3 new-campaign "Lab Exercise" \
       --recipients "Test User:you@example.com" \
       --i-accept-lab-only-terms
   ```
3. Copy the printed tracking link and open it in a browser tab — this simulates
   a recipient clicking. Submit the fake form to simulate a credential capture.
4. Generate the report:
   ```bash
   python -m phishing_sim.cli --db campaign.sqlite3 report 1 --html report.html
   ```

## LAN lab setup (more realistic)

For a multi-person or multi-VM exercise on an isolated network:

1. Boot an isolated VM network (host-only or internal adapter — no internet access).
2. Run the tracking server on one VM with `--host 0.0.0.0` so lab machines can reach it.
3. Use a local mail server (e.g. [MailHog](https://github.com/mailhog/MailHog)) to
   deliver the tracking links as actual emails to lab accounts, then have participants
   open their inboxes and interact normally.
4. Debrief using the HTML report and the awareness tips from the post-submission page.

## What makes a good exercise

- **Tell participants afterward**, not before — the awareness page does this
  automatically when they submit, but a follow-up group debrief reinforces the lesson.
- **Re-run after training** — compare click/submit rates before and after an
  awareness session to measure actual improvement.
- **Vary the pretext** — "IT Portal" is the built-in template; you can add more
  templates (HR portal, password-reset notice, package delivery) by adding a new
  HTML file to `phishing_sim/templates/` and registering the name in
  `phishing_sim/server.py`'s `TEMPLATES` set.

Keep all `.sqlite3` database files out of the repo (already in `.gitignore`) —
they contain participant names, emails, and event timestamps.
