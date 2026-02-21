"""Document ingestion script for loading knowledge base into ChromaDB.

Reads markdown documents from docs/ directory, chunks them into 300-500 token pieces,
generates embeddings using Gemini API, and stores them in ChromaDB.

Run this script once during setup: python scripts/ingest_docs.py
"""

import asyncio
import re
import sys
from pathlib import Path

from courseflow.config import settings
from courseflow.domain.models import Document, DocumentMetadata
from courseflow.infrastructure.embeddings.gemini import GeminiEmbeddingClient
from courseflow.infrastructure.vector_store.chroma import ChromaAdapter


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    """Chunk text on paragraph boundaries with token overlap.
    
    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk (default: 500)
        overlap: Token overlap between chunks (default: 50)
    
    Returns:
        List of text chunks
    """
    # Split on paragraph boundaries (double newline)
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Rough token estimate (1 token ≈ 0.75 words)
        para_tokens = len(para.split()) * 0.75
        current_tokens = len(current_chunk.split()) * 0.75
        
        if current_tokens + para_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk.strip())
                # Keep last N tokens for overlap
                words = current_chunk.split()
                overlap_words = int(overlap / 0.75)
                overlap_text = " ".join(words[-overlap_words:]) if len(words) > overlap_words else ""
                current_chunk = overlap_text + " " + para if overlap_text else para
            else:
                # Paragraph itself is too long, split on sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    sentence_tokens = len(sentence.split()) * 0.75
                    if current_tokens + sentence_tokens > max_tokens and current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                        current_tokens = sentence_tokens
                    else:
                        current_chunk += " " + sentence
                        current_tokens += sentence_tokens
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


async def ingest_documents(docs_dir: str = "./docs") -> None:
    """Ingest documents from directory into ChromaDB.
    
    Args:
        docs_dir: Root directory containing markdown documents
    """
    # Initialize clients
    print("Initializing ChromaDB and Gemini clients...")
    vector_store = ChromaAdapter(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name=settings.CHROMA_COLLECTION_NAME,
    )
    await vector_store.initialize()
    embedding_client = GeminiEmbeddingClient(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_EMBEDDING_MODEL
    )
    
    # Find all markdown files
    docs_path = Path(docs_dir)
    md_files = list(docs_path.rglob("*.md"))
    
    print(f"Found {len(md_files)} markdown files")
    print("-" * 60)
    
    total_chunks = 0
    
    try:
        for doc_path in md_files:
            # Read document
            content = doc_path.read_text(encoding="utf-8")
            
            # Extract metadata from path
            # e.g., docs/biology/photosynthesis.md -> subject=biology, topic=photosynthesis
            relative_path = doc_path.relative_to(docs_path)
            subject = relative_path.parent.name if relative_path.parent != Path(".") else "general"
            topic = doc_path.stem  # filename without extension
            
            # Chunk document
            chunks = chunk_text(content, max_tokens=500, overlap=50)
            # Domain model requires at least 100 chars per chunk
            chunks = [c for c in chunks if len(c.strip()) >= 100]
            print(f"\n📄 {doc_path.name} ({subject}/{topic})")
            print(f"   Chunks: {len(chunks)}")
            if not chunks:
                print("   ⏭️  Skipped (all chunks shorter than 100 chars)")
                continue
            
            # Process each chunk
            documents = []
            for i, chunk in enumerate(chunks):
                # Generate embedding (with rate limiting respect)
                print(f"   → Chunk {i+1}/{len(chunks)}: Generating embedding... ", end="", flush=True)
                
                try:
                    embedding = await embedding_client.generate_embedding(chunk)
                    print("✓")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    # If we hit rate limit, wait and retry
                    if "quota" in str(e).lower() or "429" in str(e):
                        print("   ⏳ Rate limit hit, waiting 60s...")
                        await asyncio.sleep(60)
                        embedding = await embedding_client.generate_embedding(chunk)
                        print("   ✓ Retry successful")
                    else:
                        raise
                
                # Create Document object
                doc_metadata = DocumentMetadata(
                    source=str(doc_path),
                    subject=subject,
                    topic=topic,
                    chunk_index=i
                )
                
                document = Document(
                    id=f"{subject}-{topic}-chunk-{i}",
                    content=chunk,
                    embedding=embedding,
                    metadata=doc_metadata
                )
                
                documents.append(document)
                
                # Small delay to respect rate limits (15 RPM = 4s between requests)
                if i < len(chunks) - 1:
                    await asyncio.sleep(4.5)  # Slightly more than 4s to be safe
            
            # Add all chunks to ChromaDB
            print(f"   💾 Storing {len(documents)} chunks in ChromaDB... ", end="", flush=True)
            await vector_store.add_documents(documents)
            print("✓")
            
            total_chunks += len(chunks)
        
        print("\n" + "=" * 60)
        print(f"✓ Ingestion complete!")
        print(f"  Total files: {len(md_files)}")
        print(f"  Total chunks: {total_chunks}")
        print(f"  ChromaDB collection: {settings.CHROMA_COLLECTION_NAME}")
        print("=" * 60)
        
    finally:
        # Cleanup
        await embedding_client.close()


if __name__ == "__main__":
    # Check if API key is set
    if settings.GEMINI_API_KEY == "your_api_key_here":
        print("Error: GEMINI_API_KEY not set!")
        print("Please set your API key in .env file or environment variable")
        sys.exit(1)
    
    asyncio.run(ingest_documents())
