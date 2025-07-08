
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
import io
from langchain.text_splitter import  CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from htmlTemplate import css,bot_template,user_template

def get_document_text(docs):
    text = ""
    for doc in docs:
        try:
            if doc.name.endswith('.pdf'):
                pdf_bytes = io.BytesIO(doc.read())
                pdf_reader = PdfReader(pdf_bytes, strict=False)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            elif doc.name.endswith(('.docx', '.doc')):
                doc_bytes = io.BytesIO(doc.read())
                document = Document(doc_bytes)
                for paragraph in document.paragraphs:
                    text += paragraph.text + "\n"
        except Exception as e:
            st.warning(f"Could not read {doc.name}: {str(e)}")
            continue
    return text
def get_text_chunks(text):
    text_spliter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunk = text_spliter.split_text(text)
    return chunk

def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    #embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
    vectorstore = FAISS.from_texts(texts=text_chunks,embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()
    # llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":512})

    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )
    return conversation_chain


def handle_userinput(user_question):
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            st.write(user_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)
        else:
            st.write(bot_template.replace(
                "{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")

    st.write(css,unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None

    st.header("Empower AI:")
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
        handle_userinput(user_question)

    with st.sidebar:
        st.subheader("Your documents:")
        pdf_docs = st.file_uploader("Upload your documents here and click on 'Process'", accept_multiple_files=True, type=['pdf', 'docx', 'doc'])
        if st.button("Process"):
            with st.spinner("Processing"):
                # get the document text
                raw_text = get_document_text(pdf_docs)

                # get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # create vector store
                vectorstore = get_vectorstore(text_chunks)

                #create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)




if __name__ == '__main__':
    main()