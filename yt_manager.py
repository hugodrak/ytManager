import requests
from bs4 import BeautifulSoup
import sqlite3
import time

conn = sqlite3.connect("yt.sqlite")

BASE_URL = "https://www.youtube.com/"


def get_subscribers(html):
    c = conn.cursor()
    with open(html, "r", encoding='utf-8') as f:
        c.execute("SELECT url FROM channels")
        urls = c.fetchall()
        soup = BeautifulSoup(f.read(), 'html.parser')
        subscriptions_container = soup.find_all('div', {"id": "items"})[1]
        subscriptions = subscriptions_container.find_all('a', {"id": "endpoint"})
        for item in subscriptions:
            attributes = item.attrs
            if "title" in attributes and "href" in attributes:
                href = attributes["href"].split("/")[-1]
                if href[0:2] == "UC" and (href,) not in urls:
                    c.execute("INSERT INTO channels (url, title, updated) VALUES (?, ?, ?)",
                              (href, attributes["title"], int(time.time())))

        conn.commit()


def get_videos():
    c = conn.cursor()
    c.execute("SELECT id, url, title, subscribers FROM channels")
    channels = c.fetchall()

    for channel_id, url, title, subscribers in channels:
        r = requests.get(f"{BASE_URL}channel/{url}/videos")
        soup = BeautifulSoup(r.text, 'html.parser')

        get_subscribe_count(soup, channel_id, subscribers)

        correct = False
        count = 0
        while not correct:
            correct = len(soup.find_all('ul', {"id": "channels-browse-content-grid"})) > 0 or len(soup.find_all("link", {"itemprop": "url"})) > 0
            if correct:
                break
            if count > 4:
                print("Tried five times, skipping.")
                break
            count += 1
            print("Woah too fast, sleeping 0.5")
            time.sleep(0.5)
            r = requests.get(f"{BASE_URL}channel/{url}/videos")
            soup = BeautifulSoup(r.text, 'html.parser')

        if len(soup.find_all('ul', {"id": "channels-browse-content-grid"})) == 0:
            print("User search")
            new_url = ""
            for page_link in soup.find_all("link", {"itemprop": "url"}):
                if page_link["href"].split("/")[3] == "user":
                    new_url = page_link["href"]
            if new_url == "":
                print(f"Channel with id: {title} has no videos.")
                continue

            r = requests.get(f"{new_url}/videos")
            soup = BeautifulSoup(r.text, 'html.parser')

            if len(soup.find_all('ul', {"id": "channels-browse-content-grid"})) == 0:
                print(f"Channel with id: {title} has a different video layout, TODO.")
                continue

        videos = soup.find_all('ul', {"id": "channels-browse-content-grid"})[0]
        c.execute("SELECT url FROM videos where channel is ?", (channel_id,))
        existing_urls = c.fetchall()

        print(f"Looking through: {title}, found {int((len(videos)-1)/2-len(existing_urls))} new videos")

        for video in videos:
            if video != "\n":
                thumb = video.find_all('img')[0]["src"]
                url = video.find_all('a')[1]["href"].split("=")[1]

                if (url,) not in existing_urls:
                    title = video.find_all('a')[1].contents[0]
                    if len(video.find_all('span', {"class": "video-time"})) == 0:
                        continue

                    length_raw = video.find_all('span', {"class": "video-time"})[0].contents[0].contents[0]
                    duration = 0
                    for i, l_section in enumerate(length_raw.split(":")[::-1]):
                        l_section = int(l_section)
                        if i == 0:
                            duration += l_section
                        elif i == 1:
                            duration += l_section * 60
                        elif i == 2:
                            duration += l_section * 3600
                        elif i == 3:
                            duration += l_section * 3600 * 24

                    if len(video.find_all('ul', {"class": "yt-lockup-meta-info"})) > 1:
                        views_raw = video.find_all('ul', {"class": "yt-lockup-meta-info"})[0].contents[0].contents[0]
                        views = ""
                        for v_sect in views_raw.split(" "):
                            v_sect = v_sect.replace(u"\xa0", u"")
                            if v_sect.isdigit():
                                views += v_sect
                        if views == "":
                            views = 0
                        else:
                            views = int(views)
                    else:
                        views = 0

                    score = int((views/subscribers)*100)

                    c.execute("INSERT INTO videos (channel, title, views, thumbnail, url, created, duration, score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (channel_id, title, views, thumb, url, int(time.time()), duration, score))

        conn.commit()
    print("done")


def get_subscribe_counts():
    c = conn.cursor()
    c.execute("SELECT id, url FROM channels")
    channels = c.fetchall()

    for channel_id, url in channels:
        r = requests.get(f"{BASE_URL}channel/{url}")
        soup = BeautifulSoup(r.text, 'html.parser')
        if len(soup.find_all("span", {"class": "yt-subscription-button-subscriber-count-branded-horizontal"})) > 0:
            subscribers_raw = soup.find_all("span", {"class": "yt-subscription-button-subscriber-count-branded-horizontal"})[0]["title"]

            if subscribers_raw[-2:] == "mn":
                subscribers = int(float(subscribers_raw[:-2].replace(",", "."))*10**6)
            else:
                subscribers = int(subscribers_raw.replace(u'\xa0', u''))

        c.execute("UPDATE channels SET subscribers=? WHERE id=?", (subscribers, channel_id))
        conn.commit()


def set_scores():
    c = conn.cursor()
    ids = c.execute("SELECT id FROM channels").fetchall()
    subs = c.execute("SELECT subscribers FROM channels").fetchall()
    ids = [x[0] for x in ids]
    subs = [x[0] for x in subs]

    for video_id, channel_id, views in c.execute("SELECT id, channel, views FROM videos").fetchall():
        try:
            index = ids.index(channel_id)
            score = int((views/subs[index])*100)
            c.execute("UPDATE videos SET score=? WHERE id=?", (score, video_id))
        except:
            print(video_id, channel_id)
            continue
    conn.commit()


def get_subscribe_count(soup, channel_id, subscribers):
    c = conn.cursor()
    if len(soup.find_all("span", {"class": "yt-subscription-button-subscriber-count-branded-horizontal"})) > 0:
        subscribers_raw = soup.find_all("span", {"class": "yt-subscription-button-subscriber-count-branded-horizontal"})[0]["title"]

        if subscribers_raw[-2:] == "mn":
            subscribers = int(float(subscribers_raw[:-2].replace(",", "."))*10**6)
        else:
            subscribers = int(subscribers_raw.replace(u'\xa0', u''))

    c.execute("UPDATE channels SET subscribers=? WHERE id=?", (subscribers, channel_id))
    conn.commit()


get_videos()

# get_subscribers("./YouTube.html")
# get_subscribe_counts()
# set_scores()

