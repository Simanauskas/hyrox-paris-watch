"""Watch HYROX Paris Grand Palais 2027 and push a phone alert when tickets go live.

Signals (any one = alert):
  1. hyrox.com/find-my-race: Paris row button flips "Find out more" -> "Buy Tickets"
  2. Event page (hyrox.com + hyroxfrance.com): "Join the waitlist" text disappears
  3. Event page: a vivenu ticket-shop widget/link appears
"""
import json, os, re, sys, urllib.request

SLUG = "hyrox-paris-grand-palais-s26-27"
EVENT_URLS = [f"https://hyrox.com/event/{SLUG}/", f"https://hyroxfrance.com/event/{SLUG}/"]
LIST_URL = "https://hyrox.com/find-my-race/"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]           # set as a GitHub secret
STATE = "state.json"
UA = {"User-Agent": "Mozilla/5.0 (personal ticket watcher, 1 req/10min)"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def check():
    hits = []
    try:
        s = get(LIST_URL)
        i = s.find(f"/event/{SLUG}/\"><span class=\"w-btn-label\">")
        if i != -1:
            label = re.search(r'w-btn-label">([^<]+)<', s[i:i + 200]).group(1)
            if label.strip().lower() != "find out more":
                hits.append(f"Find-my-race button now says '{label.strip()}'")
    except Exception as e:
        print("list err", e)
    for url in EVENT_URLS:
        try:
            s = get(url)
            if len(s) < 50_000:
                continue  # error/blocked page, don't trust it
            if "waitlist" not in s.lower():
                hits.append(f"Waitlist text gone: {url}")
            if re.search(r'vi-shop|data-vi-|vivenu\.com/(event|checkout|seller)', s):
                hits.append(f"Ticket shop widget found: {url}")
        except Exception as e:
            print("event err", url, e)
    return hits

def notify(msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": "HYROX Paris Grand Palais tickets LIVE",
                 "Priority": "urgent", "Tags": "rotating_light",
                 "Click": EVENT_URLS[0]})
    urllib.request.urlopen(req, timeout=30)

if __name__ == "__main__":
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"alerts": 0}
    hits = check()
    print(hits or "not live yet")
    if hits and state["alerts"] < 5:           # nag up to 5 times, then stop
        notify("\n".join(hits) + "\nOpen now → Men Open, solo.")
        state["alerts"] += 1
        json.dump(state, open(STATE, "w"))
    if "--test" in sys.argv:
        notify("Test alert — watcher is wired up.")
