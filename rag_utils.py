# -----------------------------
# FILE: rag_utils.py
# -----------------------------
def process_query(text, query, chat_history=None):
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    from langchain.chat_models import ChatOpenAI
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from dotenv import load_dotenv
    import os
    load_dotenv()
    import re

    # Hardcoded API key (Note: this is not a best practice but required as specified)
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key not found. Please set the OPENAI_API_KEY environment variable.")
    # Just to check — this should print True if the key loaded correctly
    print("API Key Loaded:", os.getenv("OPENAI_API_KEY") is not None)

    

    try:
        # Context enhancement with chat history
        if chat_history and len(chat_history) > 0:
            # Extract the last 3 exchanges for context
            relevant_history = chat_history[-min(3, len(chat_history)):]
            history_context = "\n".join([f"Human: {h[0]}\nAssistant: {h[1]}" for h in relevant_history])
            enhanced_query = f"Given this conversation history:\n{history_context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query

        # Improved text splitter for better chunking
        text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Larger chunks to keep tables together
        chunk_overlap=100,
        length_function=len,
        separators=["--- TABLE FROM PAGE", "\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_text(text)
        
        # Add chunk identifiers to track sources
        identified_chunks = []
        for i, chunk in enumerate(chunks):
            # Try to identify the chunk source (e.g., section heading)
            section_match = re.search(r'^(.*?)\n', chunk)
            section_name = section_match.group(1) if section_match else f"Section {i+1}"
            identified_chunks.append((f"[{section_name}]", chunk))
        
        # Create embeddings and vector store
        embeddings = OpenAIEmbeddings()
        texts = [chunk[1] for chunk in identified_chunks]
        metadatas = [{"source": chunk[0]} for chunk in identified_chunks]
        vector_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
        
        # Create a retrieval system that only gets the most relevant chunks
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}  # Only retrieve the 5 most relevant chunks
        )
        
        # Create a custom prompt template that includes the query context and asks for confidence
        prompt_template = """You are an Annual Report Assistant analyzing financial documents.
Use the following context to answer the question.

Context:
{context}

Question: {question}

Answer the question based only on the provided context. If the context doesn't contain 
the information needed to answer the question, just say "I don't have enough information 
in this report to answer that question." Be specific and include relevant financial data 
when available.

If the context contains tables, analyze them carefully to extract relevant data. Pay special 
attention to column headers and row labels when interpreting table data. Tables are often 
indicated by structured text with tabs or consistent spacing.

End your answer with a confidence score from 1-5 where:
1: Very uncertain, mostly guessing
2: Low confidence, limited evidence
3: Moderate confidence, some supporting data
4: High confidence, well supported by data
5: Very high confidence, directly stated in report

Format your confidence score like this: [Confidence: X/5]

Also include the sources of your information like this: [Sources: section names]
"""
        
        PROMPT = PromptTemplate(
            template=prompt_template, 
            input_variables=["context", "question"]
        )
        
        # Setup the QA chain with the custom prompt
        llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        # Get the answer
        result = qa_chain({"query": enhanced_query})
        answer = result["result"]
        
        # If source documents are available, format them nicely
        if "source_documents" in result and result["source_documents"]:
            sources = set()
            for doc in result["source_documents"]:
                if "source" in doc.metadata:
                    sources.add(doc.metadata["source"])
            
            # If sources aren't already included in the answer
            if "[Sources:" not in answer:
                sources_str = ", ".join(sources)
                answer += f"\n\n[Sources: {sources_str}]"
        
        # If confidence score isn't already included
        if "[Confidence:" not in answer:
            answer += "\n\n[Confidence: 3/5]"  # Default moderate confidence
            
        return answer
        
    except Exception as e:
        return f"I encountered an error processing your question: {str(e)}. Please try uploading a smaller document or asking a more specific question about a particular section of the report."