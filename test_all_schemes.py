"""List all unique scheme names stored in Qdrant database"""
from qdrant_client import QdrantClient
import config
from collections import Counter

def list_all_schemes():
    """Fetch and display all unique scheme names from Qdrant"""
    print("\n" + "="*80)
    print("ALL SCHEME NAMES IN QDRANT DATABASE")
    print("="*80 + "\n")
    
    try:
        # Connect to Qdrant
        print(f"Connecting to Qdrant: {config.QDRANT_URL}")
        client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        print("✓ Connected\n")
        
        # Scroll through all documents
        offset = None
        scheme_counter = Counter()
        total_docs = 0
        
        print("Loading scheme names...\n")
        
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
            
            # Count scheme occurrences
            for point in points:
                scheme_name = point.payload.get('scheme_name', 'Unknown')
                scheme_counter[scheme_name] += 1
                total_docs += 1
            
            if offset is None:
                break
        
        # Display results
        print("="*80)
        print(f"SUMMARY: {len(scheme_counter)} Unique Schemes | {total_docs} Total Documents")
        print("="*80 + "\n")
        
        # Sort by name
        sorted_schemes = sorted(scheme_counter.items(), key=lambda x: x[0])
        
        print(f"{'#':<5} {'Scheme Name':<50} {'Doc Count':<10}")
        print("-"*80)
        
        for idx, (scheme, count) in enumerate(sorted_schemes, 1):
            print(f"{idx:<5} {scheme:<50} {count:<10}")
        
        print("\n" + "="*80)
        
        # Save to file
        output_file = 'all_schemes.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("ALL SCHEME NAMES IN DATABASE\n")
            f.write("="*80 + "\n\n")
            for idx, (scheme, count) in enumerate(sorted_schemes, 1):
                f.write(f"{idx}. {scheme} ({count} docs)\n")
        
        print(f"✓ Saved to {output_file}")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_all_schemes()
