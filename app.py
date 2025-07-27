import streamlit as st
import requests
import json
import io
from PIL import Image # For potential future image support, though not used in current text/pdf focus
import base64 # For potential future image support

# --- Configuration ---
# IMPORTANT: For production, store your API key securely using Streamlit Secrets.
# Create a .streamlit/secrets.toml file with:
GEMINI_API_KEY = "AIzaSyDoOd2jew96NkKa-PHRyjzgHImXlGPaq7w"


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
# Note: gemini-pro is generally sufficient for text-based chat.
# gemini-2.5-pro or gemini-1.5-flash might require different pricing/access.
# The original model `gemini-2.5-pro` might not be publicly available or might be deprecated for `generateContent`.
# Reverted to `gemini-pro` which is the standard model for this API endpoint.

HEADERS = {
    "Content-Type": "application/json",
    "X-goog-api-key": GEMINI_API_KEY
}

# --- Helper Functions ---

def read_pdf_file(file):
    """Reads text from a PDF file."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except ImportError:
        st.warning("`PyPDF2` library not found. Please install it to process PDF files: `pip install PyPDF2`")
        return None
    except Exception as e:
        st.error(f"Error reading PDF file {file.name}: {e}")
        return None

def read_text_file(file):
    """Reads text from a plain text file."""
    try:
        return file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading text file {file.name}: {e}")
        return None

def call_gemini_api(conversation_history, file_context_text=""):
    """
    Calls the Gemini API with the given conversation history and additional file context.
    conversation_history is a list of {"role": "user"|"gemini", "text": "..."}
    """
    # Gemini API expects roles as 'user' and 'model'
    gemini_formatted_history = []
    for entry in conversation_history:
        role = "user" if entry["role"] == "user" else "model"
        gemini_formatted_history.append({"role": role, "parts": [{"text": entry["text"]}]})

    # Append file context to the latest user message
    if file_context_text and gemini_formatted_history and gemini_formatted_history[-1]["role"] == "user":
        # Prepend context to the *last* user message
        full_user_prompt = f"**Context from Uploaded Files:**\n\n```\n{file_context_text}\n```\n\n**User Query:** {gemini_formatted_history[-1]['parts'][0]['text']}"
        gemini_formatted_history[-1]["parts"][0]["text"] = full_user_prompt
    elif file_context_text and not gemini_formatted_history: # Case where first message is sent with files
         full_user_prompt = f"**Context from Uploaded Files:**\n\n```\n{file_context_text}\n```\n\n**User Query:** {conversation_history[0]['text']}"
         gemini_formatted_history = [{"role": "user", "parts": [{"text": full_user_prompt}]}]


    payload = {
        "contents": gemini_formatted_history
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=HEADERS, data=json.dumps(payload))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"API HTTP Error: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("API Connection Error: Could not connect to the Gemini API. Check your internet connection or API URL.")
        return None
    except requests.exceptions.Timeout:
        st.error("API Timeout Error: The request to Gemini API timed out.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"An unexpected API error occurred: {e}")
        return None
    except KeyError:
        st.error("Invalid API response format. Missing 'candidates' or 'parts'.")
        st.json(response.json()) # Display full response for debugging
        return None

# --- Session State Setup ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # Stores {"role": "user"|"gemini", "text": "..."}

if "uploaded_file_contents" not in st.session_state:
    st.session_state.uploaded_file_contents = [] # Stores [{"name": "file.txt", "content": "..."}]

# --- Sidebar File Upload ---
st.sidebar.title("📁 Upload Files")
uploaded_files = st.sidebar.file_uploader(
    "Choose text or PDF files to include in context.",
    accept_multiple_files=True,
    type=['txt', 'pdf'],
    key="file_uploader"
)

# Process newly uploaded files
if uploaded_files:
    # Check if new files were uploaded that aren't already processed
    new_files_to_process = [
        f for f in uploaded_files
        if f.name not in [item['name'] for item in st.session_state.uploaded_file_contents]
    ]

    if new_files_to_process:
        st.sidebar.info("Processing uploaded files...")
        for uploaded_file in new_files_to_process:
            file_content = None
            if uploaded_file.type == "application/pdf":
                file_content = read_pdf_file(uploaded_file)
            elif uploaded_file.type == "text/plain":
                file_content = read_text_file(uploaded_file)

            if file_content:
                st.session_state.uploaded_file_contents.append({
                    "name": uploaded_file.name,
                    "content": file_content
                })
        st.sidebar.success("Files processed!")

# Display currently loaded files in sidebar
if st.session_state.uploaded_file_contents:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Loaded Files:")
    for i, file_data in enumerate(st.session_state.uploaded_file_contents):
        st.sidebar.markdown(f"- **{file_data['name']}**")
    st.sidebar.markdown(
        """<small>Files are included in the context of your queries.
        Be mindful of token limits with very large files or many files.</small>""",
        unsafe_allow_html=True
    )
    if st.sidebar.button("Clear Uploaded Files", key="clear_files_button"):
        st.session_state.uploaded_file_contents = []
        st.rerun() # Rerun to clear the uploader widget if needed, and update display

# --- Main Chat UI ---
st.title("💬 Gemini Flash Chat")
st.markdown("Ask a question or chat with Gemini. Uploaded files will be included in the context of your queries.")

# Clear chat button
if st.button("Clear Chat", key="clear_chat_button"):
    st.session_state.chat_history = []
    st.rerun()

# Display chat history
chat_display_container = st.container()
with chat_display_container:
    for entry in st.session_state.chat_history:
        with st.chat_message("🧑‍💻" if entry["role"] == "user" else "🤖"):
            st.markdown(entry["text"])

# User input and API call
user_input = st.chat_input("Type your message...", key="user_input_chat")

if user_input:
    # Add user message to chat history for display
    st.session_state.chat_history.append({"role": "user", "text": user_input})

    # Concatenate all file contents for the current query
    file_context_text = "\n\n".join([f"### {f['name']}\n{f['content']}" for f in st.session_state.uploaded_file_contents])

    with st.spinner("Thinking..."):
        # Call Gemini API with the full conversation history and the file context
        # The file_context_text will be prepended to the *last* user message in the payload
        response_json = call_gemini_api(st.session_state.chat_history, file_context_text)

        if response_json:
            try:
                gemini_reply = response_json["candidates"][0]["content"]["parts"][0]["text"]
                st.session_state.chat_history.append({"role": "gemini", "text": gemini_reply})
            except (KeyError, IndexError):
                st.error("Could not parse Gemini's response. Unexpected format.")
                st.json(response_json) # Show the full response for debugging
        # If response_json is None, an error message was already displayed by call_gemini_api

    # Rerun to update the chat display immediately after receiving response
    st.rerun()
