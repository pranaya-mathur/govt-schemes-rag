"""List all unique scheme names in Qdrant database"""

from qdrant_client import QdrantClient
import config
from collections import Counter

def list_schemes():
    """Retrieve and display scheme statistics from vector database"""
    print("\n" + "=" * 80)
    print("SCHEME NAMES IN DATABASE")
    print("=" * 80 + "\n")
    
    try:
        print(f"Connecting to: {config.QDRANT_URL}")
        client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        print("Connected\n")
        
        # Scroll through collection
        offset = None
        schemes = Counter()
        doc_count = 0
        
        print("Loading data...\n")
        
        while True:
            results = client.scroll(
                collection_name=config.COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=['scheme_name'],
                with_vectors=False
            )
            
            points, offset = results
            
            if not points:
                break
            
            for point in points:
                name = point.payload.get('scheme_name', 'Unknown')
                schemes[name] += 1
                doc_count += 1
            
            if offset is None:
                break
        
        # Display summary
        print("=" * 80)
        print(f"Found {len(schemes)} unique schemes across {doc_count} documents")
        print("=" * 80 + "\n")
        
        # Sort alphabetically
        sorted_schemes = sorted(schemes.items())
        
        print(f"{'#':<5} {'Scheme Name':<50} {'Chunks':<10}")
        print("-" * 80)
        
        for idx, (name, count) in enumerate(sorted_schemes, 1):
            print(f"{idx:<5} {name:<50} {count:<10}")
        
        print("\n" + "=" * 80)
        
        # Save to file
        output = 'all_schemes.txt'
        with open(output, 'w', encoding='utf-8') as f:
            f.write("SCHEME DATABASE EXPORT\n")
            f.write("=" * 80 + "\n\n")
            for idx, (name, count) in enumerate(sorted_schemes, 1):
                f.write(f"{idx}. {name} ({count} chunks)\n")
        
        print(f"Saved to {output}\n")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_schemes()
