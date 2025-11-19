import requests
import os
import re
import logging
from flask import Response


def extract_video_credentials(post_infos):
    """
    Args:
        post_infos (dict): The dict of the post to load.

    Returns:
        dict: A dictionary containing 'creds' and 'post_data', or None if URL not found.
    """


    url = post_infos.get("data", {}).get("post", {}).get("url")
    if not url:
        logging.error("URL key not found in post data.")
        return None

    logging.info(f"Found URL: {url[:150]}...")

    pattern = r"CloudFront-Key-Pair-Id=([^&]+)&CloudFront-Signature=([^&]+)&CloudFront-Policy=([^&]+)"
    match = re.search(pattern, url)

    if match:
        creds = {
            "publicKey": match.group(1),
            "signature": match.group(2),
            "policy": match.group(3)
        }
        logging.info("✅ Successfully extracted video stream credentials.")
        # Return both the credentials and the full post data
        return {"creds": creds, "post_data": post_infos}
    else:
        logging.error("❌ Regex did not find video credentials in the URL.")
        return None


def proxy_stream_request(post_id, video_path, stream_credentials, content_host, user_agent_string, device_info):
    """
    Proxies a request for an HLS segment (.ts) or playlist (.m3u8).
    Rewrites URLs in playlists to point back to this proxy.

    If you read this, a small change can make you stream in 1080p lol

    Args:
        post_id (int): The post_id, used for rewriting the proxy URL.
        video_path (str): The path to the video resource (e.g., 'hls/1080p/video.m3u8').
        stream_credentials (dict): A dict with 'CloudFront-Key-Pair-Id', 'CloudFront-Signature', 'CloudFront-Policy'.
        content_host (str): The hostname of the content server.
        user_agent_string: The user agent to use
        device_info(dict): Dictionary of the device info
    Returns:
        flask.Response: A Flask Response object, either streaming content or a rewritten playlist.
    """
    real_url = f"https://{content_host}/{video_path}"

    cookie_header_string = (
        f"CloudFront-Key-Pair-Id={stream_credentials['CloudFront-Key-Pair-Id']}; "
        f"CloudFront-Signature={stream_credentials['CloudFront-Signature']}; "
        f"CloudFront-Policy={stream_credentials['CloudFront-Policy']}"
    )

    if '.m3u8' in video_path:
        logging.info(f"Requesting playlist. Using Cookie: {cookie_header_string[:80]}...")

    headers = {
        "Accept": "*/*", "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7", "Connection": "keep-alive",
        "Cookie": cookie_header_string, "Host": content_host, "Origin": "https://channel.frommyarti.com",
        "Referer": "https://channel.frommyarti.com/",
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Android WebView";v="140"' if device_info["os"] == "Android" else '"Safari";v="17", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": f'"{device_info["os"]}"', "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site",
        "User-Agent":user_agent_string,
        "X-Requested-With": "com.knowmerce.fromm.fan"
    }

    try:
        response = requests.get(real_url, headers=headers, stream=True)
        response.raise_for_status()

        if '.m3u8' in video_path:
            logging.info("Playlist found. Rewriting URLs...")
            original_content = response.text

            base_path = os.path.dirname(video_path.lstrip('/'))
            if base_path:
                proxy_prefix = f"/stream/p{post_id}/{base_path}/"
            else:
                proxy_prefix = f"/stream/p{post_id}/"

            proxy_prefix = re.sub(r'/+', '/', proxy_prefix)
            replacement_string = f"{proxy_prefix}\\1"

            rewritten_content = re.sub(
                r'^(?!#)(.*)',
                replacement_string,
                original_content,
                flags=re.MULTILINE
            )

            return Response(rewritten_content, content_type='application/vnd.apple.mpegurl')
        else:
            # Stream video segments (.ts), keys, etc.
            return Response(
                response.iter_content(chunk_size=8192),
                content_type=response.headers.get('Content-Type', 'application/octet-stream'),
                status=response.status_code
            )

    except requests.RequestException as e:
        # Re-raise the exception so it can be caught by the Flask route
        logging.error(f"Error in proxy_stream_request for {video_path}: {e}")
        raise e