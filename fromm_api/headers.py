def get_base_web_headers(device_info, user_agent_string):
    """
    Headers that mimic a mobile web browser.
    Used for the 'channel-api'.
    """
    return {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'country': 'KR',
        'language': 'ko',
        'Origin': 'https://channel.frommyarti.com',
        'Referer': 'https://channel.frommyarti.com/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Android WebView";v="140"' if device_info["os"] == "Android" else '"Safari";v="17", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': f'"{device_info["os"]}"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'timezone': 'Asia/Seoul',
        'User-Agent': user_agent_string,
        'X-Requested-With': 'com.knowmerce.fromm.fan'
    }

def get_base_app_headers():
    """
    Headers that mimic the 'okhttp' user agent.
    Used for the 'account-api'.
    """
    return {
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json; charset=UTF-8',
        'User-Agent': 'okhttp/5.1.0'
    }

def get_base_fromm_headers(device_info):
    """
    Headers that mimic the 'Fromm(fan...)' user agent.
    Used for the main 'api.frommyarti.com'.
    """
    return {
        'Accept-Encoding': 'gzip',
        'Connection': 'Keep-Alive',
        'User-Agent': f'Fromm(fan-1.38.1;{device_info["os"].lower()};{device_info["os_version"]};{device_info["model"]})',
        'Content-Type': 'application/json; charset=UTF-8' # Added based on POST example
    }