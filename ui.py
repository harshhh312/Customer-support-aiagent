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

# --- Custom CSS for a premium look ---
st.markdown("""
    <style>
    /* Main container */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Card-like containers */
    .card {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }
    
    /* Reply box with gradient border */
    .reply-box {
        background-color: var(--secondary-background-color);
        border-left: 5px solid #4CAF50;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-top: 1rem;
        white-space: pre-wrap;
        font-family: 'Segoe UI', -apple-system, sans-serif;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    .reply-box:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-online {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .badge-offline {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .badge-judge-on {
        background-color: #cce5ff;
        color: #004085;
        border: 1px solid #b8daff;
    }
    .badge-judge-off {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffc107;
    }
    
    /* Quick example buttons */
    .example-btn {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 0.4rem 1rem;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
        margin: 0.2rem;
        display: inline-block;
        color: var(--text-color);
    }
    .example-btn:hover {
        background-color: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
    }
    
    /* Metrics */
    .metric-box {
        background-color: var(--secondary-background-color);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        text-align: center;
        border: 1px solid var(--border-color);
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary-color);
    }
    .metric-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--text-color-secondary);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: var(--text-color-secondary);
        font-size: 0.8rem;
        border-top: 1px solid var(--border-color);
        margin-top: 2rem;
    }
    
    /* Stepper dots */
    .step-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .step-active {
        background-color: #4CAF50;
        animation: pulse 1.2s infinite;
    }
    .step-done {
        background-color: #4CAF50;
    }
    .step-waiting {
        background-color: #ccc;
    }
    @keyframes pulse {
        0% { opacity: 0.5; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
        100% { opacity: 0.5; transform: scale(1); }
    }
    </style>
""", unsafe_allow_html=True)

# --- Initialize session state ---
if "history" not in st.session_state:
    st.session_state.history = []
if "last_reply" not in st.session_state:
    st.session_state.last_reply = None
if "processing_time" not in st.session_state:
    st.session_state.processing_time = None

# --- Header ---
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.image("https://img.icons8.com/fluency/96/000000/artificial-intelligence.png", width=70)
with col2:
    st.title("🧠 Abstergo Support AI")
    st.caption("Enterprise Customer Support Agent • Self-Correcting RAG • LLM-as-Judge")
with col3:
    st.caption(f"🕒 {datetime.now().strftime('%H:%M')}")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ System Status")
    
    # Backend health check
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
    st.header("🧑‍⚖️ LLM-as-Judge")
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

    # --- Quick Examples ---
    st.divider()
    st.header("⚡ Quick Examples")
    st.caption("Click to auto-fill the query:")
    
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
    
    # --- Conversation History ---
    st.divider()
    st.header("📜 History")
    if st.session_state.history:
        for i, (q, _) in enumerate(st.session_state.history[-5:]):
            st.caption(f"{i+1}. {q[:60]}...")
        if len(st.session_state.history) > 5:
            st.caption(f"... and {len(st.session_state.history) - 5} more")
    else:
        st.caption("No conversations yet.")
    
    # --- Model Info ---
    st.divider()
    st.caption("🤖 **Model:** Llama 3 (local)")
    st.caption("📦 **Vector DB:** Chroma (Hybrid RAG)")
    st.caption("🔗 **Memory:** Semantic Vector + SQLite")

# --- Main Query Interface ---
st.subheader("💬 Submit a Support Ticket")

# If there's an example query, auto-fill it
example_query = st.session_state.get("example_query", "")
if example_query:
    default_question = example_query
    st.session_state.example_query = ""  # Clear after use
else:
    default_question = ""

with st.form("support_form", clear_on_submit=False):
    col_email, col_name = st.columns(2)
    with col_email:
        email = st.text_input(
            "📧 Customer Email",
            value="test@example.com",
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
    
    col_submit1, col_submit2 = st.columns([3, 1])
    with col_submit1:
        submitted = st.form_submit_button("🚀 Generate Reply", use_container_width=True)
    with col_submit2:
        clear = st.form_submit_button("🗑️ Clear", use_container_width=True)
        if clear:
            st.session_state.last_reply = None
            st.rerun()

# --- Process the query ---
if submitted:
    if not question.strip():
        st.warning("⚠️ Please describe your issue.")
        st.stop()
    
    if not email.strip():
        st.warning("⚠️ Please enter a valid email.")
        st.stop()
    
    # --- Step-by-step progress ---
    status_placeholder = st.empty()
    reply_container = st.container()
    
    with status_placeholder.container():
        st.markdown("### 🚀 Processing your request...")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown('<span class="step-dot step-active"></span> **RAG Retrieval**', unsafe_allow_html=True)
        with col_s2:
            st.markdown('<span class="step-dot step-waiting"></span> **LLM Generation**', unsafe_allow_html=True)
        with col_s3:
            st.markdown('<span class="step-dot step-waiting"></span> **Judge Review**', unsafe_allow_html=True)
    
    start_time = time.time()
    
    try:
        payload = {
            "email": email.strip(),
            "message": question.strip(),
        }
        
        # Update step 1 -> done
        with status_placeholder.container():
            st.markdown("### 🚀 Processing your request...")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown('<span class="step-dot step-done"></span> ✅ **RAG Retrieval**', unsafe_allow_html=True)
            with col_s2:
                st.markdown('<span class="step-dot step-active"></span> **LLM Generation**', unsafe_allow_html=True)
            with col_s3:
                st.markdown('<span class="step-dot step-waiting"></span> **Judge Review**', unsafe_allow_html=True)
        
        response = requests.post(
            f"{API_URL}/chat",
            json=payload,
            timeout=120,
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            reply = data.get("reply", "No reply generated.")
            
            # Update step 2 & 3 -> done
            with status_placeholder.container():
                st.markdown("### ✅ Request Complete!")
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.markdown('<span class="step-dot step-done"></span> ✅ **RAG Retrieval**', unsafe_allow_html=True)
                with col_s2:
                    st.markdown('<span class="step-dot step-done"></span> ✅ **LLM Generation**', unsafe_allow_html=True)
                with col_s3:
                    judge_status = "✅ **Judge Review**" if "judge" in reply.lower() or "draft" in reply.lower() else "⏭️ **Judge Skipped**"
                    st.markdown(f'<span class="step-dot step-done"></span> {judge_status}', unsafe_allow_html=True)
            
            # Store in history
            st.session_state.history.append((question, reply[:100] + "..."))
            st.session_state.last_reply = reply
            st.session_state.processing_time = elapsed
            
            # --- Display Reply ---
            with reply_container:
                st.success(f"✅ Reply generated in {elapsed:.2f} seconds!")
                
                # Metrics row
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
                
                st.subheader("📧 Email Draft")
                
                # Reply box
                st.markdown(f"""
                <div class="reply-box">
                    {reply.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons
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
                    # Copy to clipboard using JavaScript
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText(`{reply.replace('`', '\\`')}`)" 
                                style="width:100%; padding:0.5rem; border-radius:8px; border:1px solid #ccc; 
                                       background-color:var(--secondary-background-color); cursor:pointer;">
                        📋 Copy
                    </button>
                    """, unsafe_allow_html=True)
                
                # Raw JSON toggle
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

# --- Show last reply if it exists (no new submission) ---
elif st.session_state.last_reply:
    with st.container():
        st.success(f"✅ Previous reply (from {st.session_state.processing_time:.1f}s)")
        st.subheader("📧 Email Draft")
        st.markdown(f"""
        <div class="reply-box">
            {st.session_state.last_reply.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div class="footer">
    🔒 All data is processed locally • No external API calls • Ollama + LangChain + ChromaDB
</div>
""", unsafe_allow_html=True)