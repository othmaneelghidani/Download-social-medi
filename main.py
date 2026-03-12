import telebot
import os
import yt_dlp

# جلب التوكن من متغيرات البيئة في Railway لحمايته
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك! 👋\n"
        "أرسل لي رابط فيديو أو ريلز (Reels) من إنستغرام وسأقوم بتحميله لك فوراً."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_instagram_link(message):
    url = message.text
    
    # التأكد من أن الرسالة تحتوي على رابط إنستغرام
    if "instagram.com" in url:
        # إرسال رسالة انتظار للمستخدم
        wait_msg = bot.reply_to(message, "⏳ جاري معالجة الرابط وتحميل الفيديو... يرجى الانتظار.")
        
        try:
            # إعدادات مكتبة التحميل
            ydl_opts = {
                'outtmpl': 'video_%(id)s.%(ext)s', # اسم الملف
                'format': 'best', # أفضل جودة
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # استخراج معلومات الفيديو وتحميله
                info = ydl.extract_info(url, download=True)
                video_file = ydl.prepare_filename(info)
            
            # إرسال الفيديو للمستخدم
            with open(video_file, 'rb') as video:
                bot.send_video(message.chat.id, video, reply_to_message_id=message.message_id)
            
            # حذف الفيديو من الخادم (Railway) لتوفير المساحة
            os.remove(video_file)
            
            # حذف رسالة "جاري التحميل..."
            bot.delete_message(message.chat.id, wait_msg.message_id)
            
        except Exception as e:
            # في حال حدوث خطأ (مثل حساب خاص أو رابط غير صحيح)
            bot.edit_message_text("❌ عذراً، حدث خطأ! تأكد من أن الرابط صحيح وأن الحساب عام (Public) وليس خاصاً.", chat_id=message.chat.id, message_id=wait_msg.message_id)
            print(f"Error: {e}")
    else:
        bot.reply_to(message, "الرجاء إرسال رابط إنستغرام صحيح 🔗.")

print("البوت يعمل الآن في الخلفية...")
bot.infinity_polling()
