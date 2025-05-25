from flask import Flask, render_template, request, jsonify
import requests
import os
import json
from datetime import datetime
import uuid
from markdown_it import MarkdownIt

app = Flask(__name__)

md = MarkdownIt()

# تنظیمات
LM_API_URL = "http://localhost:1234/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}
CONVERSATIONS_DIR = "conversations"

# ایجاد پوشه مکالمات اگر وجود نداشته باشد
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)

def save_conversation(conversation_id, title, messages):
    """ذخیره مکالمه در فایل"""
    filename = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    data = {
        "id": conversation_id,
        "title": title,
        "created_at": datetime.now().isoformat(),
        "messages": messages
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_conversation(conversation_id):
    """بارگذاری مکالمه از فایل"""
    filename = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.json")
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def list_conversations():
    """لیست تمام مکالمات ذخیره شده"""
    conversations = []
    for filename in os.listdir(CONVERSATIONS_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(CONVERSATIONS_DIR, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "title": data["title"],
                    "created_at": data["created_at"]
                })
    # مرتب سازی بر اساس تاریخ (جدیدترین اول)
    return sorted(conversations, key=lambda x: x["created_at"], reverse=True)

@app.route('/')
def home():
    return render_template('index.html', conversations=list_conversations())

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data['message']
    conversation_id = data.get('conversation_id')
    is_new_conversation = data.get('is_new', False)
    
    if is_new_conversation or not conversation_id:
        conversation_id = str(uuid.uuid4())
        conversation_title = user_message[:30] + ("..." if len(user_message) > 30 else "")
        messages = []
    else:
        conversation_data = load_conversation(conversation_id)
        if conversation_data:
            conversation_title = conversation_data["title"]
            messages = conversation_data["messages"]
        else:
            return jsonify({"error": "مکالمه یافت نشد"}), 404
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        payload = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": -1,
            "stream": False
        }
        
        response = requests.post(LM_API_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        bot_response = data['choices'][0]['message']['content']
        bot_response_html = md.render(bot_response)  # تبدیل markdown به HTML
        
        messages.append({"role": "assistant", "content": bot_response})
        save_conversation(conversation_id, conversation_title, messages)
        
        return jsonify({
            "response": bot_response_html,  # ارسال نسخه HTML به جای متن خام
            "conversation_id": conversation_id,
            "conversation_title": conversation_title,
            "is_new": is_new_conversation
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/conversations', methods=['GET'])
def get_conversations():
    return jsonify(list_conversations())

@app.route('/conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    conversation = load_conversation(conversation_id)
    if conversation:
        return jsonify(conversation)
    return jsonify({"error": "مکالمه یافت نشد"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)