"""Create payload indexes in Qdrant for metadata filtering

Qdrant requires payload indexes for filtering on fields.
This script creates indexes for:
- scheme_name (keyword index)
- theme (keyword index)

Run this once after data indexing to enable metadata filtering.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
import config


def create_payload_indexes():
    """Create payload indexes for metadata filtering"""
    print("\n" + "="*80)
    print("QDRANT PAYLOAD INDEX CREATION")
    print("="*80 + "\n")
    
    try:
        # Connect to Qdrant
        print(f"Connecting to Qdrant: {config.QDRANT_URL}")
        client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        print("✓ Connected to Qdrant\n")
        
        # Check collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if config.COLLECTION_NAME not in collection_names:
            print(f"❌ Collection '{config.COLLECTION_NAME}' not found!")
            print("Please run the data pipeline first to create and populate the collection.")
            sys.exit(1)
        
        print(f"Collection '{config.COLLECTION_NAME}' found\n")
        
        # Index 1: scheme_name (keyword)
        print("Creating index for 'scheme_name' (keyword)...")
        try:
            client.create_payload_index(
                collection_name=config.COLLECTION_NAME,
                field_name="scheme_name",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print("✓ Index created for 'scheme_name'")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ Index already exists for 'scheme_name'")
            else:
                raise
        
        # Index 2: theme (keyword)
        print("\nCreating index for 'theme' (keyword)...")
        try:
            client.create_payload_index(
                collection_name=config.COLLECTION_NAME,
                field_name="theme",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print("✓ Index created for 'theme'")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ Index already exists for 'theme'")
            else:
                raise
        
        # Verify indexes
        print("\n" + "-"*80)
        print("Verifying indexes...")
        collection_info = client.get_collection(config.COLLECTION_NAME)
        
        print(f"\nCollection: {config.COLLECTION_NAME}")
        print(f"Points: {collection_info.points_count}")
        print(f"Vector size: {collection_info.config.params.vectors.size}")
        print("\nPayload indexes created successfully! ✓")
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("1. Restart your API server")
        print("2. Test metadata filtering with a query like:")
        print("   curl -X POST http://localhost:8000/query \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"query\": \"Can women apply for PMEGP?\"}'")
        print("\n✓ Metadata filtering is now enabled!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check Qdrant connection settings in .env")
        print("2. Ensure collection exists (run data pipeline first)")
        print("3. Check Qdrant server is running and accessible")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    create_payload_indexes()
