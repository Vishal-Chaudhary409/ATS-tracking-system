from dotenv import load_dotenv
import base64
import streamlit as st
import os
import io
import json
from PIL import Image
import pdf2image
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import time

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

cred = credentials.Certificate("firebase_config.json")

# Initialize Firebase
if not firebase_admin._apps:
    #cred = credentials.Certificate("firebase_config.json")  # Load Firebase credentials
    firebase_admin.initialize_app(cred)

db = firestore.client()  # Initialize Firestore database


# Function to get Gemini response
def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input_text, pdf_content[0], prompt])
    return response.text


# Convert uploaded PDF to image
def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        images = pdf2image.convert_from_bytes(uploaded_file.read())
        first_page = images[0]

        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        pdf_parts = [
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img_byte_arr).decode()
            }
        ]
        return pdf_parts
    else:
        raise FileNotFoundError("No file uploaded")


# Streamlit App Setup
st.set_page_config(page_title="ATS Resume Expert")
st.header("ATS Tracking System")

# User authentication session
if "user" not in st.session_state:
    st.session_state.user = None


# Sign up function
def sign_up(email, password):
    try:
        user = auth.create_user(email=email, password=password)
        st.success("Account created successfully! Please log in.")
    except Exception as e:
        st.error(f"Error creating account: {str(e)}")


# Login function
def login(email, password):
    try:
        user = auth.get_user_by_email(email)
        st.session_state.user = {"email": email, "uid": user.uid}
        st.success("Logged in successfully!")
    except Exception as e:
        st.error("Invalid email or password")


# Logout function
def logout():
    st.session_state.user = None
    st.success("Logged out successfully!")


# User Authentication UI
if st.session_state.user is None:
    choice = st.selectbox("Login or Sign Up", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.button("Sign Up"):
            sign_up(email, password)
    else:
        if st.button("Login"):
            login(email, password)

    st.stop()  # Stop execution until login/signup is complete

# Display user info
st.sidebar.write(f"Logged in as: {st.session_state.user['email']}")
if st.sidebar.button("Logout"):
    logout()
    st.stop()

# Main Application Logic
input_text = st.text_area("Job Description: ", key="input")
uploaded_file = st.file_uploader("Upload your resume (PDF)...", type=["pdf"])

if uploaded_file is not None:
    st.write("✅ PDF Uploaded Successfully")

submit1 = st.button("Tell Me About the Resume")
submit3 = st.button("Percentage Match")

input_prompt1 = """
You are an experienced Technical Human Resource Manager. Your task is to review the provided resume against the job description. 
Please share your professional evaluation on whether the candidate's profile aligns with the role.
Highlight the strengths and weaknesses of the applicant in relation to the specified job requirements.
"""

input_prompt3 = """
You are a skilled ATS (Applicant Tracking System) scanner with a deep understanding of data science and ATS functionality.
Your task is to evaluate the resume against the provided job description. Give me the percentage of match if the resume matches
the job description. First, output the percentage, then keywords missing, and finally, provide final thoughts.
"""

# Resume Analysis
if submit1 or submit3:
    if uploaded_file is not None:
        pdf_content = input_pdf_setup(uploaded_file)
        prompt = input_prompt1 if submit1 else input_prompt3
        response = get_gemini_response(input_text, pdf_content, prompt)

        st.subheader("The Response:")
        st.write(response)

        # Save to Firestore
        user_uid = st.session_state.user["uid"]
        db.collection("users").document(user_uid).collection("resume_analysis").add({
            "job_description": input_text,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        st.success("Analysis saved successfully!")

    else:
        st.error("Please upload the resume.")
