import streamlit as st
import assemblyai as aai
import tempfile
import boto3
from botocore.exceptions import NoCredentialsError
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

aws_access_key_id = 'AKIAS7DOCR7X3RL6UWY3'
aws_secret_access_key = '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'

s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

# AssemblyAI API key setup
aai.settings.api_key = "e87c6067b9d345c08166ce56e842f0b6"  
llm = ChatOpenAI(api_key="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")

# AWS S3 setup
s3 = boto3.client('s3')
BUCKET_NAME = 'audiofilellm'  

def upload_file_to_s3(file, file_name):
    try:
        s3.upload_fileobj(file, BUCKET_NAME, file_name)
        return f"s3://{BUCKET_NAME}/{file_name}"
    except NoCredentialsError:
        st.error("Credentials not available")
        return None

def get_file_from_s3(file_name):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            s3.download_fileobj(BUCKET_NAME, file_name, temp_file)
            return temp_file.name
    except NoCredentialsError:
        st.error("Credentials not available")
        return None

def transcribe_audio(file_path):
    # Create a new Transcriber
    transcriber = aai.Transcriber()

    # Transcribe using AssemblyAI
    transcript = transcriber.transcribe(file_path)

    # Check for errors
    if transcript.error:
        st.error(f"Transcription error: {transcript.error}")
        return ""

    return transcript.text

def get_chatbot_response(transcript, user_query, chunk_size=800):
    # Split the transcript into chunks
    transcript_chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
    
    # Use only the last N chunks for context
    relevant_context = "\n".join(transcript_chunks[-10:])  # Adjust the number of chunks as needed

    messages = [
        SystemMessage(content=f'You will answer questions based on the following transcript - "{relevant_context}"'),
        HumanMessage(content=user_query)
    ]
    response = llm.invoke(messages)
    return response.content

# Streamlit interface
def main():
    st.title("Audio Transcription and Langchain Chatbot")

    if 'transcript' not in st.session_state:
        st.session_state.transcript = ""

    # Audio upload and save to S3
    audio_file = st.file_uploader("Upload Audio", type=['wav', 'mp3', 'mp4', 'ogg', 'm4a'])
    if audio_file is not None:
        file_name = audio_file.name
        s3_path = upload_file_to_s3(audio_file, file_name)
        if s3_path:
            st.success(f"File uploaded to {s3_path}")
            st.session_state.s3_file_name = file_name  # Save the file name in session state

    # Option to transcribe from S3
    if st.button("Transcribe from S3"):
        if 's3_file_name' in st.session_state and st.session_state.s3_file_name:
            local_file_path = get_file_from_s3(st.session_state.s3_file_name)
            if local_file_path:
                st.session_state.transcript = transcribe_audio(local_file_path)
        else:
            st.error("No file selected")

    if st.session_state.transcript:
        st.write("Transcript:")
        st.text_area("Transcript Output", st.session_state.transcript, height=250)

    # Chatbot interaction
    user_query = st.text_input("Ask a question based on the transcript:")
    if user_query:
        with st.spinner('Generating response...'):
            response = get_chatbot_response(st.session_state.transcript, user_query)
            st.write("Chatbot Response:")
            st.write(response)

if __name__ == '__main__':
    main()








# import streamlit as st
# import assemblyai as aai
# import tempfile
# from langchain_openai import ChatOpenAI
# from langchain.schema import SystemMessage, HumanMessage

# # AssemblyAI API key setup
# aai.settings.api_key = "e87c6067b9d345c08166ce56e842f0b6"  
# llm = ChatOpenAI(api_key = "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")


# def transcribe_audio(uploaded_file):
#     # Save the uploaded file to a temporary file
#     with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
#         temp_file.write(uploaded_file.getvalue())
#         temp_file_path = temp_file.name

#     # Create a new Transcriber
#     transcriber = aai.Transcriber()

#     # Transcribe using AssemblyAI
#     transcript = transcriber.transcribe(temp_file_path)

#     # Check for errors
#     if transcript.error:
#         st.error(f"Transcription error: {transcript.error}")
#         return ""

#     return transcript.text

# def get_chatbot_response(transcript, user_query, chunk_size=800):
#     # Split the transcript into chunks
#     transcript_chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size)]
    
#     # Use only the last N chunks for context
#     relevant_context = "\n".join(transcript_chunks[-10:])  # Adjust the number of chunks as needed

#     messages = [
#         SystemMessage(content=f'You will answer questions based on the following transcript - "{relevant_context}"'),
#         HumanMessage(content=user_query)
#     ]
#     response = llm.invoke(messages)
#     return response.content

# # def get_chatbot_response(transcript, user_query):
# #     messages = [
# #         SystemMessage(content=f'You analyze this transcript and answer any questions based on or about it - "{transcript}"'),
# #         HumanMessage(content=user_query)
# #     ]
# #     response = llm.invoke(messages)
# #     return response.content

# # Streamlit interface
# def main():
#     st.title("Audio Transcription and Langchain Chatbot")

#     if 'transcript' not in st.session_state:
#         st.session_state.transcript = ""

#     # Audio upload
#     audio_file = st.file_uploader("Upload Audio", type=['wav', 'mp3', 'mp4', 'ogg', 'm4a'])

#     if audio_file is not None and not st.session_state.transcript:
#         with st.spinner('Transcribing...'):
#             st.session_state.transcript = transcribe_audio(audio_file)
    
#     if st.session_state.transcript:
#         st.write("Transcript:")
#         st.text_area("Transcript Output", st.session_state.transcript, height=250)

#     # Chatbot interaction
#     user_query = st.text_input("Ask a question based on the transcript:")
#     if user_query:
#         with st.spinner('Generating response...'):
#             response = get_chatbot_response(st.session_state.transcript, user_query)
#             st.write("Chatbot Response:")
#             st.write(response)

# if __name__ == '__main__':
#     main()




# def main():
#     st.title("Audio Transcription and Langchain Chatbot")

#     # Audio upload
#     audio_file = st.file_uploader("Upload Audio", type=['wav', 'mp3', 'mp4', 'ogg', 'm4a'])

#     if audio_file is not None:
#         with st.spinner('Transcribing...'):
#             transcript = transcribe_audio(audio_file)
#             st.write("Transcript:")
#             st.text_area("Transcript Output", transcript, height=250)

#         # Chatbot interaction
#         user_query = st.text_input("Ask a question based on the transcript:")
#         if user_query:
#             with st.spinner('Generating response...'):
#                 response = get_chatbot_response(transcript, user_query)
#                 st.write("Chatbot Response:")
#                 st.write(response)

# if __name__ == '__main__':
#     main()