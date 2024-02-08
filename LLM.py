
import streamlit as st
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import requests
import snowflake.connector
import os
from dotenv import load_dotenv
load_dotenv(os.path.join('C:/Users/19452/Desktop/LLM','.env'))
                         

# Load pre-trained GPT-2 model and tokenizer
model_name = 'gpt2-medium'
model = GPT2LMHeadModel.from_pretrained(model_name)
tokenizer = GPT2Tokenizer.from_pretrained(model_name)

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
        return response.json().get('text', '')
    else:
        st.error("Failed to transcribe audio")
        st.write(f"Error: {response.text}")
        return None

def generate_answer(transcript, question):
    input_text = transcript + " " + question
    input_ids = tokenizer.encode(input_text, return_tensors='pt', truncation=True, max_length=1024)
    
    output = model.generate(input_ids, max_length=1024, num_return_sequences=1, no_repeat_ngram_size=2)
    answer = tokenizer.decode(output[0], skip_special_tokens=True)
    return answer

def main():
    st.title("Audio File Transcription and Chatbot Interaction")

    uploaded_file = st.file_uploader("Upload an audio file", type=['wav', 'mp3', 'ogg'])
    transcript = ""

    if uploaded_file is not None:
        transcript = transcribe_audio(uploaded_file, os.getenv('APIKEY'))
        st.text_area("Transcript", value=transcript, height=150)

        if st.button('Save Transcript'):
            save_transcript_to_snowflake(transcript)
            st.success('Transcript saved successfully to Snowflake.')

    st.subheader("Chat with the GPT-2 bot based on the transcript")
    user_input = st.text_input("Your question:")

    if user_input and transcript:
        answer = generate_answer(transcript, user_input)
        st.text_area("GPT-2 Response", value=answer, height=100)

if __name__ == "__main__":
    main()


