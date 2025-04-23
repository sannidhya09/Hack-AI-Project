
# 📊 TarkAI — HackAI 2025
Environment Setup: You will have to use your own API key in the .env file for complete functioning of the code. Working model will be demonstrated in video and live demo.

## 🧠 Problem Statement
Annual reports are packed with valuable insights about a company’s financials, strategy, and performance. However, these reports are often long, complex, and hard to understand quickly — especially for investors, researchers, and business analysts.

## 🎯 Our Goal
Build an AI-powered app that can automatically:
- Read and understand uploaded annual report PDFs
- Process Text, Images, Tables
- Answer questions users ask in natural language (Q&A)
- Extract and summarize content from charts, tables, and text
- Help users gain key insights efficiently without reading the whole document

## 💼 Real-World Use Cases
- Investors doing company analysis
- Financial journalists needing quick facts
- Business students learning report analysis
- Compliance officers reviewing key highlights

## 💡 Why This Matters
Automating this process reduces hours of manual reading and allows non-experts to access crucial insights in seconds.

---

## 🤖 Core Q&A Capability

Our app uses a RAG (Retrieval-Augmented Generation) pipeline to accurately answer questions grounded in the uploaded annual report. 

- 🔹 **PDF Text Extraction**: Extract raw text and tables using PyPDF2.
- 🔹 Able to process images using Tesseract OCR 
- 🔹 **Chunking & Embedding**: Split the text and generate vector embeddings using OpenAI's `text-embedding-ada-002`.
- 🔹 **Semantic Retrieval**: Use FAISS to fetch only the relevant chunks of the report.
- 🔹 **Q&A Generation**: A lightweight GPT model generates grounded answers based only on retrieved context and semantic search


This ensures users get **fact-based answers** derived from the annual report — no hallucinations.

## 📊 Table & Figure Extraction

Our app detects and extracts tables and figures from the PDF using PyMuPDF and image-based parsing. We ensure questions related to tabular data (like revenue by year) can be answered accurately, with fallback handling if charts are unavailable.



