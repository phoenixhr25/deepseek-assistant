import os
import requests
from flask import Flask, request, render_template

app = Flask(__name__)

API_KEY = os.getenv("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")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "deepseek-ai/deepseek-chat"  # 可换成任意支持的模型

def ask_openrouter(question):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",  # 可选
        "X-Title": "DeepSeek Assistant"  # 可选标题
    }
    data = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a friendly and intelligent multilingual assistant. Please always respond in the same language as the user's question."},
            {"role": "user", "content": question}
        ]
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        elif "error" in result:
            return "出错啦：" + result["error"].get("message", "未知错误")
        else:
            return f"未知响应: {result}"
    except Exception as e:
        return "请求异常：" + str(e)

@app.route("/", methods=["GET", "POST"])
def home():
    answer = ""
    question = ""
    if request.method == "POST":
        question = request.form.get("question")
        if question:
            answer = ask_openrouter(question)
    return render_template("index.html", question=question, answer=answer)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
