import streamlit as st
import math
from PIL import Image
import google.generativeai as genai
import json

st.set_page_config(page_title="AI 視覺減肥小幫手", layout="wide")
st.title("🏃‍♂️ AI 相機辨識熱量 × 智慧減肥小幫手")

# --- 初始化自訂食物與 AI 辨識紀錄 ---
if "custom_food" not in st.session_state:
    st.session_state.custom_food = {
        "茶葉蛋 (75大卡)": 75,
        "雞胸肉 (150大卡)": 150,
        "地瓜 (140大卡)": 140,
        "白飯 (1碗/280大卡)": 280,
    }

if "ai_detected_calories" not in st.session_state:
    st.session_state.ai_detected_calories = 0

if "ai_food_summary" not in st.session_state:
    st.session_state.ai_food_summary = ""

# --- 左側邊欄：個人資料與目標規劃 ---
st.sidebar.header("👤 個人基本資料與目標")
gender = st.sidebar.selectbox("性別", ["男", "女"])
age = st.sidebar.slider("年齡", 1, 100, 25)
height = st.sidebar.slider("身高 (cm)", 100, 220, 170)
current_weight = st.sidebar.slider("目前體重 (kg)", 30.0, 150.0, 70.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.header("🎯 減重目標設定")
target_weight = st.sidebar.slider("目標體重 (kg)", 30.0, 150.0, 65.0, step=0.1)

# API Key 輸入（讓用戶自由輸入自己的 Gemini Key）
st.sidebar.markdown("---")
st.sidebar.header("🔑 AI 辨識設定")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", help="使用相機功能需先去 Google AI Studio 免費申請 Key 貼過來")

# 計算核心數據
if gender == "男":
    bmr = 10 * current_weight + 6.25 * height - 5 * age + 5
else:
    bmr = 10 * current_weight + 6.25 * height - 5 * age - 161

tdee = bmr * 1.2  
daily_deficit = 350  
daily_budget = tdee - daily_deficit

# --- 規劃看板 ---
st.header("📅 減重進度預測藍圖")
if current_weight > target_weight:
    weight_to_lose = current_weight - target_weight
    total_calories_needed = weight_to_lose * 7700
    days_needed = math.ceil(total_calories_needed / daily_deficit)
    months_needed = days_needed / 30
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="需要減去的體重", value=f"{weight_to_lose:.1f} 公斤")
    with col2:
        st.metric(label="總共需創造的熱量缺口", value=f"{total_calories_needed:.0f} 大卡")
    with col3:
        st.metric(label="預計達成目標天數", value=f"{days_needed} 天", delta=f"約 {months_needed:.1f} 個月", delta_color="inverse")
else:
    st.success("🎉 您已達到或超越目標體重！")

st.markdown("---")

# --- 主畫面功能分頁 ---
tab1, tab2, tab3, tab4 = st.tabs(["📸 AI 相機偵測熱量", "🍽️ 今日飲食結算", "💧 減重飲水追蹤", "➕ 新增自訂菜單"])

with tab1:
    st.subheader("📷 拍下食物，讓 AI 幫你算卡路里")
    st.write("不知道吃什麼、多少熱量？直接用相機拍下來，AI 會自動辨識種類並估算大卡！")
    
    # 提供相機拍照與文件上傳兩種模式
    img_file = st.camera_input("📸 請將鏡頭對準你的食物拍照")
    
    if not img_file:
        img_file = st.file_uploader("或者從相簿上傳食物照片", type=["jpg", "jpeg", "png"])

    if img_file:
        # 顯示上傳的圖片
        image = Image.open(img_file)
        st.image(image, caption="待偵測的食物照片", width=300)
        
        if st.button("🚀 開始 AI 視覺辨識熱量"):
            if not api_key:
                st.error("❌ 請先在左側邊欄欄位輸入您的 Gemini API Key 才能啟動 AI 辨識功能喔！")
            else:
                with st.spinner("AI 正在看這盤菜，請稍候..."):
                    try:
                        # 設定 Gemini 密鑰與模型
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        # 設計提示詞，逼 AI 回傳嚴格的 JSON 格式
                        prompt = """
                        你是一位專業的營養師與食物AI辨識系統。
                        請幫我分析這張照片中的所有食物，並估算它的熱量。
                        請嚴格只回傳 JSON 格式，不要包含任何額外的 Markdown 語法（不要用 ```json 包裹），格式如下：
                        {
                            "food_list": "辨識出的食物詳細清單與各自大卡描述",
                            "total_calories": 總熱量數字(純整數)
                        }
                        """
                        
                        # 呼叫 AI
                        response = model.generate_content([prompt, image])
                        
                        # 解析結果
                        result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
                        
                        # 存入 Session State
                        st.session_state.ai_detected_calories = int(result["total_calories"])
                        st.session_state.ai_food_summary = result["food_list"]
                        
                        st.success("🎉 辨識成功！")
                    except Exception as e:
                        st.error(f"辨識出錯了，可能是 API Key 錯誤或網路問題。錯誤訊息: {e}")

    # 顯示 AI 辨識成果
    if st.session_state.ai_detected_calories > 0:
        st.info(f"📋 **AI 辨識報告：**\n{st.session_state.ai_food_summary}")
        st.metric(label="📸 相機今日偵測到總熱量", value=f"{st.session_state.ai_detected_calories} 大卡")
        if st.button("🗑️ 清空相機紀錄"):
            st.session_state.ai_detected_calories = 0
            st.session_state.ai_food_summary = ""
            st.rerun()

with tab2:
    st.subheader("🔥 今日熱量赤字追蹤")
    st.info(f"📋 今日建議飲食總熱量預算（已扣除 350 大卡赤字）：**{daily_budget:.0f}** 大卡")
    
    # 基礎手動點選餐食
    st.write("### 🍱 點選其他手動餐食份量")
    manual_calories = 0
    col_a, col_b = st.columns(2)
    for i, (food_name, calories) in enumerate(st.session_state.custom_food.items()):
        with col_a if i % 2 == 0 else col_b:
            count = st.number_input(f"{food_name}", min_value=0, max_value=10, value=0, step=1, key=f"food_{food_name}")
            manual_calories += count * calories
            
    st.markdown("---")
    # 加總：手動點選的 + 相機拍出來的
    total_consumed = manual_calories + st.session_state.ai_detected_calories
    
    st.markdown(f"### 🖐️ 手動點選攝取：**{manual_calories}** 大卡")
    st.markdown(f"### 📸 相機辨識攝取：**{st.session_state.ai_detected_calories}** 大卡")
    st.markdown(f"## 🚩 今日總共攝取熱量：**{total_consumed}** 大卡")
    
    # 結算
    remaining_calories = daily_budget - total_consumed
    st.subheader("📊 今日赤字結算看板")
    if remaining_calories >= 0:
        st.metric(label="剩餘可吃熱量額度", value=f"{remaining_calories:.0f} 大卡")
    else:
        st.metric(label="熱量已超標！", value=f"{remaining_calories:.0f} 大卡", delta_color="inverse")

with tab3:
    st.subheader("💧 減重飲水追蹤")
    water_target = current_weight * 50
    st.success(f"💡 減重人每日飲水目標（體重 x 50ml）：**{water_target:.0f}** ml")
    
    current_water = st.number_input(
        "今天喝了多少水？（每一千 CC 增加一格）", 
        min_value=0, max_value=10000, value=0, step=1000
    )
    water_remaining = water_target - current_water
    
    if water_remaining > 0:
        st.metric(label="還差多少水分達標", value=f"{water_remaining:.0f} ml")
        st.progress(min(current_water / water_target, 1.0))
    else:
        st.metric(label="🎉 飲水達標！太棒了！", value=f"已超過目標 {(current_water - water_target):.0f} ml")
        st.progress(1.0)

with tab4:
    st.subheader("➕ 擴充你的自訂菜單")
    new_food_name = st.text_input("食物名稱（例如：鮭魚便當、滷肉飯）")
    new_food_cal = st.number_input("這份食物的熱量（大卡）", min_value=1, max_value=2000, value=300, step=10)
    
    if st.button("➕ 新增至我的菜單庫"):
        if new_food_name:
            full_name = f"{new_food_name} ({new_food_cal}大卡)"
            st.session_state.custom_food[full_name] = new_food_cal
            st.success(f"已成功將「{new_food_name}」加入您的個人菜單庫！")
            st.rerun()
