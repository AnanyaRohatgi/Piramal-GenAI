from flask import Flask, render_template, request, jsonify
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAI
import os
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, RetrievalQA
import re
import html

app = Flask(__name__)

# Initialize OpenAI API
os.environ["OPENAI_API_KEY"] = "sk-proj-IsnzuMuKUhjleGiwjtm0T3BlbkFJWT87k5UDLmryR0Oaa2eN"

# Initialize document processing components
embeddings = OpenAIEmbeddings()

def load_documents():
    try:
        # Check if we have a saved vector store
        if os.path.exists("faiss_index"):
            print("Loading existing vector store from disk...")
            return FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        # Use DirectoryLoader with PyPDFLoader for PDF files
        loader = DirectoryLoader("data", glob="*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        
        if not documents:
            print("Warning: No PDF documents found in the data directory")
            return None
            
        print(f"Successfully loaded {len(documents)} PDF documents")
        
        # Split documents into chunks - using RecursiveCharacterTextSplitter for better handling of PDFs
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        texts = text_splitter.split_documents(documents)
        print(f"Created {len(texts)} text chunks from PDFs")
        
        # Create vector store
        vectorstore = FAISS.from_documents(texts, embeddings)
        print("Vector store created successfully")
        
        # Save vector store to disk
        vectorstore.save_local("faiss_index")
        print("Vector store saved to disk")
        
        return vectorstore
    except Exception as e:
        print(f"Error in load_documents: {str(e)}")
        raise e

# Initialize vector store
vectorstore = load_documents()

@app.route('/')
def home():
    return render_template('index.html')

def format_document_html(document, template_type):
    """Format the document text into HTML with proper styling"""
    # Escape HTML to prevent injection
    document = html.escape(document)
    
    # Replace newlines with <br> tags
    document = document.replace('\n', '<br>')
    
    # Format title
    document = re.sub(r'TITLE: (.+)<br>', r'<h2 class="doc-title">\1</h2>', document)
    
    # Format section headers and content
    document = re.sub(r'(\d+\.\s+[A-Z\s]+)<br>(.+?)(?=<br>\d+\.|$)', 
                     r'<h3 class="section-title">\1</h3><div class="section-content">\2</div>', 
                     document, flags=re.DOTALL)
    
    # Clean up any remaining placeholder text
    document = document.replace('[Generated content]', '')
    
    # Add document type badge
    doc_type_map = {
        'sop': 'Standard Operating Procedure',
        'protocol': 'Test Protocol',
        'report': 'Analysis Report'
    }
    
    doc_type_html = f'<div class="doc-type-badge">{doc_type_map.get(template_type, "Document")}</div>'
    
    # Combine everything with styling
    styled_document = f"""
    <div class="generated-document">
        {doc_type_html}
        {document}
    </div>
    """
    
    return styled_document

@app.route('/generate', methods=['POST'])
def generate_document():
    template_type = request.json.get('template_type')
    requirements = request.json.get('requirements')
    
    try:
        if template_type == 'sop':
            template = """Create a detailed Standard Operating Procedure (SOP) document for the pharmaceutical industry.
            Topic: {requirements}
            
            Use the knowledge from the PDF documents to create a comprehensive and accurate SOP.
            
            Format the output as follows:
            
            TITLE: [Generated title based on requirements]
            
            1. PURPOSE
            [Generated content]
            
            2. SCOPE
            [Generated content]
            
            3. RESPONSIBILITIES
            [Generated content]
            
            4. MATERIALS AND EQUIPMENT
            [Generated content]
            
            5. PROCEDURE
            [Generated content with numbered steps]
            
            6. SAFETY CONSIDERATIONS
            [Generated content]
            
            7. QUALITY CONTROL
            [Generated content]
            
            8. REFERENCES
            [Generated content]"""
        
        elif template_type == 'protocol':
            template = """Create a detailed Test Protocol document for the pharmaceutical industry.
            Topic: {requirements}
            
            Use the knowledge from the PDF documents to create a comprehensive and accurate Test Protocol.
            
            Format the output as follows:
            
            TITLE: [Generated title based on requirements]
            
            1. OBJECTIVE
            [Generated content]
            
            2. TEST PARAMETERS
            [Generated content]
            
            3. EQUIPMENT AND MATERIALS
            [Generated content]
            
            4. TEST METHODOLOGY
            [Generated content]
            
            5. ACCEPTANCE CRITERIA
            [Generated content]
            
            6. DATA RECORDING
            [Generated content]
            
            7. REPORTING REQUIREMENTS
            [Generated content]"""
            
        elif template_type == 'report':
            template = """Create a detailed Analysis Report for the pharmaceutical industry.
            Topic: {requirements}
            
            Use the knowledge from the PDF documents to create a comprehensive and accurate Analysis Report.
            
            Format the output as follows:
            
            TITLE: [Generated title based on requirements]
            
            1. EXECUTIVE SUMMARY
            [Generated content]
            
            2. INTRODUCTION
            [Generated content]
            
            3. METHODOLOGY
            [Generated content]
            
            4. RESULTS AND DISCUSSION
            [Generated content]
            
            5. CONCLUSIONS
            [Generated content]
            
            6. RECOMMENDATIONS
            [Generated content]
            
            7. APPENDICES
            [Generated content]"""
        else:
            return jsonify({
                'success': False,
                'error': f'Template type "{template_type}" is not supported'
            })

        # Add Piramal Pharma specific context to the prompt
        piramal_context = """
        This document is being created for Piramal Pharma, a global pharmaceutical company with expertise in:
        - Contract Development and Manufacturing (CDMO)
        - Complex Hospital Generics
        - India Consumer Healthcare
        
        Ensure the document follows pharmaceutical industry best practices and regulatory standards including:
        - Good Manufacturing Practices (GMP)
        - FDA/EMA/CDSCO requirements as applicable
        - ICH guidelines
        """
        
        template = piramal_context + "\n\n" + template

        # Create a retrieval-based document generation system
        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(temperature=0.7, max_tokens=2000),
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 5})
        )
        
        # Combine the template with the retrieved content
        prompt_template = PromptTemplate(
            input_variables=["requirements"],
            template=template
        )
        
        # First retrieve relevant information from PDFs
        context = qa.run(requirements)
        
        # Then generate the document using the template and context
        llm_chain = LLMChain(
            llm=OpenAI(temperature=0.7, max_tokens=2000),
            prompt=PromptTemplate(
                input_variables=["requirements", "context"],
                template=template + "\n\nUse this information from the PDFs to inform your response: {context}"
            )
        )
        
        result = llm_chain.run(requirements=requirements, context=context)
        
        # Format the document as HTML for better display
        formatted_html = format_document_html(result.strip(), template_type)
        
        # Get plain text for download
        plain_text = result.strip()
        
        return jsonify({
            'success': True,
            'message': 'Document generated successfully',
            'document': plain_text,
            'formatted_html': formatted_html
        })
            
    except Exception as e:
        print(f"Error generating document: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=False)  # Disabled debugging for production
