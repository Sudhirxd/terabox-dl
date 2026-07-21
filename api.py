import os
import re
import json
import sys
from typing import Optional, Dict, Union
from urllib.parse import urlparse, parse_qs
from curl_cffi import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

DEFAULT_NDUS = "YuLuQdPpeHuiMGEQDXpWDu6K2P4-xInj8YGEzswD"

def parse_netscape_cookies(content: str) -> Dict[str, str]:
    """
    Parse Netscape / Mozilla cookie file format text into a dictionary of cookie name -> value.
    """
    cookies = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5].strip()
            val = parts[6].strip()
            cookies[name] = val
    return cookies

def load_cookies(cookie_src: Optional[Union[str, dict]] = None) -> Dict[str, str]:
    """
    Flexible cookie loader supporting:
    - Path to Netscape cookies.txt file
    - Raw Netscape format string
    - JSON string / dict
    - Chrome extension JSON format
    - Cookie header string (key=value; ...)
    - Simple ndus string
    - Fallback to environment variables or local cookies.txt file
    """
    if isinstance(cookie_src, dict):
        return {str(k): str(v) for k, v in cookie_src.items()}

    raw_str = ""
    if isinstance(cookie_src, str) and cookie_src.strip():
        candidate = cookie_src.strip()
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                    raw_str = f.read()
            except Exception:
                raw_str = ""
        else:
            raw_str = candidate

    if not raw_str:
        env_cookie_file = os.environ.get("TERABOX_COOKIE_FILE") or os.environ.get("COOKIE_FILE")
        if env_cookie_file and os.path.isfile(env_cookie_file):
            try:
                with open(env_cookie_file, "r", encoding="utf-8", errors="ignore") as f:
                    raw_str = f.read()
            except Exception:
                pass

        if not raw_str:
            raw_str = os.environ.get("COOKIE_JSON") or os.environ.get("TERABOX_COOKIES") or ""

        if not raw_str:
            for default_file in ["cookies.txt", "terabox_cookies.txt", "cookies.json"]:
                if os.path.isfile(default_file):
                    try:
                        with open(default_file, "r", encoding="utf-8", errors="ignore") as f:
                            raw_str = f.read()
                        if raw_str:
                            break
                    except Exception:
                        pass

    if not raw_str:
        ndus_env = os.environ.get("NDUS") or DEFAULT_NDUS
        return {"ndus": ndus_env}

    if "\t" in raw_str:
        netscape_parsed = parse_netscape_cookies(raw_str)
        if netscape_parsed:
            return netscape_parsed

    try:
        data = json.loads(raw_str)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        elif isinstance(data, list):
            result = {}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    result[str(item["name"])] = str(item["value"])
            if result:
                return result
    except Exception:
        pass

    if "=" in raw_str:
        result = {}
        for pair in raw_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k.strip()] = v.strip()
        if result:
            return result

    return {"ndus": raw_str.strip()}

def extract_surl(url_or_surl: str) -> tuple[str, str]:
    """
    Extracts (surl_param, short_url) from a full TeraBox URL or raw surl key.
    """
    s = url_or_surl.strip()

    param_match = re.search(r'[?&]surl=([a-zA-Z0-9_-]+)', s)
    if param_match:
        key = param_match.group(1)
    else:
        path_match = re.search(r'/s/([a-zA-Z0-9_-]+)', s)
        if path_match:
            key = path_match.group(1)
        else:
            key = s

    if key.startswith("1"):
        short_url = key[1:]
        surl_param = key
    else:
        short_url = key
        surl_param = "1" + key

    return surl_param, short_url

def extract_jstoken(html_text: str) -> Optional[str]:
    """
    Extracts jsToken using multiple regex pattern fallbacks.
    """
    patterns = [
        r'fn%28%22(.*?)%22%29',
        r'fn\("([^"]+)"\)',
        r'jsToken\s*=\s*["\']([^"\']+)["\']',
        r'jsToken["\']?\s*:\s*["\']([^"\']+)["\']',
        r'window\.jsToken\s*=\s*["\']([^"\']+)["\']'
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text)
        if match and match.group(1):
            return match.group(1)
    return None

def tera(surl_or_url: str, cookies_input: Optional[Union[str, dict]] = None) -> str:
    """
    Generates download details for a TeraBox link or shorturl code.
    Returns a JSON string response.
    """
    try:
        surl_param, short_url = extract_surl(surl_or_url)
        cookies = load_cookies(cookies_input)

        session = requests.Session(impersonate="chrome110")
        session.cookies.update(cookies)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        first_url = f"https://dm.terabox.app/sharing/link?surl={surl_param}"
        response = session.get(first_url, headers=headers, timeout=15)

        if response.status_code != 200:
            return json.dumps({
                "errno": -1,
                "errmsg": f"HTTP error {response.status_code} fetching sharing page"
            })

        jsToken = extract_jstoken(response.text)
        if not jsToken:
            return json.dumps({
                "errno": -2,
                "errmsg": "Failed to extract jsToken from TeraBox page. Cookies or verification may be required."
            })

        api_url = "https://dm.terabox.app/share/list"
        params = {
            "app_id": "250528",
            "jsToken": jsToken,
            "site_referer": "https://www.terabox.app/",
            "shorturl": short_url,
            "root": "1"
        }

        api_headers = {
            "Host": "dm.terabox.app",
            "User-Agent": headers["User-Agent"],
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://dm.terabox.app/sharing/link?surl={short_url}&clearCache=1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://dm.terabox.app"
        }

        api_response = session.get(api_url, params=params, headers=api_headers, timeout=15)

        try:
            return json.dumps(api_response.json())
        except json.JSONDecodeError:
            return json.dumps({
                "errno": -3,
                "errmsg": "Invalid JSON response received from TeraBox API",
                "raw_response": api_response.text[:500]
            })

    except Exception as e:
        return json.dumps({
            "errno": -99,
            "errmsg": f"Unexpected error: {str(e)}"
        })

def format_bytes(bytes_num: Union[int, str, float], decimals: int = 2) -> str:
    try:
        b = float(bytes_num)
    except (ValueError, TypeError):
        return "0 Bytes"
    if b <= 0:
        return "0 Bytes"
    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while b >= k and i < len(sizes) - 1:
        b /= k
        i += 1
    return f"{b:.{decimals}f} {sizes[i]}"

DEVELOPER_DATA = {
    "name": "@SudhirXD",
    "telegram": "https://t.me/Sudhirxd",
    "github": "https://www.Github.com/Sudhirxd",
    "website": "https://www.sudhirxd.in"
}

def parse_dlink_params(dlink: str) -> tuple[str, str]:
    expires = "8h"
    region = "jp"
    if dlink:
        try:
            parsed = urlparse(dlink)
            qs = parse_qs(parsed.query)
            if "expires" in qs and qs["expires"]:
                expires = qs["expires"][0]
            if "region" in qs and qs["region"]:
                region = qs["region"][0]
        except Exception:
            pass
    return expires, region

def get_file_type(category: Union[int, str], duration: Optional[int] = None) -> str:
    cat = str(category or "").strip()
    if cat == "1" or duration is not None:
        return "video"
    elif cat == "2":
        return "audio"
    elif cat == "3":
        return "image"
    elif cat == "4":
        return "document"
    elif cat == "5":
        return "archive"
    return "file"

def build_custom_response(url: str, parsed_result: dict) -> tuple[dict, int]:
    if parsed_result.get("errno") != 0:
        return {
            "status": "error",
            "message": parsed_result.get("errmsg", "Failed to fetch TeraBox link details"),
            "developer": DEVELOPER_DATA,
            "meta": {
                "request_id": parsed_result.get("request_id"),
                "server_time": parsed_result.get("server_time")
            }
        }, 400

    raw_list = parsed_result.get("list", [])
    first_item = raw_list[0] if raw_list else {}

    raw_title = parsed_result.get("title") or first_item.get("server_filename") or ""
    clean_title = raw_title.lstrip("/") if isinstance(raw_title, str) else str(raw_title)
    if "/" in clean_title and not first_item.get("server_filename"):
        clean_title = clean_title.split("/")[-1]

    sz_bytes = 0
    try:
        if "size" in first_item and first_item["size"] is not None:
            sz_bytes = int(first_item["size"])
    except (ValueError, TypeError):
        sz_bytes = 0

    dlink = first_item.get("dlink") or ""
    expires, region = parse_dlink_params(dlink)

    thumbs_raw = first_item.get("thumbs") or {}

    file_duration = first_item.get("duration")
    if file_duration is not None:
        try:
            file_duration = int(file_duration)
        except (ValueError, TypeError):
            pass

    width = first_item.get("width")
    height = first_item.get("height")
    resolution = None
    if width is not None and height is not None:
        try:
            resolution = {"width": int(width), "height": int(height)}
        except (ValueError, TypeError):
            resolution = {"width": width, "height": height}

    is_adult = bool(first_item.get("is_adult") == 1 or first_item.get("is_adult") is True)

    response_data = {
        "status": "success",
        "message": "File fetched successfully",
        "developer": DEVELOPER_DATA,
        "share": {
            "url": url,
            "share_id": parsed_result.get("share_id"),
            "uk": parsed_result.get("uk"),
            "title": clean_title if clean_title else first_item.get("server_filename")
        },
        "file": {
            "name": first_item.get("server_filename"),
            "path": first_item.get("path"),
            "type": get_file_type(first_item.get("category"), file_duration),
            "size": {
                "text": format_bytes(sz_bytes),
                "bytes": sz_bytes
            },
            "duration": file_duration,
            "resolution": resolution,
            "md5": first_item.get("md5"),
            "fs_id": str(first_item.get("fs_id")) if first_item.get("fs_id") is not None else None
        },
        "download": {
            "direct_url": dlink,
            "expires": expires,
            "region": region
        },
        "thumbnails": {
            "icon": thumbs_raw.get("icon"),
            "small": thumbs_raw.get("url1"),
            "medium": thumbs_raw.get("url2"),
            "large": thumbs_raw.get("url3")
        },
        "meta": {
            "request_id": parsed_result.get("request_id"),
            "server_time": parsed_result.get("server_time"),
            "adult_content": is_adult
        }
    }

    return response_data, 200

# --- Flask Web Server ---
app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "name": "TeraBox Downloader API",
        "status": "operational",
        "developer": DEVELOPER_DATA,
        "endpoints": {
            "/api": "Fetch TeraBox file details and download links"
        },
        "usage": {
            "GET": "/api?url=https://terabox.app/s/1HSEb8PZRUE7Z1Tvd3ZtT0g",
            "POST": "/api with JSON body {'url': '...', 'cookies': '...'}"
        }
    })

@app.route('/api', methods=['GET', 'POST'])
def api_route():
    url = None
    cookies_input = None

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json(silent=True) or {}
            url = data.get('url')
            cookies_input = data.get('cookies') or data.get('cookie')
        else:
            url = request.form.get('url')
            cookies_input = request.form.get('cookies') or request.form.get('cookie')

    if not url:
        url = request.args.get('url')
    if not cookies_input:
        cookies_input = request.args.get('cookies') or request.args.get('cookie')

    if not url or not url.strip():
        return jsonify({
            "status": "error",
            "message": "Missing required parameter: url",
            "developer": DEVELOPER_DATA,
            "example": "/api?url=https://terabox.app/s/1HSEb8PZRUE7Z1Tvd3ZtT0g"
        }), 400

    try:
        raw_result = tera(url.strip(), cookies_input)
        parsed_result = json.loads(raw_result)
        res_data, status_code = build_custom_response(url.strip(), parsed_result)
        return jsonify(res_data), status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "developer": DEVELOPER_DATA,
            "url": url
        }), 500

# Vercel entrypoint
app = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


