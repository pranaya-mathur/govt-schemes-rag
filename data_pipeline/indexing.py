"""Index chunks into Qdrant vector database"""
import uuid
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import data_pipeline.config as config


class QdrantIndexer:
    """Index chunks into Qdrant"""
    
    def __init__(self):
        print("Connecting to Qdrant...")
        self.client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        
        print(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        print(f"Embedding dimension: {self.dimension}")
    
    def create_collection(self):
        """Create Qdrant collection"""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if config.COLLECTION_NAME in collection_names:
                print(f"Collection '{config.COLLECTION_NAME}' already exists")
                overwrite = input("Recreate collection? (yes/no): ")
                if overwrite.lower() == 'yes':
                    self.client.delete_collection(config.COLLECTION_NAME)
                    print("Deleted existing collection")
                else:
                    return
            
            # Create new collection
            self.client.create_collection(
                collection_name=config.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection: {config.COLLECTION_NAME}")
        
        except Exception as e:
            print(f"Error creating collection: {str(e)}")
            raise
    
    def embed_chunks(self, chunks: List[Dict]) -> List[List[float]]:
        """Generate embeddings for chunks"""
        texts = [chunk["text"] for chunk in chunks]
        print(f"Generating embeddings for {len(texts)} chunks...")
        
        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True
        )
        return embeddings.tolist()
    
    def index_chunks(self, chunks: List[Dict], batch_size: int = 100):
        """Index chunks into Qdrant"""
        print(f"Indexing {len(chunks)} chunks...")
        
        # Generate embeddings
        embeddings = self.embed_chunks(chunks)
        
        # Create points
        points = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "scheme_name": chunk.get("scheme_name", "Unknown"),
                    "official_url": chunk.get("official_url", ""),
                    "ministry": chunk.get("ministry", ""),
                    "theme": chunk.get("theme", "general"),
                    "text": chunk.get("text", "")
                }
            )
            points.append(point)
        
        # Upload in batches
        total = len(points)
        for i in range(0, total, batch_size):
            batch = points[i:i+batch_size]
            self.client.upsert(
                collection_name=config.COLLECTION_NAME,
                points=batch
            )
            print(f"Uploaded batch {i//batch_size + 1}/{(total-1)//batch_size + 1}")
        
        print(f"\n✓ Successfully indexed {total} chunks into Qdrant!")
    
    def get_collection_info(self):
        """Get collection statistics"""
        info = self.client.get_collection(config.COLLECTION_NAME)
        print(f"\nCollection: {config.COLLECTION_NAME}")
        print(f"Points count: {info.points_count}")
        print(f"Vector size: {info.config.params.vectors.size}")
        print(f"Distance: {info.config.params.vectors.distance}")


if __name__ == "__main__":
    # Example: Index sample chunks
    indexer = QdrantIndexer()
    
    # Create collection
    indexer.create_collection()
    
    # Sample chunks
    sample_chunks = [
        {
            "scheme_name": "PMEGP",
            "official_url": "https://www.kviconline.gov.in/pmegp",
            "ministry": "Ministry of MSME",
            "theme": "benefits",
            "text": "Get 25-35% subsidy on project cost under PMEGP scheme."
        },
        {
            "scheme_name": "PMEGP",
            "official_url": "https://www.kviconline.gov.in/pmegp",
            "ministry": "Ministry of MSME",
            "theme": "eligibility",
            "text": "Eligibility: Age 18+ years, minimum 8th pass for manufacturing."
        }
    ]
    
    # Index chunks
    indexer.index_chunks(sample_chunks)
    
    # Show stats
    indexer.get_collection_info()
