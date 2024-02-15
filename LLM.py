import streamlit as st
import os
from dotenv import load_dotenv
import requests
import snowflake.connector
from langchain.llms import OpenAI  # Import LangChain

# Load environment variables
load_dotenv(os.path.join('C:/Users/19452/Desktop/LLM', '.env'))

# Initialize LangChain with GPT-3
model_kwargs = {'api_key': os.getenv('OPENAI_API_KEY')}
llm = OpenAI(model_kwargs=model_kwargs)

# Snowflake connection details
snowflake_account = os.getenv('snowflake_account')
snowflake_user = os.getenv('snowflake_user')
snowflake_password = os.getenv('snowflake_password')
snowflake_warehouse = 'compute_wh'
snowflake_database = 'transcripts'
snowflake_schema = 'public'
snowflake_table = 'transcripts'

def save_transcript_to_snowflake(transcript):
    conn = snowflake.connector.connect(
        user=snowflake_user,
        password=snowflake_password,
        account=snowflake_account,
        warehouse=snowflake_warehouse,
        database=snowflake_database,
        schema=snowflake_schema
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO {snowflake_table} (transcript) VALUES (%s)",
            (transcript,)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def transcribe_audio(uploaded_file, api_key):
    url = "https://transcribe.whisperapi.com"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": uploaded_file.getvalue()}

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        transcription = response.json().get('text', '')
        if transcription:
            return transcription
        else:
            st.error("Transcription service returned an empty response.")
            return None
    else:
        st.error("Failed to transcribe audio")
        st.write(f"Error: {response.text}")
        return None

def generate_answer_with_langchain(transcript, question):
    response = llm.complete(prompt=f"{transcript}\n\nQuestion: {question}\nAnswer:", max_tokens=1024)
    return response.get('choices')[0].get('text').strip()

def main():
    st.title("Audio File Transcription and Chatbot Interaction")

    uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'ogg'])
    transcript = ""

    if uploaded_file is not None:
        transcript = transcribe_audio(uploaded_file, os.getenv('APIKEY'))

        if transcript:
            st.text_area("Transcript", value=transcript, height=150)
        else:
            st.write("No transcript received or it's empty.")  # Debugging

        if st.button('Save Transcript'):
            save_transcript_to_snowflake(transcript)
            st.success('Transcript saved successfully to Snowflake.')

    st.subheader("Chat with the AI based on the transcript")
    user_input = st.text_input("Your question:")

    if user_input and transcript:
        answer = generate_answer_with_langchain(transcript, user_input)
        st.text_area("AI Response", value=answer, height=100)

if __name__ == "__main__":
    main()
