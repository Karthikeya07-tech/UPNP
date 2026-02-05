# UPnP Music Player (Termux)

Discover UPnP/DLNA MediaRenderer devices on your WiFi and play music (URL or local file) on them from the Termux terminal. While playing, a progress bar shows elapsed/total time and you can **press Enter to stop** playback.

## Requirements

- **Termux** on Android
- Phone and the speaker/TV on the **same WiFi**
- Python 3.10+

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/upnp-music.git
cd upnp-music

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

---

## Script behavior in the Termux terminal

When you run `python main.py`, the script runs in one flow and stays in the terminal until you stop playback or it ends. Here is what happens step by step:

1. **Start** – It prints a short message and asks that your phone is on the same WiFi as the speaker/TV.

2. **Discovery** – It sends an SSDP search on the network and waits a few seconds. It prints:  
   `Discovering UPnP devices (MediaRenderers)...`

3. **Device list** – It lists only devices that can play media (MediaRenderers), e.g.:
   ```
   Found 2 device(s):
     1. Living Room Speaker
     2. Kitchen TV
   ```
   You type a number and press Enter to choose one.

4. **Music source** – It asks for either:
   - A **URL** (e.g. `https://example.com/song.mp3`), or  
   - A **local file path** (e.g. `/sdcard/Music/song.mp3`).  
   If you give a file path, the script starts a small HTTP server on your phone and tells the renderer to stream from that URL.

5. **Playback starts** – It sends the media URL to the chosen device and starts playback. It then prints:  
   `Playing. Press Enter to stop.`

6. **Progress bar** – While the device is playing, the script **polls the device** every ~1.5 seconds and updates a **single line** in the terminal with:
   - A bar like `[=========>          ]`
   - Elapsed time / total time (e.g. `1:23 / 3:45`)
   - Percentage (e.g. `(35%)`)
   - Reminder: `(Enter = stop)`  
   So you see how much of the track is done and how much is still pending.

7. **Stopping** – When you want to stop the music:
   - **Press Enter** (nothing else to type).  
   The script sends **Stop** to the device, the progress line is replaced with `Stopped.`, the file server (if any) is shut down, and the script exits. You get your shell prompt back.

8. **If the track ends by itself** – When the device reports that playback has ended, the script prints `Playback ended on device.` and exits.

So: **one run = one flow**: discover → choose device → give URL/file → play → see progress → press Enter to stop (or wait until it ends).

---

## Flow (summary)

| Step | What happens |
|------|-------------------------------|
| 1 | **Discovery** – SSDP search; list MediaRenderer devices. |
| 2 | **Select device** – You pick one by number. |
| 3 | **Music source** – You enter a URL or a local file path (local file → script serves it over HTTP). |
| 4 | **Play** – Script sends SetAVTransportURI + Play to the device. |
| 5 | **Progress** – Script polls GetPositionInfo and shows a status line: elapsed / total and a bar. |
| 6 | **Stop** – You **press Enter** → script sends Stop → script exits. (Or script exits when playback ends.) |

---

## How to stop the music

- **While the script is running and music is playing:** press **Enter** in the Termux terminal.  
- The script will send a **Stop** command to the device and then exit. No need to type anything else.

---

## Usage examples

- **Play from URL:** when asked for music, paste e.g.  
  `https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3`
- **Play local file:** enter path like `/sdcard/Download/music.mp3` (Termux can access storage if you grant it).
- **Stop:** when you see the progress bar, press **Enter** to stop and exit.

---

## Notes

- Some renderers only accept certain formats (e.g. MP3). If playback fails, try another URL or file.
- For local files, the renderer must be able to reach your phone’s IP on the WiFi; the script uses your local IP and a temporary HTTP server.
- The progress bar uses the device’s reported position; if the device doesn’t report duration, you may see `--` for total time.
