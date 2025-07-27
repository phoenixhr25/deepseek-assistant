from flask import Flask, request, render_template
import requests
import os
from dotenv import load_dotenv  # ✅ 加载 .env 的库

load_dotenv()  # ✅ 读取 .env 文件

app = Flask(__name__)

API_KEY = os.getenv("DEEPSEEK_API_KEY")  # ✅ 从环境变量读取，不再硬编码
API_URL = "https://api.deepseek.com/v1/chat/completions"

def ask_deepseek(question):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个聪明又温柔的中文问答助手。"},
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
            answer = ask_deepseek(question)
    return render_template("index.html", question=question, answer=answer)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ✅ Render 会自动注入 PORT
    app.run(host="0.0.0.0", port=port, debug=True)
