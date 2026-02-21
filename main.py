import warnings
warnings.filterwarnings("ignore")

import os, base64, time, sqlite3, re, email.utils
from datetime import datetime
from email_reply_parser import EmailReplyParser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from google import genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Ayarlar
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
DB_PATH = 'conversations.db'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "").strip()
IGNORE_LIST = ['binance', 'google', 'linkedin', 'no-reply', 'noreply', 'newsletter', 'trendyol', 'github', 'coursera', 'indeed']

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash-lite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS history (thread_id TEXT, role TEXT, content TEXT, timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS processed_messages (msg_id TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

def is_processed(msg_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM processed_messages WHERE msg_id = ?', (msg_id,))
    exists = c.fetchone()
    conn.close()
    return exists is not None

def mark_as_processed(msg_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO processed_messages VALUES (?)', (msg_id,))
    conn.commit()
    conn.close()

def save_history(thread_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (thread_id, role, content, now_str))
    conn.commit()
    conn.close()

def get_history(thread_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM history WHERE thread_id = ? ORDER BY timestamp DESC LIMIT 10", (thread_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r, "parts": [{"text": cnt}]} for r, cnt in reversed(rows)]

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_full_body(payload):
    content = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    elif 'body' in payload and 'data' in payload['body']:
        content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    if not content:
        return ""
        
    # Use robust parsing library to strip ALL previous thread/quote context reliably
    parsed_email = EmailReplyParser.read(content)
    visible_text = parsed_email.reply
    
    return visible_text.strip()

def process_emails():
    try:
        service = get_gmail_service()
        # Çok fazla maili aynı anda işleyip Gmail API'yi yormamak için maxResults: 3
        results = service.users().messages().list(userId='me', q='is:unread newer_than:30m', maxResults=3).execute()
        messages = results.get('messages', [])

        if not messages: return

        for msg in messages:
            msg_id = msg['id']
            if is_processed(msg_id): continue

            try:
                msg_full = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                headers = msg_full['payload']['headers']
                sender_raw = next(h['value'] for h in headers if h['name'] == 'From')
                _, sender_email = email.utils.parseaddr(sender_raw)
                
                if any(word in sender_email.lower() for word in IGNORE_LIST):
                    service.users().messages().batchModify(userId='me', body={'ids': [msg_id], 'removeLabelIds': ['UNREAD']}).execute()
                    mark_as_processed(msg_id)
                    continue

                thread_id = msg_full['threadId']
                orig_id = next(h['value'] for h in headers if h['name'] == 'Message-ID')
                subject = next(h['value'] for h in headers if h['name'] == 'Subject')
                full_content = get_full_body(msg_full['payload']) or msg_full['snippet']

                print(f"[*] Mesaj Alındı: {sender_email}")
                
                history = get_history(thread_id)
                chat = client.chats.create(
                    model=MODEL_ID, 
                    config={'system_instruction': "Sen Emin Kılıç'sın. Clemta demo otomasyonusun. Müşteri HANGİ DİLDE YAZIYORSA O DİLDE profesyonelce yanıt ver. İstenmediği sürece önceki mesajların bağlamını TEKRARLAMA veya ÖZETLEME. Sadece sorulan o anki cümlenin cevabını ver. LÜTFEN YANITLARININ UZUNLUĞUNU MAKSİMUM 120-150 KELİME (3-4 kısa paragraf) İLE SINIRLANDIR. E-POSTANIN BİTİMİNE KESİNLİKLE İMZA EKLEME (örn: Saygılarımla, Emin Kılıç, Clemta Demo Bot vb.) çünkü imza resim olarak otomatik ekleniyor."}, 
                    history=history
                )
                response = chat.send_message(full_content)
                
                ai_response = response.text.strip()
                # Sadece mesajın EN SONUNDAKİ imza kalıplarını güvenlice temizle (cümlenin ortasını kesmemek için)
                ai_response = re.sub(r'(?i)\s*(Saygılarımla|İyi çalışmalar|Best regards|Sincerely),?\s*(Emin Kılıç|Emin Kilic|Clemta Demo Bot)?\s*$', '', ai_response).strip()
                ai_response = re.sub(r'(?i)\n\s*(Emin Kılıç|Emin Kilic|Clemta Demo Bot)\s*$', '', ai_response).strip()

                if not ai_response: continue

                # Email yapısını hazırla
                clean_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"
                
                # HTML yapısında cevap ve imza
                html_content = ai_response.replace('\n', '<br>')
                html_body = f"""\
                <html>
                  <body>
                    <p style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
                      {html_content}
                    </p>
                    <div style="margin-top: 5px;">
                      <img src="cid:signature_image" alt="Emin Kılıç Signature" style="width: 200px; height: auto;">
                    </div>
                  </body>
                </html>
                """

                # Eğer resim varsa Multipart (HTML + Resim) gönder, yoksa sadece düz metin (Fallback) gönder
                if os.path.exists("signature.png"):
                    reply = MIMEMultipart('related')
                    
                    # HTML kısmını ekle
                    msg_alternative = MIMEMultipart('alternative')
                    reply.attach(msg_alternative)
                    msg_text = MIMEText(html_body, 'html', 'utf-8')
                    msg_alternative.attach(msg_text)

                    # Resmi ekle ve CID bağla
                    with open("signature.png", "rb") as img_file:
                        msg_image = MIMEImage(img_file.read(), name="signature.png")
                        msg_image.add_header('Content-ID', '<signature_image>')
                        msg_image.add_header('Content-Disposition', 'inline', filename="signature.png")
                        reply.attach(msg_image)
                else:
                    reply = MIMEText(f"{ai_response}\n\n--\nEmin Kılıç\nClemta Demo Bot", 'plain', 'utf-8')

                reply['To'] = sender_email
                reply['Subject'] = Header(clean_subject, 'utf-8').encode()
                reply['In-Reply-To'] = orig_id
                reply['References'] = orig_id
                
                service.users().messages().send(userId='me', body={'raw': base64.urlsafe_b64encode(reply.as_bytes()).decode(), 'threadId': thread_id}).execute()
                
                mark_as_processed(msg_id)
                service.users().messages().batchModify(userId='me', body={'ids': [msg_id], 'removeLabelIds': ['UNREAD']}).execute()
                save_history(thread_id, "user", full_content)
                save_history(thread_id, "model", ai_response)
                print(f"✅ Başarıyla Yanıtlandı: {sender_email}")
                time.sleep(3) # Gmail senkronizasyonu için biraz daha bekleme
            except Exception as e:
                # Sadece içeriği olan hataları bas, boş hataları görmezden gel
                err_msg = str(e).strip()
                if err_msg and "Message-ID" not in err_msg:
                    print(f"⚠️ Detay: {err_msg[:100]}")
    except Exception as e:
        if str(e).strip(): print(f"❌ Kritik: {str(e)[:100]}")

if __name__ == "__main__":
    init_db()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] CLEMTA BOT: STABİL VE TEMİZ LOG MODU.")
    while True:
        process_emails()
        time.sleep(30)
