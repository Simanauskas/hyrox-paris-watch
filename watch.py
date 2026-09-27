"""Watch HYROX Paris Grand Palais 2027 and push a phone alert when tickets go live."""
import datetime, json, os, re, sys, urllib.request

SLUG = "hyrox-paris-grand-palais-s26-27"
EVENT_URLS = [f"https://hyrox.com/event/{SLUG}/", f"https://hyroxfrance.com/event/{SLUG}/"]
LIST_URL = "https://hyrox.com/find-my-race/"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
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

def notify(title, msg):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": title, "Priority": "urgent",
                 "Tags": "rotating_light", "Click": EVENT_URLS[0]})
    urllib.request.urlopen(req, timeout=30)

if __name__ == "__main__":
    state = {"alerts": 0, "last_day": ""}
    if os.path.exists(STATE):
        state.update(json.load(open(STATE)))
    old = dict(state)

    hits = check()
    print(hits or "not live yet")
    if hits and state["alerts"] < 5:  # nag up to 5 times, then stop
        notify("HYROX Paris Grand Palais tickets LIVE",
               "\n".join(hits) + "\nOpen now -> Men Open, solo.")
        state["alerts"] += 1

    # Keepalive: one commit per day so GitHub doesn't disable the schedule after 60 days
    state["last_day"] = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    if state != old:
        json.dump(state, open(STATE, "w"))
    if "--test" in sys.argv:
        notify("HYROX watcher test", "Test alert - watcher is wired up.")
