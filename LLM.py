import streamlit as st
import assemblyai as aai
import tempfile
import boto3
from botocore.exceptions import NoCredentialsError
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from langchain.schema import SystemMessage, HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings

load_dotenv(os.path.join(r'C:/Users/19452/Desktop/LLM/VoiceIQ/.env', '.env'))

s3=boto3.client('s3')
open_ai_key= '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' 
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
# AssemblyAI API key setup
aai.settings.api_key = os.getenv('AssemblyAI_API')  
llm = ChatOpenAI(api_key="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")

# AWS S3 setup
s3 = boto3.client('s3')
BUCKET_NAME = 'audiofilellm'  
# path = '/Users/maverick1997/Downloads/01-ted-talk.mp3'

# file='01-ted-talk.mp3'
# s3_bucket_path = "audiofile/"+file

def upload_file_to_s3(file,file_name):
    try:
        s3_bucket_path = "audiofile/"+file
        response= s3.upload_file(file_name,BUCKET_NAME,s3_bucket_path)
        print(response)
        # s3.meta.client.upload_file(Filename='/Users/maverick1997/Downloads/01-ted-talk.mp3', Bucket='audiofilellm',Key='01-ted-talk.mp3')
        # response =  f"s3://{BUCKET_NAME}/audiofile/{file_name}"
        # print("response:", response)
    except NoCredentialsError:
        st.error("Upload failed: Credentials not available")
        return None

def list_files_in_s3():
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            return [file['Key'] for file in response['Contents']]
        else:
            return []
    except NoCredentialsError:
        st.error("Failed to list files: Credentials not available")
        return []


def get_file_from_s3(file_name):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            s3.download_fileobj(BUCKET_NAME, file_name, temp_file)
            return temp_file.name
    except NoCredentialsError:
        st.error("Fetch failed: Credentials not available")
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

class PageContentDocument:
    def __init__(self, content, metadata=None):
        self.page_content = content
        self.metadata = metadata if metadata is not None else {}

def split_Data(docs):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len
    )
    docs_chunks = text_splitter.split_documents(docs)
    return docs_chunks


def create_embeddings():
    return OpenAIEmbeddings(deployment="text-embedding-ada-002", openai_api_key= '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')

def push_to_pinecone(pinecone_api_key, pinecone_environment, pinecone_index_name, embeddings, docs):
    Pinecone.apikey = pinecone_api_key
    Pinecone.environment = pinecone_environment
    index = Pinecone.from_documents(docs, embeddings, index_name=pinecone_index_name)
    return index



def get_chatbot_response(transcript, user_query):
    embeddings = create_embeddings()
    wrapped_transcript = PageContentDocument(transcript)
    transcript_chunks = split_Data([wrapped_transcript])
    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    pinecone_index = push_to_pinecone(pinecone_api_key, "us-central1-gcp-starter", "transcript", embeddings, transcript_chunks)


    llm = ChatOpenAI(model='gpt-3.5-turbo', temperature=1, openai_api_key= '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')
    # pinecone_index.filter{"text": ""}
    retriever = pinecone_index.as_retriever(search_type='similarity', search_kwargs={'k': 3})
    chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    
    answer = chain.run(user_query)
    return answer

# Streamlit interface
def main():
    st.title("Audio Transcription and Langchain Chatbot")

    if 'transcript' not in st.session_state:
        st.session_state.transcript = ""

    # Audio upload and save to S3
    audio_file = st.file_uploader("Upload Audio", type=['wav', 'mp3', 'mp4', 'ogg', 'm4a'])
    if audio_file is not None:
        file_name = audio_file.name
        filename = 'C:\\Users\\19452\\Downloads\\'+file_name
        s3_path = upload_file_to_s3(file_name, filename)
        if s3_path:
            st.success(f"File uploaded to {s3_path}")
            st.session_state.s3_file_name = file_name  # Save the file name in session state

    files_in_s3 = list_files_in_s3()
    selected_file = st.selectbox("Select a file for transcription", files_in_s3)

    # Transcribe button
    if st.button("Transcribe Selected File"):
        if selected_file:
            local_file_path = get_file_from_s3(selected_file)
            if local_file_path:
                st.session_state.transcript = transcribe_audio(local_file_path)
                st.success("File transcribed successfully")
        else:
            st.error("No file selected")

    # Display transcription
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