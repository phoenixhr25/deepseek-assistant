from flask import Flask, request, render_template, session
import requests, os, time, csv, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv

# 本地加载 .env；线上请用平台环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "dev-only-secret")

# ===== 配置 =====
DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
AVAILABLE_MODELS = [
    {"id": "deepseek-chat", "name": "DeepSeek Chat (默认)"},
    {"id": "deepseek-reasoner", "name": "DeepSeek R1 (推理)"},
]

# ===== 日志（滚动文件 + CSV 统计；不记录正文/Key）=====
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)
handler = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"),
                              maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
app_logger.addHandler(handler)

CSV_PATH = os.path.join(LOG_DIR, "requests.csv")
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp", "ip_masked", "model", "status", "duration_ms"])

def mask_ip(ip: str) -> str:
    if not ip: return "-"
    part = ip.split(",")[0].strip()
    segs = part.split(".")
    return f"{segs[0]}.{segs[1]}.x.x" if len(segs) == 4 else part[:6] + "..."

def write_csv(ip_masked: str, model: str, status: str, duration_ms: int):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(timespec="seconds") + "Z",
            ip_masked, model, status, int(duration_ms)
        ])

# ===== DeepSeek 调用 =====
def call_deepseek(prompt, model, temperature, max_tokens, client_ip):
    if not DEEPSEEK_API_KEY:
        app_logger.error("DEEPSEEK_API_KEY missing")
        return None, "缺少 DEEPSEEK_API_KEY，请在项目根目录创建 .env 并填写。"

    start = time.time()
    try:
        r = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model or DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": float(temperature),
                "max_tokens": int(max_tokens)
            },
            timeout=30
        )
        status_code = r.status_code
        try:
            data = r.json()
        except Exception:
            data = {"error": {"message": f"非JSON响应 HTTP {status_code}"}}

        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        duration = (time.time() - start) * 1000
        ip_masked = mask_ip(client_ip)
        app_logger.info(f"ip={ip_masked} model={model} http={status_code} has_text={bool(text)} t_ms={int(duration)}")
        write_csv(ip_masked, model, "ok" if text else f"http_{status_code}", duration)

        if text:
            return text, None
        return None, data.get("error", {}).get("message", f"空响应（HTTP {status_code}）")

    except Exception as e:
        duration = (time.time() - start) * 1000
        ip_masked = mask_ip(client_ip)
        app_logger.exception(f"ip={ip_masked} model={model} status=exception t_ms={int(duration)}")
        write_csv(ip_masked, model, "exception", duration)
        return None, str(e)

@app.route("/healthz")
def healthz():
    return "ok"

@app.route("/", methods=["GET", "POST"])
def home():
    question = session.get("last_q", "")
    answer = ""
    error = ""
    model = DEFAULT_MODEL
    temperature = 0.3
    max_tokens = 300

    try:
        if request.method == "POST":
            question = (request.form.get("question") or "").strip()
            model = request.form.get("model") or DEFAULT_MODEL
            temperature = float(request.form.get("temperature", 0.3))
            max_tokens = int(request.form.get("max_tokens", 300))
            session["last_q"] = question

            if not DEEPSEEK_API_KEY:
                error = "未读取到 DEEPSEEK_API_KEY。请在项目根目录创建 .env，示例：\nDEEPSEEK_API_KEY=sk-xxxx\nAPP_SECRET=任意长字符串"
            else:
                client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "-")
                answer, err = call_deepseek(question, model, temperature, max_tokens, client_ip)
                if err: error = f"DeepSeek 出错：{err}"
    except Exception as e:
        error = f"页面处理异常：{e}"

    return render_template(
        "index.html",
        models=AVAILABLE_MODELS,
        selected_model=model,
        question=question,
        answer=answer,
        error=error,
        temperature=temperature,
        max_tokens=max_tokens
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
