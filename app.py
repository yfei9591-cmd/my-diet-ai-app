import streamlit as st
import datetime
import sqlite3
from PIL import Image
import google.generativeai as genai

# 1. 建立或連線到雲端在地資料庫
def init_db():
    conn = sqlite3.connect('diet_tracker.db')
    c = conn.cursor()
    # 建立體重與飲水紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_records (
            date TEXT PRIMARY KEY,
            weight REAL,
            height REAL,
            age INTEGER,
            water INTEGER
        )
    ''')
    # 建立食物照片紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            food_desc TEXT,
            calories INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. 設定 Google AI（請記得在 Streamlit 後台設定你的 API Key）
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.warning("請在 Streamlit Secrets 中設定 GOOGLE_API_KEY")

st.title("🍎 智慧減肥與健康追蹤日記")

# ----------------- 功能一：日期選擇（想紀錄哪一天，就選哪一天） -----------------
st.header("📅 選擇紀錄日期")
selected_date = st.date_input("你想記錄或查看哪一天的日記？", datetime.date.today())
date_str = selected_date.strftime("%Y-%m-%d")

# 讀取當天已有的身體舊資料
conn = sqlite3.connect('diet_tracker.db')
c = conn.cursor()
c.execute("SELECT height, weight, age, water FROM daily_records WHERE date = ?", (date_str,))
db_data = c.fetchone()
conn.close()

default_height = db_data[0] if db_data else 165.0
default_weight = db_data[1] if db_data else 60.0
default_age = db_data[2] if db_data else 30
default_water = db_data[3] if db_data else 0

# ----------------- 功能二：精準數值輸入（終結不好用的左右拉桿） -----------------
st.header("⚖️ 身體數值更新")

# 使用「加減號按鈕」數值輸入框，可以用手機鍵盤直接打，也可以按左右的＋－號精準微調
col1, col2, col3 = st.columns(3)
with col1:
    height = st.number_input("身高 (cm)", min_value=50.0, max_value=250.0, value=default_height, step=0.1, format="%.1f")
with col2:
    weight = st.number_input("體重 (kg)", min_value=10.0, max_value=300.0, value=default_weight, step=0.1, format="%.1f")
with col3:
    age = st.number_input("年齡 (歲)", min_value=1, max_value=120, value=default_age, step=1)

if st.button("儲存今日身體數值"):
    conn = sqlite3.connect('diet_tracker.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_records (date, height, weight, age, water)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            height=excluded.height,
            weight=excluded.weight,
            age=excluded.age
    ''', (date_str, height, weight, age, default_water))
    conn.commit()
    conn.close()
    st.success(f"💾 {date_str} 的身體資料已成功存檔！")

# ----------------- 功能三：📸 AI 食物相機紀錄 -----------------
st.header("📸 AI 飲食相機日記")

img_file = st.file_uploader("拍下或上傳食物照片", type=["jpg", "jpeg", "png"])

if img_file is not None:
    image = Image.open(img_file)
    st.image(image, caption="準備分析的食物", use_container_width=True)
    
    if st.button("讓 AI 分析並記錄這餐"):
        with st.spinner("AI 正在努力算熱量中..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "請幫我辨識這張圖片中的食物，並給出預估的總熱量（只需給出簡單的食物名稱與大卡數，例如：炸雞便當，約 750 大卡）。"
                response = model.generate_content([prompt, image])
                ai_result = response.text
                
                # 這裡簡單假設一個估算熱量，實際應用中可由 AI 格式化輸出
                st.info(f"🔮 AI 分析結果：\n{ai_result}")
                
                # 將這餐記錄進資料庫
                now_time = datetime.datetime.now().strftime("%H:%M")
                conn = sqlite3.connect('diet_tracker.db')
                c = conn.cursor()
                c.execute("INSERT INTO food_records (date, time, food_desc, calories) VALUES (?, ?, ?, ?)", 
                          (date_str, now_time, ai_result, 0))
                conn.commit()
                conn.close()
                st.success("飲食已同步記進當天日記本中！")
            except Exception as e:
                st.error(f"AI 連線失敗，請檢查金鑰。錯誤回報: {e}")

# ----------------- 功能四：💧 喝水計數器 -----------------
st.header("💧 喝水追蹤")
st.subheader(f"目前已喝： {default_water} cc")

col_w1, col_w2 = st.columns(2)
with col_w1:
    if st.button("＋ 增加 250cc"):
        default_water += 250
        conn = sqlite3.connect('diet_tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO daily_records (date, water) VALUES (?, ?) ON CONFLICT(date) DO UPDATE SET water=excluded.water", (date_str, default_water))
        conn.commit()
        conn.close()
        st.rerun()
with col_w2:
    if st.button("🗑️ 飲水歸零"):
        default_water = 0
        conn = sqlite3.connect('diet_tracker.db')
        c = conn.cursor()
        c.execute("INSERT INTO daily_records (date, water) VALUES (?, ?) ON CONFLICT(date) DO UPDATE SET water=excluded.water", (date_str, default_water))
        conn.commit()
        conn.close()
        st.rerun()

# ----------------- 功能五：📜 歷史日記查閱區 -----------------
st.write("---")
st.header(f"📜 {date_str} 的健康日記小結")

conn = sqlite3.connect('diet_tracker.db')
c = conn.cursor()
c.execute("SELECT time, food_desc FROM food_records WHERE date = ?", (date_str,))
today_foods = c.fetchall()
conn.close()

if today_foods:
    st.markdown("**🍴 這天吃了這些東西：**")
    for row in today_foods:
        st.write(f"- 🕒 [{row[0]}] {row[1]}")
else:
    st.write("填寫上方相機功能，這天還沒有吃東西的紀錄喔。")
