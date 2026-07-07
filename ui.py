import streamlit as st
import requests
import json
import time
from datetime import datetime

# --- Configuration ---
API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Abstergo Support AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    /* ========== GLOBAL ========== */
    .main {
        padding: 1.5rem 2rem;
    }
    
    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ========== HEADER ========== */
    .header-container {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 1.5rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }
    .header-icon {
        font-size: 3rem;
        filter: drop-shadow(0 0 10px rgba(100, 200, 255, 0.3));
    }
    .header-title {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .header-subtitle {
        color: #a8b2d1;
        font-size: 0.9rem;
        margin-top: -2px;
        letter-spacing: 0.3px;
    }
    .header-time {
        color: #8892b0;
        font-size: 0.85rem;
        background: rgba(255,255,255,0.06);
        padding: 0.4rem 1.2rem;
        border-radius: 30px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    
    /* ========== SIDEBAR ========== */
    .css-1d391kg {background-color: #0a0a1a;}
    .css-1d391kg .stButton > button {
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .css-1d391kg .stButton > button:hover {
        transform: translateX(4px);
    }
    
    /* ========== CARDS ========== */
    .card {
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    .card:hover {
        border-color: rgba(247, 151, 30, 0.3);
        box-shadow: 0 8px 30px rgba(0,0,0,0.25);
    }
    
    /* ========== REPLY BOX ========== */
    .reply-box {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-left: 5px solid #f7971e;
        padding: 1.8rem 2.2rem;
        border-radius: 14px;
        margin-top: 1rem;
        white-space: pre-wrap;
        font-family: 'Segoe UI', -apple-system, sans-serif;
        line-height: 1.8;
        color: #e6e6e6;
        box-shadow: 0 4px 24px rgba(247, 151, 30, 0.08);
        transition: all 0.4s ease;
        border: 1px solid rgba(247, 151, 30, 0.1);
    }
    .reply-box:hover {
        border-color: rgba(247, 151, 30, 0.3);
        box-shadow: 0 8px 32px rgba(247, 151, 30, 0.12);
        transform: translateY(-2px);
    }
    .reply-box strong {
        color: #f7971e;
    }
    
    /* ========== STATUS BADGES ========== */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        border-radius: 30px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    .badge-online {
        background: rgba(46, 213, 115, 0.15);
        color: #2ed573;
        border: 1px solid rgba(46, 213, 115, 0.2);
    }
    .badge-offline {
        background: rgba(255, 107, 107, 0.12);
        color: #ff6b6b;
        border: 1px solid rgba(255, 107, 107, 0.2);
    }
    .badge-judge-on {
        background: rgba(54, 172, 255, 0.12);
        color: #36acff;
        border: 1px solid rgba(54, 172, 255, 0.2);
    }
    .badge-judge-off {
        background: rgba(255, 165, 0, 0.12);
        color: #ffa500;
        border: 1px solid rgba(255, 165, 0, 0.2);
    }
    
    /* ========== METRICS ========== */
    .metric-box {
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 0.9rem 1rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-box:hover {
        border-color: rgba(247, 151, 30, 0.2);
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #f7971e, #ffd200);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #8892b0;
        margin-top: 2px;
    }
    
    /* ========== STEP INDICATORS ========== */
    .step-container {
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 0.8rem 1.2rem;
        border: 1px solid rgba(255,255,255,0.05);
        margin-bottom: 1rem;
    }
    .step-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
        transition: all 0.3s ease;
    }
    .step-active {
        background: #f7971e;
        animation: pulse 1.2s infinite;
        box-shadow: 0 0 20px rgba(247, 151, 30, 0.4);
    }
    .step-done {
        background: #2ed573;
        box-shadow: 0 0 12px rgba(46, 213, 115, 0.3);
    }
    .step-waiting {
        background: #2d3436;
        opacity: 0.4;
    }
    .step-label {
        color: #ccd6f6;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .step-label.done { color: #2ed573; }
    .step-label.active { color: #f7971e; }
    .step-label.waiting { color: #636e72; }
    
    @keyframes pulse {
        0% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.15); }
        100% { opacity: 0.6; transform: scale(1); }
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(247, 151, 30, 0.25);
    }
    
    /* ========== FOOTER ========== */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #636e72;
        font-size: 0.75rem;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 2rem;
        letter-spacing: 0.5px;
    }
    
    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0a1a; }
    ::-webkit-scrollbar-thumb { 
        background: linear-gradient(180deg, #f7971e, #ffd200);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover { background: #f7971e; }
</style>
""", unsafe_allow_html=True)

# --- Initialize session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "last_reply" not in st.session_state:
    st.session_state.last_reply = None
if "processing_time" not in st.session_state:
    st.session_state.processing_time = None
if "email" not in st.session_state:        # <-- NEW: Store email for clear history
    st.session_state.email = "test@example.com"

# ========================================
# HEADER (Premium)
# ========================================
st.markdown("""
<div class="header-container">
    <div class="header-left">
        <span class="header-icon">🧠</span>
        <div>
            <div class="header-title">Abstergo Support AI</div>
            <div class="header-subtitle">Enterprise Customer Support • Self-Correcting RAG • LLM-as-Judge</div>
        </div>
    </div>
    <div class="header-time">🕒 """ + datetime.now().strftime('%H:%M') + """</div>
</div>
""", unsafe_allow_html=True)

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown("### ⚙️ System Status")
    
    # Backend health
    backend_online = False
    try:
        health = requests.get(f"{API_URL}/health", timeout=2)
        if health.status_code == 200:
            st.markdown('✅ **Backend:** <span class="status-badge badge-online">Online</span>', unsafe_allow_html=True)
            backend_online = True
        else:
            st.markdown('⚠️ **Backend:** <span class="status-badge badge-offline">Unhealthy</span>', unsafe_allow_html=True)
    except:
        st.markdown('❌ **Backend:** <span class="status-badge badge-offline">Offline</span>', unsafe_allow_html=True)
        st.warning("Start FastAPI: `uvicorn app.main:app --reload`")

    # Judge status
    st.divider()
    st.markdown("### 🧑‍⚖️ LLM-as-Judge")
    if backend_online:
        try:
            judge_resp = requests.get(f"{API_URL}/api/hitl/status", timeout=2)
            if judge_resp.status_code == 200:
                mode = judge_resp.json().get("mode", True)
                if mode:
                    st.markdown('🔒 **Mode:** <span class="status-badge badge-judge-on">Manual Approval</span>', unsafe_allow_html=True)
                else:
                    st.markdown('🚀 **Mode:** <span class="status-badge badge-judge-off">Auto-Send</span>', unsafe_allow_html=True)
        except:
            st.caption("⚠️ Judge status unavailable")
    else:
        st.caption("⏳ Waiting for backend...")

    # Quick Examples
    st.divider()
    st.markdown("### ⚡ Quick Examples")
    st.caption("Click to auto-fill:")
    
    examples = [
        "What is your refund policy?",
        "How do I reset my password?",
        "My app crashes on startup, what should I do?",
        "I was charged twice for my Pro plan.",
    ]
    
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state.example_query = ex
            st.rerun()

    # ========================================
    # HISTORY + CLEAR BUTTON (UPDATED)
    # ========================================
    st.divider()
    st.markdown("### 📜 History")
    if st.session_state.history:
        for i, (q, _) in enumerate(st.session_state.history[-5:]):
            st.caption(f"{i+1}. {q[:60]}...")
        if len(st.session_state.history) > 5:
            st.caption(f"... and {len(st.session_state.history) - 5} more")
    else:
        st.caption("No conversations yet.")
    
    # --- NEW: Clear Chat History Button ---
    if st.button("🗑️ Clear Chat History", use_container_width=True, key="clear_history_btn"):
        try:
            email = st.session_state.get("email", "test@example.com")
            response = requests.post(f"{API_URL}/clear_history/{email}")
            if response.status_code == 200:
                st.session_state.history = []
                st.session_state.last_reply = None
                st.success("✅ History cleared successfully!")
                st.rerun()
            else:
                st.error(f"❌ Failed to clear history: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Cannot connect to backend. Make sure FastAPI is running.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    # Tech Stack
    st.divider()
    st.caption("🤖 **Model:** Llama 3 (local)")
    st.caption("📦 **Vector DB:** Chroma (Hybrid RAG)")
    st.caption("🔗 **Memory:** Semantic Vector + SQLite")
    st.caption("🐳 **Deploy:** Docker + FastAPI")

# ========================================
# MAIN QUERY INTERFACE
# ========================================
st.markdown("### 💬 Submit a Support Ticket")

example_query = st.session_state.get("example_query", "")
if example_query:
    default_question = example_query
    st.session_state.example_query = ""
else:
    default_question = ""

with st.form("support_form", clear_on_submit=False):
    col_email, col_name = st.columns(2)
    with col_email:
        email = st.text_input(
            "📧 Customer Email",
            value=st.session_state.get("email", "test@example.com"),  # <-- Use session state
            help="Used to fetch CRM profile and long-term memory."
        )
    with col_name:
        name = st.text_input(
            "👤 Customer Name (optional)",
            placeholder="e.g., John Doe",
            help="Overrides the name from CRM (useful for testing)."
        )
    
    question = st.text_area(
        "📝 Describe your issue",
        value=default_question,
        placeholder="e.g., I need a refund for my Pro plan. I was charged twice this month.",
        height=130,
    )
    
    col_submit1, col_submit2 = st.columns([4, 1])
    with col_submit1:
        submitted = st.form_submit_button("🚀 Generate Reply", use_container_width=True)
    with col_submit2:
        clear = st.form_submit_button("🗑️ Clear", use_container_width=True)
        if clear:
            st.session_state.last_reply = None
            st.rerun()

# ========================================
# PROCESS QUERY
# ========================================
if submitted:
    if not question.strip():
        st.warning("⚠️ Please describe your issue.")
        st.stop()
    
    if not email.strip():
        st.warning("⚠️ Please enter a valid email.")
        st.stop()
    
    # --- Store email in session state for clear history ---
    st.session_state.email = email.strip()
    
    # --- Progress Steps ---
    status_placeholder = st.empty()
    reply_container = st.container()
    
    with status_placeholder.container():
        st.markdown("""
        <div class="step-container">
            <span class="step-dot step-active"></span> <span class="step-label active">RAG Retrieval</span> &nbsp;&nbsp;
            <span class="step-dot step-waiting"></span> <span class="step-label waiting">LLM Generation</span> &nbsp;&nbsp;
            <span class="step-dot step-waiting"></span> <span class="step-label waiting">Judge Review</span>
        </div>
        """, unsafe_allow_html=True)
    
    start_time = time.time()
    
    try:
        payload = {"email": email.strip(), "message": question.strip()}
        
        with status_placeholder.container():
            st.markdown("""
            <div class="step-container">
                <span class="step-dot step-done"></span> <span class="step-label done">✅ RAG Retrieval</span> &nbsp;&nbsp;
                <span class="step-dot step-active"></span> <span class="step-label active">LLM Generation</span> &nbsp;&nbsp;
                <span class="step-dot step-waiting"></span> <span class="step-label waiting">Judge Review</span>
            </div>
            """, unsafe_allow_html=True)
        
        response = requests.post(f"{API_URL}/chat", json=payload, timeout=120)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get("reply", "No reply generated.")
            
            with status_placeholder.container():
                st.markdown("""
                <div class="step-container">
                    <span class="step-dot step-done"></span> <span class="step-label done">✅ RAG Retrieval</span> &nbsp;&nbsp;
                    <span class="step-dot step-done"></span> <span class="step-label done">✅ LLM Generation</span> &nbsp;&nbsp;
                    <span class="step-dot step-done"></span> <span class="step-label done">✅ Judge Review</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.session_state.history.append((question, reply[:100] + "..."))
            st.session_state.last_reply = reply
            st.session_state.processing_time = elapsed
            
            with reply_container:
                st.success(f"✅ Reply generated in {elapsed:.2f} seconds!")
                
                # Metrics
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{elapsed:.1f}s</div>
                        <div class="metric-label">⏱️ Response Time</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_m2:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{len(reply.split())}</div>
                        <div class="metric-label">📝 Words</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_m3:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-value">{len(question.split())}</div>
                        <div class="metric-label">❓ Query Length</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("#### 📧 Email Draft")
                st.markdown(f"""
                <div class="reply-box">
                    {reply.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
                
                col_act1, col_act2, col_act3 = st.columns([1, 1, 2])
                with col_act1:
                    st.download_button(
                        label="📥 Download .txt",
                        data=reply,
                        file_name=f"reply_{email.split('@')[0]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with col_act2:
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText(`{reply.replace('`', '\\`')}`)" 
                                style="width:100%; padding:0.6rem; border-radius:10px; 
                                       border:1px solid rgba(255,255,255,0.1); 
                                       background:rgba(255,255,255,0.05); 
                                       color:#ccd6f6; cursor:pointer; font-weight:600;
                                       transition:all 0.2s ease;">
                        📋 Copy
                    </button>
                    """, unsafe_allow_html=True)
                
                with st.expander("🔧 View Raw Response"):
                    st.json(data)
                    
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.code(response.text)
            
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out. The LLM might be taking too long. Try again.")
    except requests.exceptions.ConnectionError:
        st.error("🔌 Cannot connect to backend. Make sure FastAPI is running on port 8000.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")

# --- Show last reply ---
elif st.session_state.last_reply:
    with st.container():
        st.success(f"✅ Previous reply (from {st.session_state.processing_time:.1f}s)")
        st.markdown("#### 📧 Email Draft")
        st.markdown(f"""
        <div class="reply-box">
            {st.session_state.last_reply.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)

# ========================================
# FOOTER
# ========================================
st.markdown("""
<div class="footer">
    🔒 All data is processed locally • No external API calls • Ollama + LangChain + ChromaDB
</div>
""", unsafe_allow_html=True)