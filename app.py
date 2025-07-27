import streamlit as st
import requests
import json

# ========== CONFIG ========== #
GEMINI_API_KEY = "AIzaSyDoOd2jew96NkKa-PHRyjzgHImXlGPaq7w"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
HEADERS = {
    "Content-Type": "application/json",
    "X-goog-api-key": GEMINI_API_KEY
}

# ========== SESSION STATE SETUP ========== #
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ========== SIDEBAR FILE UPLOAD ========== #
st.sidebar.title("📁 Upload Files")
uploaded_files = st.sidebar.file_uploader("Choose text or PDF files", accept_multiple_files=True, type=['txt', 'pdf'])

file_texts = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            import PyPDF2
            reader = PyPDF2.PdfReader(uploaded_file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        else:
            text = uploaded_file.read().decode("utf-8")
        file_texts.append(f"File: {uploaded_file.name}\n{text}")

# ========== CHAT UI ========== #
st.title("💬 Gemini 2.0 Flash Chat")
st.markdown("Ask a question or chat with Gemini. Uploaded files will be included in context.")

user_input = st.chat_input("Type your message...")
if user_input:
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "text": user_input})

    # Build context
    context_text = "\n\n".join(file_texts)
    full_prompt = f"{context_text}\n\nUser: {user_input}" if file_texts else user_input

    payload = {
        "contents": [
            {
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    response = requests.post(GEMINI_API_URL, headers=HEADERS, data=json.dumps(payload))

    if response.ok:
        gemini_reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        st.session_state.chat_history.append({"role": "gemini", "text": gemini_reply})
    else:
        st.error(f"Error: {response.status_code} - {response.text}")

# ========== DISPLAY CHAT ========== #
for entry in st.session_state.chat_history:
    with st.chat_message("🧑‍💻" if entry["role"] == "user" else "🤖"):
        st.markdown(entry["text"])
