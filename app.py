import streamlit as st
import base64
import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import io
import pytesseract

# Import our custom modules
from pdf_utils import extract_text_and_tables_from_pdf, clean_text
from rag_utils import process_query

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(page_title="📊 TarkAI", layout="wide")

# --------- SESSION STATE INIT ---------
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'pdf_uploaded' not in st.session_state:
    st.session_state.pdf_uploaded = False
if 'pdf_content' not in st.session_state:
    st.session_state.pdf_content = ""
if 'pdf_tables' not in st.session_state:
    st.session_state.pdf_tables = []
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = ""
if 'document_summary' not in st.session_state:
    st.session_state.document_summary = ""

# --------- BACKGROUND IMAGE FUNCTION ---------
def add_bg_from_local(image_file):
    try:
        with open(image_file, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url(data:image/png;base64,{encoded_string});
                background-size: cover;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            .stApp::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(255, 255, 255, 0.6);
                z-index: -1;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.warning("Background image not found!")

# --------- THEME FUNCTIONS ---------
def apply_theme():
    if st.session_state.theme == 'dark':
        st.markdown("""
        <style>
        .main, .stApp { background-color: #121212; color: #FFFFFF !important; }
        .stTextInput > div > div > input { background-color: #2E2E2E; color: #FFFFFF; }
        .stButton > button { background-color: #0E86D4; color: white; }
        .stForm { background-color: #1E1E1E; padding: 20px; border-radius: 10px; }
        .element-container .stAlert.success { background-color: rgba(0, 168, 107, 0.2); }
        .user-message {
            background-color: #2E2E2E;
            color: white;
        }
        .assistant-message {
            background-color: #1E1E1E;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        add_bg_from_local("background1.jpg")

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

# --------- AUTH FUNCTIONS ---------
def authenticate(username, password):
    return username == "admin" and password == "admin"

def handle_form_submit():
    st.session_state.form_username = st.session_state.username_input
    st.session_state.form_password = st.session_state.password_input
    st.session_state.form_submitted = True

def logout():
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.chat_history = []
    st.session_state.pdf_uploaded = False
    st.session_state.pdf_content = ""
    st.session_state.pdf_tables = []
    st.session_state.processing_status = ""
    st.session_state.document_summary = ""
    st.session_state.pop('form_submitted', None)
    st.session_state.pop('form_username', None)
    st.session_state.pop('form_password', None)

# Update the chat handling function in app.py

def handle_chat_submit():
    if st.session_state.user_question.strip() and st.session_state.pdf_uploaded:
        question = st.session_state.user_question
        st.session_state.chat_history.append(("user", question))
        
        # Process the query using RAG system
        with st.spinner("Analyzing the report to answer your question..."):
            # Combine all content for processing
            combined_content = st.session_state.pdf_content
            
            if st.session_state.pdf_tables:
                tables_text = "\n\nTables:\n" + "\n".join(st.session_state.pdf_tables[:10])  # Limit to 10 tables
                combined_content += tables_text
            
            # Extract previous QA pairs for conversation memory
            previous_qa = []
            for i in range(0, len(st.session_state.chat_history)-1, 2):
                if i+1 < len(st.session_state.chat_history):
                    q = st.session_state.chat_history[i][1]
                    a = st.session_state.chat_history[i+1][1]
                    previous_qa.append((q, a))
            
            # Pass conversation history to the RAG processor
            response = process_query(combined_content, question, previous_qa)
            st.session_state.chat_history.append(("assistant", response))
        
        st.session_state.user_question = ""

# Function to process standalone image
def process_image(image_file):
    try:
        image = Image.open(image_file)
        
        # Resize very large images to prevent memory issues
        max_dimension = 2000
        if image.width > max_dimension or image.height > max_dimension:
            if image.width > image.height:
                new_width = max_dimension
                new_height = int(image.height * (max_dimension / image.width))
            else:
                new_height = max_dimension
                new_width = int(image.width * (max_dimension / image.height))
            image = image.resize((new_width, new_height))
        
        # Display image with reasonable size
        st.image(image, caption="Uploaded Image", width=600)
        
        # Extract text from image
        with st.spinner("Extracting text from image using OCR..."):
            img_text = pytesseract.image_to_string(image)
            cleaned_text = clean_text(img_text)
            
            if not cleaned_text.strip():
                st.warning("No text could be extracted from this image. It may not contain readable text or the quality might be too low.")
                return None
                
            # Preview the extracted text
            if len(cleaned_text) > 500:
                preview = cleaned_text[:500] + "..."
            else:
                preview = cleaned_text
                
            with st.expander("📝 Extracted Text Preview"):
                st.code(preview, language="text")
                
            return cleaned_text
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

# --------- STYLES ---------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
}
/*done*/
/* Main container adjustments */
.main .block-container {
    max-width: 95% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Logo container styling */
.logo-container {
    position: absolute;
    top: 20px;
    left: 20px;
    z-index: 1000;
}

/* Headings */
h1 {
    font-size: 72px !important;
    font-weight: 800;
    text-align: center;
}

h2 {
    font-size: 50px !important;
    font-weight: 700;
    text-align: center;
}

h3 {
    font-size: 35px !important;
    margin-top: 15px !important;
}

/* Login box */
div[data-testid="stForm"] {
    width: 85%;
    max-width: 1100px;
    height: 650px;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    margin-top: 90px;
    background-color: rgba(255, 255, 255, 0.5);
    padding: 60px 50px;
    border-radius: 25px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

/* Input labels */
div[data-testid="stTextInput"] label {
    font-size: 28px !important;
    font-weight: 600 !important;
    color: black !important;
}

/* Input fields */
input[type="text"], input[type="password"] {
    font-size: 24px !important;
    padding: 18px 14px !important;
    border-radius: 12px !important;
    border: 2px solid #ccc !important;
    background: rgba(255,255,255,0.7) !important;
    color: black !important;
    height: 60px !important;
}

/* Upload box */
section[data-testid="stFileUploader"] {
    width: 95% !important;
    margin: auto;
    padding: 25px;
    font-size: 26px;
}

/* Chat bubbles */
.user-message {
    background-color: #DCF8C6;
    padding: 15px;
    border-radius: 15px;
    margin: 8px 0;
    font-size: 22px;
}

.assistant-message {
    background-color: #FFF;
    padding: 15px;
    border-radius: 15px;
    margin: 8px 0;
    font-size: 22px;
}

/* Chat input */
div[data-testid="stTextInput"] > div > div > input {
    font-size: 22px !important;
}

/* Logout Button */
div.stButton > button {
    font-size: 26px !important;
    padding: 16px 35px !important;
    border-radius: 12px !important;
    background-color: #ff4b4b !important;
    color: white !important;
    font-weight: 600 !important;
}

div.stButton > button:hover {
    background-color: #cc0000 !important;
}

/* Success/Error messages */
div[data-testid="stAlert"] p {
    font-size: 24px !important;
}

/* Caption text */
.css-1vbkxwb {
    font-size: 18px !important;
}

/* Theme toggle button */
.theme-toggle {
    font-size: 26px !important;
    padding: 16px 35px !important;
    border-radius: 12px !important;
    background-color: #0E86D4 !important;
    color: white !important;
    font-weight: 600 !important;
}

/* Tables expander */
.stExpander {
    border-radius: 15px;
    margin: 20px 0;
}

/* Status messages */
.status-message {
    background-color: #f0f7ff;
    border-left: 5px solid #0078ff;
    padding: 10px 15px;
    margin: 15px 0;
    border-radius: 5px;
}

/* Document summary */
.document-summary {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    padding: 15px;
    border-radius: 8px;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# Apply theme based on current state
apply_theme()

# --------- MAIN APP STRUCTURE ---------
# Create a container for the logo that will appear at the top of every page
logo_container = st.container()
with logo_container:
    # Create columns - smaller ratio for the logo to make it bigger visually
    logo_col, content_col, theme_col = st.columns([1, 6, 1])
    with logo_col:
        try:
            # Try to load the logo with both extensions
            try:
                logo = Image.open("mindtree.png")
                st.image(logo, width=220)
            except FileNotFoundError:
                try:
                    logo = Image.open("mindtree.jpg")
                    st.image(logo, width=220)
                except FileNotFoundError:
                    st.error("Logo file not found. Please ensure 'mindtree.png' or 'mindtree.jpg' exists.")
        except Exception as e:
            st.error(f"Error loading logo: {e}")
    
    with theme_col:
        current_theme = "🌙 Dark" if st.session_state.theme == 'light' else "☀️ Light"
        st.button(current_theme, on_click=toggle_theme, key="theme_toggle", 
                  help="Toggle between light and dark mode")

# Continue with the rest of the app
if not st.session_state.authenticated:
    st.markdown("<h1>📊 TarkAI</h1>", unsafe_allow_html=True)
    st.markdown("<h2>🔐 Login:</h2>", unsafe_allow_html=True)

    # Wider login form with fewer empty columns on sides
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<label style='font-size:42px; font-weight:700;'>Username</label>",
                        unsafe_allow_html=True)
            st.text_input("", key="username_input")
            st.markdown("<label style='font-size:42px; font-weight:700;'>Password</label>",
                        unsafe_allow_html=True)
            st.text_input("", type="password", key="password_input")
            st.caption("Use 'admin' for both username and password")
            st.form_submit_button("Sign In", on_click=handle_form_submit)

    if 'form_submitted' in st.session_state and st.session_state.form_submitted:
        username = st.session_state.form_username
        password = st.session_state.form_password
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")
            st.session_state.form_submitted = False
else:
    # Adjusted column ratios to make content wider
    col1, col2, col3 = st.columns([1, 5, 1])
    with col3:
        st.button("Logout", on_click=logout)

    st.markdown(f"<h2>Welcome, <span style='color:#0078ff;'>{st.session_state.username}!</span></h2>",
                unsafe_allow_html=True)
    st.markdown("<h3 style='font-size:35px; margin-top:15px;'>Upload Annual Report (PDF) or Image</h3>", unsafe_allow_html=True)

    # Instructions and file size warning
    st.info("📋 Upload a PDF annual report or an image containing text to analyze. For PDFs, the system will process up to 30 pages. For optimal performance, consider using smaller documents or specific sections of large reports.")

    uploaded = st.file_uploader("", type=["pdf", "png", "jpg", "jpeg"])

    if uploaded:
        file_type = uploaded.type
        
        if file_type.startswith('application/pdf'):
            st.success("✅ PDF Uploaded!")
            
            # Check file size and warn if too large
            file_size_mb = uploaded.size / (1024 * 1024)
            if file_size_mb > 20:
                st.warning(f"⚠️ Large PDF detected ({file_size_mb:.1f} MB). Only the first 30 pages will be processed. Consider uploading a smaller file for better performance.")
            
            # Process the PDF
            with st.spinner("Processing PDF content... This may take a moment for large documents."):
                st.session_state.processing_status = "Processing PDF content..."
                
                try:
                    pdf_text, pdf_tables = extract_text_and_tables_from_pdf(uploaded)
                    
                    if pdf_text:
                        st.session_state.pdf_content = pdf_text
                        st.session_state.pdf_tables = pdf_tables
                        st.session_state.pdf_uploaded = True
                        
                        # Generate a brief summary of the content for the user
                        text_length = len(pdf_text)
                        table_count = len(pdf_tables)
                        
                        st.session_state.document_summary = f"""
                        📄 **Document processed successfully!**
                        - Text extracted: {text_length} characters
                        - Tables detected: {table_count}
                        - Processing status: Complete
                        """
                        
                        if pdf_tables:
                            with st.expander("📋 Detected Tables (Sample)"):
                                for idx, table in enumerate(pdf_tables[:5]):  # Show only first 5 tables
                                    st.markdown(f"**Table {idx+1}:**")
                                    st.code(table[:1000] if len(table) > 1000 else table, language="text")
                                    if idx >= 4 and len(pdf_tables) > 5:
                                        st.info(f"{len(pdf_tables) - 5} more tables detected but not shown.")
                                        break
                    else:
                        st.error("No text could be extracted from this PDF. The document might be scanned or protected.")
                
                except Exception as e:
                    st.error(f"Error processing PDF: {str(e)}")
                    st.session_state.pdf_uploaded = False
        
        elif file_type.startswith('image/'):
            # Process the image with OCR
            extracted_text = process_image(uploaded)
            
            if extracted_text:
                st.session_state.pdf_content = extracted_text
                st.session_state.pdf_uploaded = True
                
                # Generate a brief summary
                st.session_state.document_summary = f"""
                🖼️ **Image processed successfully!**
                - Text extracted: {len(extracted_text)} characters
                - Processing status: Complete
                """
    
    # Display document summary if available
if st.session_state.document_summary:
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.7); 
                border-radius: 10px; 
                padding: 15px; 
                margin: 15px 0; 
                border-left: 5px solid #0078ff;">
        <h4 style="color: #0078ff; margin-top: 0; margin-bottom: 10px; font-size: 20px;">
            📄 Document processed successfully!
        </h4>
        <ul style="list-style-type: none; padding-left: 0; margin-bottom: 0;">
            <li style="padding: 5px 0; font-size: 16px;">
                <strong>Text extracted:</strong> {text_length} characters
            </li>
            <li style="padding: 5px 0; font-size: 16px;">
                <strong>Tables detected:</strong> {table_count}
            </li>
            <li style="padding: 5px 0; font-size: 16px;">
                <strong>Processing status:</strong> Complete
            </li>
        </ul>
    </div>
    """.format(
        text_length=len(st.session_state.pdf_content),
        table_count=len(st.session_state.pdf_tables)
    ), unsafe_allow_html=True)
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for role, message in st.session_state.chat_history:
            if role == "user":
                st.markdown(
                    f'<div class="user-message">{message}</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="assistant-message">{message}</div>',
                    unsafe_allow_html=True)

    # Add small spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Wider chat input with 6:1 ratio
    col1, col2 = st.columns([6, 1])
    with col1:
        st.text_input("Ask a question about the report...", key="user_question", 
                     disabled=not st.session_state.pdf_uploaded)
    with col2:
        st.button("Send", on_click=handle_chat_submit, disabled=not st.session_state.pdf_uploaded)
        
    if not st.session_state.pdf_uploaded:
        st.info("Please upload a PDF or image to start asking questions.")
    
    # Add example questions if document is uploaded
    if st.session_state.pdf_uploaded and not st.session_state.chat_history:
        st.markdown("### Example questions you can ask:")
        example_questions = [
            "What are the key financial highlights?",
            "What is the company's revenue growth?",
            "Who are the board members mentioned in this report?",
            "What are the main risks mentioned in this document?",
            "Summarize the business outlook section."
        ]
        
        for q in example_questions:
            if st.button(q, key=f"example_{q}"):
                st.session_state.user_question = q
                handle_chat_submit()
                st.rerun()