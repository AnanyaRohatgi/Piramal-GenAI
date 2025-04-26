import os
import glob
import pytesseract
from pdf2image import convert_from_path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
import re

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = "OPEN_API_KEY"

app = Flask(__name__)
CORS(app)

def ocr_from_pdf(pdf_path):
    """Extract text from images in a PDF using OCR."""
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"OCR error for {pdf_path}: {e}")
        return ""

def load_docs():
    """Load and process all PDFs in the 'newdata' folder."""
    documents = []
    pdf_files = glob.glob("newdata/*.pdf")
    for pdf_path in pdf_files:
        try:
            # Try to load text from PDF using PyPDFLoader
            loader = PyPDFLoader(pdf_path)
            loaded_documents = loader.load()
            if not loaded_documents:
                # If no text extracted, use OCR as fallback
                doc_text = ocr_from_pdf(pdf_path)
                if doc_text:
                    documents.append(Document(page_content=doc_text, metadata={'source': pdf_path}))
            else:
                documents.extend(loaded_documents)
        except Exception as e:
            print(f"Error loading {pdf_path}: {e}")
            continue

    # Split documents into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)

    # Create embeddings and vectorstore
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local("faiss_index")
    return vectorstore

# Load documents and initialize vectorstore at startup
vectorstore = load_docs()
chat_history = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    global chat_history
    if vectorstore is None:
        return jsonify({"error": "No documents loaded.", "success": False}), 500

    data = request.json
    query = data.get('question')
    if not query:
        return jsonify({"error": "No question provided"}), 400

    try:
        llm = ChatOpenAI(temperature=0.5)
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            return_source_documents=True
        )
        result = qa({"question": query, "chat_history": chat_history})
        chat_history.append((query, result["answer"]))

        # Format the answer before sending it back
        formatted_answer = format_response(result["answer"])

        return jsonify({"answer": formatted_answer, "success": True})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}", "success": False}), 500

def format_response(response):
    """
    Format the response to break each point into a new line.
    For example:
    '1. Point 1. 2. Point 2.' -> 
    '1. Point 1.<br>2. Point 2.'
    """
    # Remove **bold markdown from the response
    response = re.sub(r'\*\*(.*?)\*\*', r'\1', response)  # Remove the **bold markdown**

    # Replace each numbered item with a new line break
    formatted = re.sub(r'(\d+\.\s*)', r'<br>\1', response)  # Break each point into a new line
    return formatted

if __name__ == "__main__":
    app.run(debug=True, port=5000)