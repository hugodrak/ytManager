from bs4 import BeautifulSoup
import sqlite3

conn = sqlite3.connect("yt.sqlite")

def find_one(soup_target, tag_target, query):
    search = soup_target.find_all(tag_target, query)
    if len(search) == 1:
        return search[0]
    else:
        return None


def convert_to_seconds(time_raw):
    duration = 0
    for i, l_section in enumerate(time_raw.split(":")[::-1]):
        l_section = int(l_section)
        if i == 0:
            duration += l_section
        elif i == 1:
            duration += l_section * 60
        elif i == 2:
            duration += l_section * 3600
        elif i == 3:
            duration += l_section * 3600 * 24
    return duration


def update_wl():
    tag = "a:yt-simple-endpoint"

    soup = BeautifulSoup(open('wl2.htm', 'r'), 'html.parser')
    container = soup.find_all('div', {"id": "contents", "class": "ytd-playlist-video-list-renderer"})[0]
    videos = container.find_all('div', {"id": "content"})

    parsed_videos = []

    for video in videos:
        parsed_video = {'title': '', 'duration': 0, 'url': '', 'channel': None}
        vid_id = None

        # Duration
        duration_raw = find_one(video, 'span', {"class": "ytd-thumbnail-overlay-time-status-renderer"})
        if duration_raw:
            parsed_video['duration'] = convert_to_seconds(duration_raw.text.strip())
        else:
            continue

        # Title
        title_raw = find_one(video, 'span', {"id": "video-title"})
        if title_raw:
            parsed_video['title'] = title_raw.text.strip()
        else:
            continue

        # URL
        url_raw = find_one(video, 'a', {"id": "thumbnail"})
        if url_raw:
            url_href = url_raw.attrs['href'].strip()
            if (i1 := url_href.find("v=")) and (i2 := url_href.find("&")):
                url = url_href[i1+2: i2]
                c = conn.cursor()
                c.execute("SELECT id FROM watchLater WHERE url IS (?)", (url,))
                existing = c.fetchall()
                if existing:
                    vid_id = existing[0][0]
                parsed_video['url'] = url_href[i1+2: i2]
            else:
                continue

        # channel name
        channel_raw = find_one(find_one(video, 'yt-formatted-string', {"class": "ytd-channel-name"}), "a", {})
        if channel_raw:
            channel_href = channel_raw.attrs['href'].strip()
            channel_type, channel_name = channel_href.split("/")[-2:]
            c = conn.cursor()
            if channel_type == "channel":
                c.execute("SELECT id FROM channels WHERE url is (?)", (channel_name,))
            elif channel_type == "user":
                c.execute("SELECT id FROM channels WHERE title is (?)", (channel_name,))
            channels = c.fetchall()
            if len(channels) == 1:
                parsed_video['channel'] = channels[0][0]
        else:
            continue

        c = conn.cursor()
        if vid_id:
            c.execute("UPDATE watchLater SET channel=?, title=?, url=?, duration=? WHERE id IS ?", (parsed_video['channel'], parsed_video['title'], parsed_video['url'], parsed_video['duration'], vid_id))
        else:
            c.execute("INSERT INTO watchLater (channel, title, url, duration) VALUES (?, ?, ?, ?)", (parsed_video['channel'], parsed_video['title'], parsed_video['url'], parsed_video['duration']))
        conn.commit()


def get_videos():
    c = conn.cursor()
    c.execute("SELECT title, duration, url FROM watchLater ORDER BY duration DESC")
    videos = c.fetchall()
    for video in videos:
        print(f"{video[1]}s --> https://www.youtube.com/watch?v={video[2]} | {video[0]}")

get_videos()