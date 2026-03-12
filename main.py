import telebot
import yt_dlp
import instaloader
import requests
import os
import re
import glob
import shutil
import time

TOKEN = '8769012947:AAGAUv-nzlffQrbr_szn0rEfvlcWsVpR5Uc'
bot = telebot.TeleBot(TOKEN)

L = instaloader.Instaloader(
    download_pictures=False,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False
)

# دالة مساعدة لتحميل الملف من رابط مباشر
def download_from_url(url, filename):
    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except:
        return False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! 👋\nأرسل لي أي رابط من **إنستغرام** أو **تيك توك**، وسأقوم بتحميله لك بأعلى جودة.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text
    chat_id = message.chat.id
    
    is_instagram = "instagram.com" in url
    is_tiktok = "tiktok.com" in url or "vm.tiktok.com" in url

    if not (is_instagram or is_tiktok):
        bot.reply_to(message, "الرجاء إرسال رابط صحيح من إنستغرام أو تيك توك 🔗.")
        return

    wait_msg = bot.reply_to(message, "⏳ جاري جلب الفيديو من المصادر المتعددة...")
    video_path = f"video_{chat_id}_{int(time.time())}.mp4"
    download_success = False

    # ----------------- قسم التيك توك -----------------
    if is_tiktok:
        # المصدر الأول: TikWM API (بدون علامة مائية)
        try:
            bot.edit_message_text("⏳ جاري التحميل من تيك توك (المصدر 1)...", chat_id=chat_id, message_id=wait_msg.message_id)
            api_url = f"https://www.tikwm.com/api/?url={url}"
            res = requests.get(api_url, timeout=10).json()
            if res.get('code') == 0:
                play_url = res['data']['play']
                if download_from_url(play_url, video_path):
                    download_success = True
        except Exception as e:
            print(f"TikTok API Error: {e}")

    # ----------------- قسم الإنستغرام -----------------
    elif is_instagram:
        # المصدر الأول: Cobalt API (ممتاز لتخطي حظر السيرفرات)
        if not download_success:
            try:
                bot.edit_message_text("⏳ جاري التحميل من إنستغرام (API خارجي)...", chat_id=chat_id, message_id=wait_msg.message_id)
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                data = {"url": url}
                res = requests.post("https://api.cobalt.tools/api/json", json=data, headers=headers, timeout=10)
                if res.status_code == 200:
                    video_url = res.json().get("url")
                    if video_url and download_from_url(video_url, video_path):
                        download_success = True
            except Exception as e:
                print(f"Cobalt API Error: {e}")

    # ----------------- المصادر البديلة (yt-dlp) -----------------
    if not download_success:
        try:
            bot.edit_message_text("⏳ جاري تجربة المصدر البديل (yt-dlp)...", chat_id=chat_id, message_id=wait_msg.message_id)
            ydl_opts = {
                'outtmpl': video_path,
                'format': 'best',
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                if os.path.exists(video_path):
                    download_success = True
        except Exception as e:
            print(f"yt-dlp Error: {e}")

    # ----------------- المصدر الأخير لإنستغرام (Instaloader) -----------------
    if not download_success and is_instagram:
        try:
            bot.edit_message_text("⏳ جاري تجربة المصدر الأخير...", chat_id=chat_id, message_id=wait_msg.message_id)
            match = re.search(r'(?:p|reel|tv)/([^/?#&]+)', url)
            if match:
                shortcode = match.group(1)
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=shortcode)
                files = glob.glob(f"{shortcode}/*.mp4")
                if files:
                    # نقل الملف للمسار الأساسي لسهولة الإرسال
                    shutil.move(files[0], video_path)
                    download_success = True
                # تنظيف مجلد Instaloader
                if os.path.exists(shortcode):
                    shutil.rmtree(shortcode)
        except Exception as e:
            print(f"Instaloader Error: {e}")

    # ----------------- إرسال الفيديو -----------------
    if download_success and os.path.exists(video_path):
        try:
            bot.edit_message_text("✅ تم التحميل! جاري الإرسال...", chat_id=chat_id, message_id=wait_msg.message_id)
            with open(video_path, 'rb') as video:
                bot.send_video(chat_id, video, reply_to_message_id=message.message_id)
        except Exception as e:
            bot.reply_to(message, "❌ حجم الفيديو كبير جداً أو حدث خطأ أثناء الإرسال للتطبيق.")
        finally:
            # تنظيف الملف لضمان عدم امتلاء السيرفر
            if os.path.exists(video_path):
                os.remove(video_path)
            bot.delete_message(chat_id, wait_msg.message_id)
    else:
        bot.edit_message_text("❌ فشل التحميل من جميع المصادر المتاحة. قد يكون الحساب خاصاً، أو أن المنصة قامت بحظر الاتصال مؤقتاً.", chat_id=chat_id, message_id=wait_msg.message_id)

print("البوت يعمل الآن ومستعد لتنزيل (إنستغرام + تيك توك)...")
bot.infinity_polling()
