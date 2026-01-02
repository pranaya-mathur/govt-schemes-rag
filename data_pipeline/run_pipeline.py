#!/usr/bin/env python3
"""Complete data pipeline: Load -> Chunk -> Index"""
import json
from pathlib import Path
from chunking import LLMChunker
from indexing import QdrantIndexer


def load_schemes_from_json(file_path: str):
    """Load schemes from JSON file"""
    print(f"Loading schemes from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        schemes = json.load(f)
    print(f"Loaded {len(schemes)} schemes")
    return schemes


def save_chunks(chunks, output_path: str):
    """Save chunks to JSON file"""
    print(f"Saving chunks to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(chunks)} chunks")


def run_pipeline(schemes_file: str, output_chunks_file: str = None):
    """Run complete pipeline"""
    print("="*60)
    print("Starting Data Pipeline")
    print("="*60)
    
    # Step 1: Load schemes
    schemes = load_schemes_from_json(schemes_file)
    
    # Step 2: Chunk schemes using LLM
    print("\n" + "="*60)
    print("Step 1: LLM-Powered Chunking")
    print("="*60)
    chunker = LLMChunker()
    chunks = chunker.chunk_schemes_batch(schemes)
    
    # Save chunks if output path provided
    if output_chunks_file:
        save_chunks(chunks, output_chunks_file)
    
    # Step 3: Index into Qdrant
    print("\n" + "="*60)
    print("Step 2: Qdrant Indexing")
    print("="*60)
    indexer = QdrantIndexer()
    
    # Create collection
    indexer.create_collection()
    
    # Index chunks
    indexer.index_chunks(chunks)
    
    # Show stats
    indexer.get_collection_info()
    
    print("\n" + "="*60)
    print("✓ Pipeline Complete!")
    print("="*60)
    print(f"Total schemes processed: {len(schemes)}")
    print(f"Total chunks created: {len(chunks)}")
    print(f"Collection: {indexer.client.get_collection('myschemerag').collection_name}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run data pipeline")
    parser.add_argument(
        "schemes_file",
        help="Path to schemes JSON file"
    )
    parser.add_argument(
        "--output",
        help="Path to save chunks JSON (optional)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Run pipeline
    run_pipeline(args.schemes_file, args.output)
