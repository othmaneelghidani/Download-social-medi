import telebot
import yt_dlp
import instaloader
import os
import re
import glob
import shutil

# التوكن موضوع مباشرة كما طلبت
TOKEN = '8769012947:AAGAUv-nzlffQrbr_szn0rEfvlcWsVpR5Uc'
bot = telebot.TeleBot(TOKEN)

# إعداد المصدر الثاني (Instaloader)
L = instaloader.Instaloader(
    download_pictures=False,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False
)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! 👋\nأرسل لي رابط إنستغرام، وسأحاول تحميله باستخدام عدة مصادر لضمان نجاح العملية.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text
    
    if "instagram.com" not in url:
        bot.reply_to(message, "الرجاء إرسال رابط إنستغرام صحيح 🔗.")
        return

    wait_msg = bot.reply_to(message, "⏳ جاري التحميل... سأجرب المصدر الأول.")
    video_path = None

    # المحاولة الأولى: باستخدام yt-dlp
    try:
        ydl_opts = {
            'outtmpl': f'video_{message.chat.id}.%(ext)s',
            'format': 'best',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
    except Exception as e:
        print(f"Source 1 failed: {e}")
        bot.edit_message_text("المصدر الأول فشل، جاري تجربة المصدر الثاني 🔄...", chat_id=message.chat.id, message_id=wait_msg.message_id)

    # المحاولة الثانية: باستخدام Instaloader (تتدخل فقط إذا فشل الأول)
    if not video_path or not os.path.exists(video_path):
        try:
            # استخراج المعرف (Shortcode) من الرابط
            match = re.search(r'(?:p|reel|tv)/([^/?#&]+)', url)
            if match:
                shortcode = match.group(1)
                post = instaloader.Post.from_shortcode(L.context, shortcode)
                L.download_post(post, target=shortcode)
                
                # البحث عن ملف الفيديو المحمل في المجلد
                files = glob.glob(f"{shortcode}/*.mp4")
                if files:
                    video_path = files[0]
        except Exception as e:
            print(f"Source 2 failed: {e}")

    # إرسال الفيديو إذا نجح التحميل من أي من المصدرين
    if video_path and os.path.exists(video_path):
        try:
            bot.edit_message_text("✅ تم التحميل بنجاح! جاري الإرسال...", chat_id=message.chat.id, message_id=wait_msg.message_id)
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video, reply_to_message_id=message.message_id)
        except Exception as e:
            bot.reply_to(message, "❌ حدث خطأ أثناء إرسال الفيديو لتيليجرام.")
        finally:
            # تنظيف الملفات من سيرفر Railway حتى لا تمتلئ مساحة التخزين
            if 'yt-dlp' in str(video_path) or f'video_{message.chat.id}' in str(video_path):
                if os.path.exists(video_path):
                    os.remove(video_path)
            else:
                folder = os.path.dirname(video_path)
                if os.path.exists(folder):
                    shutil.rmtree(folder)
            
            # حذف رسالة الانتظار
            bot.delete_message(message.chat.id, wait_msg.message_id)
    else:
        bot.edit_message_text("❌ فشل التحميل من جميع المصادر. تأكد أن الحساب عام (Public) وليس خاصاً.", chat_id=message.chat.id, message_id=wait_msg.message_id)

print("البوت يعمل الآن...")
bot.infinity_polling()
