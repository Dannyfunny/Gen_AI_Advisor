import streamlit as st
import plotly.express as px
import yfinance as yf
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime, timedelta

# ========== OpenRouter API Setup ==========
api_key = st.secrets["openrouter_api_key"]
model_name = st.secrets["openrouter_model"]
api_base = "https://openrouter.ai/api/v1"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

# ========== Simulated Login ==========
def login_section():
    st.sidebar.subheader("🔐 Simulated Login")
    email = st.sidebar.text_input("Enter your email")
    if st.sidebar.button("Login"):
        st.session_state['user'] = {"email": email}
        st.success(f"✅ Logged in as {email}")

# ========== Portfolio Allocation ==========
def get_portfolio_allocation(risk):
    if risk == "Low":
        return {"Equity": 30, "Debt": 60, "Gold": 10}
    elif risk == "Medium":
        return {"Equity": 50, "Debt": 40, "Gold": 10}
    else:
        return {"Equity": 70, "Debt": 20, "Gold": 10}

# ========== GPT Portfolio Explanation ==========
def explain_portfolio(allocation, age, risk, goal):
    prompt = f"""
    Act like a professional financial advisor. Explain this portfolio allocation for a {age}-year-old user with {risk} risk tolerance and goal: {goal}.
    The allocation is: Equity: {allocation['Equity']}%, Debt: {allocation['Debt']}%, Gold: {allocation['Gold']}%."""
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful financial advisor."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(f"{api_base}/chat/completions", headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]

# ========== CAGR Fetcher ==========
def fetch_cagr(ticker, years=5):
    end = datetime.now()
    start = end - timedelta(days=years * 365)
    data = yf.download(ticker, start=start, end=end)
    if data.empty or "Adj Close" not in data:
        return None
    start_price = data["Adj Close"].iloc[0]
    end_price = data["Adj Close"].iloc[-1]
    cagr = ((end_price / start_price) ** (1 / years)) - 1
    return round(cagr * 100, 2)

# ========== PDF Export ==========
def generate_pdf(name, age, income, risk, goal, allocation, explanation, mip_info=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Wealth Advisor Report", ln=True, align="C")

    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Name: {name} | Age: {age} | Income: ₹{income:,}", ln=True)
    pdf.cell(200, 10, f"Risk Tolerance: {risk} | Goal: {goal}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Portfolio Allocation:", ln=True)
    for asset, percent in allocation.items():
        pdf.cell(200, 10, f"{asset}: {percent}%", ln=True)

    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Advisor's Explanation:\n{explanation}")

    if mip_info:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"\nMonthly Investment Plan:\n"
                              f"{'Target: ₹' + str(mip_info['future_value']) if mip_info['mode'] == 'goal' else ''}\n"
                              f"Invest ₹{mip_info['monthly']:,}/month for {mip_info['years']} years "
                              f"at {mip_info['rate']}% expected return.\n"
                              f"{'Future Corpus: ₹' + str(mip_info['future_value']) if mip_info['mode'] == 'monthly' else ''}")
    pdf.output("/mnt/data/wealth_report.pdf")

# ========== Streamlit App ==========
st.set_page_config(page_title="GenAI Wealth Advisor", page_icon="💼")
st.title("💼 GenAI-Based Wealth Advisor Chatbot")

login_section()
if 'user' not in st.session_state:
    st.stop()

# Profile Inputs
st.subheader("👤 Profile Details")
age = st.slider("Age", 18, 70, 30)
income = st.number_input("Monthly Income (₹)", value=50000)
risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
goal = st.text_input("Primary Goal (e.g., retirement, house)")

if st.button("🔍 Generate Portfolio"):
    allocation = get_portfolio_allocation(risk_tolerance)

    fig = px.pie(
        names=list(allocation.keys()),
        values=list(allocation.values()),
        title="Your Investment Allocation",
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig)

    explanation = explain_portfolio(allocation, age, risk_tolerance, goal)
    st.markdown("### 📘 Advisor's Explanation")
    st.write(explanation)

    # ===== Monthly Investment Plan =====
    st.subheader("📈 Monthly Investment Plan")
    plan_type = st.radio("Choose Plan Type", ["🎯 I know my goal amount", "💸 I know my monthly investment"])

    rate = st.slider("Expected Annual Return (%)", 6.0, 15.0, 12.0)
    years = st.slider("Investment Duration (Years)", 1, 40, 10)
    months = years * 12
    monthly_rate = rate / 100 / 12

    mip_info = None

    if plan_type == "🎯 I know my goal amount":
        target = st.number_input("Target Corpus (₹)", value=4500000)
        monthly = target * monthly_rate / ((1 + monthly_rate) ** months - 1)
        monthly = round(monthly)
        st.success(f"To reach ₹{target:,} in {years} years at {rate}% return, invest ₹{monthly:,}/month.")
        mip_info = {"mode": "goal", "monthly": monthly, "years": years, "rate": rate, "future_value": target}
    else:
        monthly = st.number_input("Monthly Investment Amount (₹)", value=5000)
        future_value = monthly * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        future_value = round(future_value)
        st.success(f"Invest ₹{monthly:,}/month for {years} years at {rate}% to get ₹{future_value:,}")
        mip_info = {"mode": "monthly", "monthly": monthly, "years": years, "rate": rate, "future_value": future_value}

    # ===== CAGR Section with Average =====
    st.subheader("📉 Real-Time Return Estimates")
    returns = {
        "Equity": fetch_cagr("^NSEI"),
        "Debt": fetch_cagr("ICICIBANK.NS"),
        "Gold": fetch_cagr("GOLDBEES.NS")
    }

    df_cagr = pd.DataFrame({"Asset": returns.keys(), "CAGR (%)": returns.values()})
    st.dataframe(df_cagr)

    valid_returns = [r for r in returns.values() if r is not None]
    if valid_returns:
        avg_cagr = round(sum(valid_returns) / len(valid_returns), 2)
        st.info(f"📊 **Average CAGR across asset classes: {avg_cagr}%**")

    # ===== PDF Report =====
    if st.button("📄 Generate PDF Report"):
        generate_pdf("User", age, income, risk_tolerance, goal, allocation, explanation, mip_info)
        st.download_button("📥 Download PDF", open("/mnt/data/wealth_report.pdf", "rb"), "Wealth_Report.pdf")

    # ===== GPT Q&A =====
    st.subheader("💬 Ask About Your Portfolio")
    user_question = st.text_input("Type your question")

    if "gpt_response" not in st.session_state:
        st.session_state["gpt_response"] = ""

    if st.button("Ask GPT"):
        if user_question.strip() != "":
            prompt = f"The user has a portfolio: {allocation}, age {age}, goal: {goal}. Question: {user_question}"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a financial advisor."},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post(f"{api_base}/chat/completions", headers=headers, json=payload)
            reply = response.json()["choices"][0]["message"]["content"]
            st.session_state["gpt_response"] = reply

    if st.session_state["gpt_response"]:
        st.markdown("#### 🧠 GPT Answer:")
        st.write(st.session_state["gpt_response"])

    # ===== Feedback & Restart =====
    st.subheader("⭐ Rate Your Experience")
    rating = st.selectbox("How would you rate this output?", ["Select", "Excellent", "Good", "Average", "Poor"])
    if rating != "Select":
        st.success("🎉 Thank you for your feedback! You may restart the app now.")
        if st.button("🔄 Restart"):
            st.session_state.clear()
            st.experimental_rerun()
