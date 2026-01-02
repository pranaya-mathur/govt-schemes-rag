"""LLM-powered intelligent chunking for government schemes"""
import json
from typing import List, Dict
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import data_pipeline.config as config


class LLMChunker:
    """Intelligent chunker using LLM for theme-based splitting"""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=config.CHUNKING_MODEL,
            temperature=config.TEMPERATURE,
            base_url=config.OLLAMA_BASE_URL
        )
        self.chunking_prompt = self._build_prompt()
    
    def _build_prompt(self):
        """Build chunking prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", 
             f"You are a government scheme analyzer. Given scheme text, split it into "
             f"logical chunks based on these themes: {', '.join(config.THEME_CATEGORIES)}.\n"
             f"Return ONLY a JSON array of chunks with 'theme' and 'text' keys.\n"
             f"Keep chunks between {config.MIN_CHUNK_SIZE}-{config.MAX_CHUNK_SIZE} tokens."),
            ("human", 
             "Scheme Name: {scheme_name}\n"
             "Official URL: {official_url}\n\n"
             "Scheme Text:\n{text}")
        ])
    
    def chunk_scheme(self, scheme_data: Dict) -> List[Dict]:
        """Chunk a single scheme using LLM"""
        try:
            chain = self.chunking_prompt | self.llm
            result = chain.invoke({
                "scheme_name": scheme_data.get("scheme_name", "Unknown"),
                "official_url": scheme_data.get("official_url", ""),
                "text": scheme_data.get("text", "")
            })
            
            # Parse LLM response
            chunks_json = self._extract_json(result.content)
            chunks = json.loads(chunks_json)
            
            # Add metadata to each chunk
            enriched_chunks = []
            for chunk in chunks:
                enriched_chunks.append({
                    "scheme_name": scheme_data.get("scheme_name"),
                    "official_url": scheme_data.get("official_url"),
                    "ministry": scheme_data.get("ministry"),
                    "theme": chunk.get("theme", "general"),
                    "text": chunk.get("text", "")
                })
            
            return enriched_chunks
        
        except Exception as e:
            print(f"Error chunking scheme {scheme_data.get('scheme_name')}: {str(e)}")
            # Fallback: create single chunk
            return [{
                "scheme_name": scheme_data.get("scheme_name"),
                "official_url": scheme_data.get("official_url"),
                "ministry": scheme_data.get("ministry"),
                "theme": "general",
                "text": scheme_data.get("text", "")
            }]
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        # Find JSON array in response
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text
    
    def chunk_schemes_batch(self, schemes: List[Dict]) -> List[Dict]:
        """Chunk multiple schemes"""
        all_chunks = []
        total = len(schemes)
        
        for idx, scheme in enumerate(schemes):
            print(f"Chunking scheme {idx+1}/{total}: {scheme.get('scheme_name', 'Unknown')}")
            chunks = self.chunk_scheme(scheme)
            all_chunks.extend(chunks)
        
        print(f"\nTotal schemes: {total}")
        print(f"Total chunks created: {len(all_chunks)}")
        return all_chunks


if __name__ == "__main__":
    # Example usage
    chunker = LLMChunker()
    
    sample_scheme = {
        "scheme_name": "PMEGP",
        "official_url": "https://www.kviconline.gov.in/pmegp",
        "ministry": "Ministry of MSME",
        "text": """Prime Minister's Employment Generation Programme (PMEGP) is a credit-linked 
        subsidy scheme. Benefits: Get 25-35% subsidy on project cost. Maximum project cost 
        up to Rs 50 lakh. Eligibility: Age 18+ years, minimum 8th pass for manufacturing. 
        Application: Apply online through KVIC portal with documents."""
    }
    
    chunks = chunker.chunk_scheme(sample_scheme)
    print(json.dumps(chunks, indent=2))
