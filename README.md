# ☁️ TeraBox Downloader Python API

A fast, lightweight, and Vercel-ready **TeraBox direct download link generator API** built in Python with Flask and `curl_cffi` to bypass anti-bot and Cloudflare protections seamlessly.

---

## ✨ Features

- ⚡ **Single-File Architecture**: Everything is self-contained inside [api.py](file:///c:/Users/HP/Desktop/TeraBox-Dl-main/api.py).
- ☁️ **Vercel Serverless Ready**: Configured for instant deployment to Vercel via `vercel.json`.
- 🔗 **Direct Link Extraction**: Extract direct download links, filenames, file sizes, thumbnails, and metadata from TeraBox links.
- 🍪 **Netscape Cookie Support**: Automatically loads cookies from standard Netscape format files (`cookies.txt`), JSON, or environment variables.
- 🌐 **CORS Supported**: Configured with `flask-cors` headers for cross-origin frontend requests.
- 👨‍💻 **Developer Metadata**: Includes developer, website, and GitHub links in every response.

---

## 👨‍💻 Credits & Developer Info

- **Developer**: [SudhirXD](https://t.me/Sudhirxd)
- **Telegram**: [t.me/Sudhirxd](https://t.me/Sudhirxd)
- **Website**: [www.sudhirxd.in](https://www.sudhirxd.in)
- **GitHub**: [www.github.com/Sudhirxd](https://www.github.in/Sudhirxd)

---

## 🛠️ Requirements & Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🚀 Running Locally

Start the API server:
```bash
python api.py
```
*The server starts at `http://localhost:5000`.*

---

## 🔌 API Documentation

### Fetch File Details Endpoint
- **URL:** `/api`
- **Method:** `GET` or `POST`

#### Example Request
```bash
curl -X GET "http://localhost:5000/api?url=https://terabox.app/s/1HSEb8PZRUE7Z1Tvd3ZtT0g"
```

#### JSON Response Schema
```json
{
  "status": "success",
  "message": "File fetched successfully",
  "developer": {
    "name": "SudhirXD",
    "telegram": "https://t.me/Sudhirxd",
    "github": "https://www.github.com/Sudhirxd",
    "website": "https://www.sudhirxd.in"
  },
  "share": {
    "url": "https://terabox.app/s/1HSEb8PZRUE7Z1Tvd3ZtT0g",
    "share_id": 54404273244,
    "uk": 4400609552707,
    "title": "Beautiful_Paki_CabinCrew.mp4"
  },
  "file": {
    "name": "Beautiful_Paki_CabinCrew.mp4",
    "path": "/2025-06-21 21-56/Beautiful_Paki_CabinCrew.mp4",
    "type": "video",
    "size": {
      "text": "7.70 MB",
      "bytes": 8071052
    },
    "duration": 174,
    "resolution": {
      "width": 352,
      "height": 640
    },
    "md5": "1166e5d88f5a4a0ef8bd01ba5c463a32",
    "fs_id": "375033477530196"
  },
  "download": {
    "direct_url": "https://dm-d.terabox.app/file/1166e5d88f5a4a0ef8bd01ba5c463a32?...",
    "expires": "8h",
    "region": "jp"
  },
  "thumbnails": {
    "icon": "https://data.terabox.app/thumbnail/...size=c60_u60",
    "small": "https://data.terabox.app/thumbnail/...size=c140_u90",
    "medium": "https://data.terabox.app/thumbnail/...size=c360_u270",
    "large": "https://data.terabox.app/thumbnail/...size=c850_u580"
  },
  "meta": {
    "request_id": 63612857912146974,
    "server_time": 1784613645,
    "adult_content": true
  }
}
```

---

## ☁️ Deploying to Vercel

1. Push this repository to GitHub / GitLab.
2. Import the repository in [Vercel](https://vercel.com).
3. Vercel automatically deploys `api.py` via `vercel.json`.

---

## 📜 License

MIT License
