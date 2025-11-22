import logging
import sys
import os
from datetime import timedelta, datetime, timezone

from flask import (
    Flask, render_template, jsonify, send_from_directory,
    session, redirect, url_for, request, make_response,
    g, flash, render_template_string
)

from util.streaming import proxy_stream_request, extract_video_credentials
from util.utils import parse_user_agent, is_valid_email
from fromm_api.FrommAPI import FrommAPI, ApiError

# Configuration
app = Flask(__name__)
app.secret_key = 'LeeNakkoWhyAreYouSoCool?!!' #replace this if you ever plan to make this online
CONTENT_HOST = "channel-contents.frommyarti.com"

# Global store for video credentials (replaces the Session for heavy data)
# Structure: { "tab_id_post_id": {creds_object} }
VIDEO_CREDS_STORE = {}

# Logger Configuration
log = app.logger
log.setLevel(logging.INFO)
if not log.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    log.addHandler(stream_handler)


@app.before_request
def load_api_from_session():
    data = session.get('fromm_api_data')
    g.api = FrommAPI.from_session_data(data)
    # check expired tokens
    if g.api.access_token and g.api.is_token_expired():
        log.info("Session expired. Logging out user.")
        g.api.signout()
        session.pop('fromm_api_data', None)
        if request.endpoint and 'static' not in request.endpoint and 'login' not in request.endpoint:
            flash("Your session has expired. Please login again.", "warning")


def save_api_to_session():
    session['fromm_api_data'] = g.api.get_session_data()


@app.template_filter('kst_format')
def kst_format_filter(timestamp_ms):
    try:
        timestamp_sec = timestamp_ms / 1000.0
        dt_utc = datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        kst_tz = timezone(timedelta(hours=9))
        dt_kst = dt_utc.astimezone(kst_tz)
        return dt_kst.strftime('%Y-%m-%d at %I:%M %p')
    except Exception:
        return str(timestamp_ms)


@app.route('/')
def index():
    if g.api.access_token:
        return redirect(url_for('channels_page'))
    return redirect(url_for('login_page'))


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if g.api.access_token:
        return redirect(url_for('channels_page'))

    if request.method == 'POST':
        email_input = request.form.get('username', '').strip()
        password_input = request.form.get('password', '').strip()
        device_id_input = request.form.get('deviceId', '').strip()
        user_agent_input = request.form.get('userAgent', '').strip()
        parsed_device_info = parse_user_agent(user_agent_input)

        if not is_valid_email(email_input):
            log.warning(f"Invalid email format: {email_input}")
            flash("Invalid email format provided.", "danger")
            return render_template('login.html', error="Invalid email format.")

        try:
            if not g.api.account.check_user_exists(email_input):
                log.warning(f"User not found: {email_input}")
                flash("Account not found.", "danger")
                return render_template('login.html', error="Account not found.")
        except Exception as e:
            log.error(f"API check failed: {e}")
            flash("Unable to verify account existence.", "danger")
            return render_template('login.html')

        try:
            if g.api.signin(email_input, password_input, device_id_input, user_agent_input, parsed_device_info):
                log.info(f"Login successful: {email_input}")
                save_api_to_session()
                flash("Logged in successfully!", "success")

                resp = make_response(redirect(url_for('channels_page')))
                resp.set_cookie('accessToken', g.api.access_token)
                return resp
            else:
                log.warning("Login failed: Invalid credentials")
                flash("Login failed. Invalid credentials.", "danger")
        except Exception as e:
            log.error(f"Login exception: {e}")
            flash(f"An error occurred: {e}", "danger")

        return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')


@app.route('/logout')
def logout_page():
    g.api.signout()
    session.pop('fromm_api_data', None)
    flash("You have been logged out.", "info")
    resp = make_response(redirect(url_for('login_page')))
    resp.delete_cookie('accessToken')
    return resp


@app.route('/channels')
def channels_page():
    if not g.api.access_token:
        return redirect(url_for('login_page'))

    channel_list = []
    try:
        channel_response = g.api.channel.get_channels()
        if channel_response.get('success'):
            channel_list = channel_response.get('data', {}).get("channels", [])
        else:
            log.warning(f"Channel fetch failed: {channel_response}")
            flash("Could not fetch channels from API.", "warning")
    except ApiError as e:
        log.error(f"API error: {e}")
        flash(f"Error fetching channels: {e}", "danger")

    return render_template('channels.html', channels=channel_list, active_page='channels')


@app.route('/videos/<string:channel_id>')
def videos_page(channel_id):
    if not g.api.access_token:
        return redirect(url_for('login_page'))

    session['last_channel_id'] = channel_id

    videos_live = {}
    is_last = True
    raw_last_post = {}

    try:
        posts_response = g.api.channel.get_posts(channel_id=channel_id, limit=50)
        if posts_response.get('success'):
            data = posts_response.get("data", {})
            is_last = data.get("isLast", True)
            raw_posts = data.get("posts", [])

            if raw_posts:
                raw_last_post = raw_posts[-1]

            for p in raw_posts:
                if p.get("type") == "live_record" and p.get('isVisible'):
                    videos_live[p["id"]] = {
                        "title": p["title"],
                        "displayStartAt": p["displayStartAt"],
                        "thumbnail": p["thumbnail"]
                    }
        else:
            log.warning(f"Post fetch failed: {posts_response}")
            flash("Could not fetch posts.", "warning")
    except ApiError as e:
        log.error(f"API error: {e}")
        flash(f"Error fetching channel: {e}", "danger")

    videos_list = sorted(videos_live.items(), key=lambda item: item[1]['displayStartAt'], reverse=True)

    return render_template(
        'videos.html',
        channel_id=channel_id,
        videos=videos_list,
        active_page='videos',
        is_last=is_last,
        last_post=raw_last_post
    )


@app.route('/api/load-more-videos', methods=['POST'])
def load_more_videos():
    if not g.api.access_token:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    channel_id = data.get('channel_id')
    last_post_data = data.get('last_post')

    if not channel_id or not last_post_data:
        return jsonify({'error': 'Missing data'}), 400

    new_videos_html = ""
    is_last = True
    next_last_post = None

    try:
        posts_response = g.api.channel.get_posts(
            channel_id=channel_id,
            limit=50,
            last_post=last_post_data
        )

        if posts_response.get('success'):
            resp_data = posts_response["data"]
            raw_posts = resp_data.get("posts", [])
            is_last = resp_data.get("isLast", True)

            if raw_posts:
                next_last_post = raw_posts[-1]

            videos_live = {}
            for p in raw_posts:
                if p["type"] == "live_record" and p['isVisible']:
                    videos_live[p["id"]] = {
                        "title": p["title"],
                        "displayStartAt": p["displayStartAt"],
                        "thumbnail": p["thumbnail"]
                    }

            videos_list = sorted(videos_live.items(), key=lambda item: item[1]['displayStartAt'], reverse=True)

            template_fragment = """
            {% for video_id, video_data in videos %}
            <a href="{{ url_for('player_page', channel_id=channel_id, post_id=video_id) }}" class="block bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors shadow overflow-hidden">
                <img src="{{ video_data.thumbnail.url }}" alt="Thumbnail for {{ video_data.title }}" class="w-full h-40 object-cover">
                <div class="p-4">
                    <h2 class="font-semibold text-lg truncate" title="{{ video_data.title }}">{{ video_data.title }}</h2>
                    <p class="text-sm text-gray-400">{{ video_data.displayStartAt | kst_format }}</p>
                </div>
            </a>
            {% endfor %}
            """

            new_videos_html = render_template_string(
                template_fragment,
                videos=videos_list,
                channel_id=channel_id
            )

    except Exception as e:
        log.error(f"Error loading more videos: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'html': new_videos_html,
        'isLast': is_last,
        'lastPost': next_last_post
    })


@app.route('/player/<string:channel_id>/<int:post_id>')
def player_page(channel_id, post_id):
    if not g.api.access_token:
        return redirect(url_for('login_page'))

    log.info(f"Serving player: channel={channel_id}, post={post_id}")
    return render_template('player.html', channel_id=channel_id, post_id=post_id)


@app.route('/api/post/<string:channel_id>/<int:post_id>')
def get_post_info(channel_id, post_id):
    if not g.api.access_token:
        return jsonify({"error": "Not authenticated"}), 401

    tab_id = request.headers.get('X-Tab-ID')
    if not tab_id:
        return jsonify({"error": "Tab ID header missing"}), 400

    try:
        videos_info = g.api.channel.get_post(channel_id=channel_id, post_id=post_id)
        if not videos_info.get('success'):
            log.warning(f"Video info fetch failed: {videos_info}")
            return jsonify({"error": "Could not fetch video info"}), 500

        video_data = extract_video_credentials(videos_info)
        if not video_data:
            return jsonify({"error": "Post data or URL not found"}), 404

        # We combine Tab ID + Post ID so one tab can even handle multiple posts if needed
        storage_key = f"{tab_id}_{post_id}"
        VIDEO_CREDS_STORE[storage_key] = video_data['creds']
        if 'master_url' in video_data['post_data']:
            video_data['post_data']['url'] = video_data['post_data']['master_url']
            log.info("Master playlist used to stream")
        return jsonify(video_data['post_data'])

    except ApiError as e:
        log.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/stream/p<int:post_id>/<path:video_path>')
def stream_proxy(post_id, video_path):
    tab_id = request.args.get('tid')

    if not tab_id:
        tab_id = request.headers.get('X-Tab-ID')
    if not tab_id:
        # log.error("Stream proxy: Missing Tab ID")
        return "Missing Tab ID", 400

    storage_key = f"{tab_id}_{post_id}"
    stream_creds = VIDEO_CREDS_STORE.get(storage_key)

    if not stream_creds:
        return "Streaming credentials expired or missing. Please refresh.", 401

    try:
        mapped_creds = {
            "CloudFront-Key-Pair-Id": stream_creds['publicKey'],
            "CloudFront-Signature": stream_creds['signature'],
            "CloudFront-Policy": stream_creds['policy']
        }
        return proxy_stream_request(
            post_id,
            video_path,
            mapped_creds,
            CONTENT_HOST,
            user_agent_string=g.api.user_agent_string,
            device_info=g.api.device_info
        )
    except KeyError as e:
        log.error(f"Stream proxy creds error: {e}")
        return "Invalid streaming credentials format.", 500
    except Exception as e:
        log.error(f"Stream proxy error: {e}")
        return f"Error proxying request: {e}", 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'clomm.ico',
        mimetype='image/vnd.microsoft.icon'
    )


if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)