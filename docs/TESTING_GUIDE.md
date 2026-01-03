# Testing Guide - Government Schemes RAG System

Complete guide to test the system on your local machine.

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.10 or higher
- **RAM**: 8GB minimum (16GB recommended for Ollama)
- **Disk**: 10GB free space
- **OS**: Windows/Linux/macOS

### Required Accounts
1. **Groq API** (free tier: 30 req/min)
   - Sign up: https://console.groq.com
   - Get API key from dashboard

2. **Qdrant Cloud** (free tier: 1GB)
   - Sign up: https://cloud.qdrant.io
   - Create cluster and get URL + API key

---

## 🚀 Step-by-Step Setup

### 1. Clone Repository

```bash
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected time**: 5-10 minutes (downloads PyTorch, transformers, etc.)

### 4. Install and Setup Ollama

#### Windows
```bash
# Download from: https://ollama.ai/download/windows
# Install and run the installer

# Verify installation
ollama --version

# Pull model
ollama pull deepseek-r1:8b
```

#### Linux/macOS
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify installation
ollama --version

# Pull model
ollama pull deepseek-r1:8b
```

**Model size**: ~4.7GB  
**Download time**: 5-15 minutes (depending on internet speed)

#### Start Ollama Server

```bash
# In a separate terminal
ollama serve
```

Keep this terminal open!

### 5. Configure Environment Variables

Create `.env` file in project root:

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use any text editor
```

**Required `.env` contents**:
```ini
# Groq (for answer generation and judges)
GROQ_API_KEY=gsk_your_actual_groq_key_here

# Qdrant (vector database)
QDRANT_URL=https://your-cluster-xxxxx.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here

# Qdrant collection name
COLLECTION_NAME=govt_schemes

# Ollama (local inference)
OLLAMA_BASE_URL=http://localhost:11434

# Models
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_MODEL=deepseek-r1:8b
EMBEDDING_MODEL=BAAI/bge-m3

# Logging
LOG_LEVEL=INFO
```

### 6. Process Data (First Time Only)

⚠️ **Important**: You need the schemes JSON file from myscheme.gov.in

```bash
# If you have the schemes.json file
python data_pipeline/run_pipeline.py path/to/schemes.json
```

**Expected output**:
```
✅ Loaded 2,153 schemes
✅ Created 10,812 chunks
✅ Generated embeddings
✅ Indexed to Qdrant collection: govt_schemes
```

**Time**: 20-30 minutes (one-time process)

---

## ✅ Verify Setup

### Test 1: Check Ollama

```bash
curl http://localhost:11434/api/version
```

**Expected**:
```json
{"version":"0.x.x"}
```

### Test 2: Check Python Imports

```bash
python -c "from src.llm import get_ollama_llm, get_groq_llm; print('✅ Imports OK')"
```

**Expected**: `✅ Imports OK`

### Test 3: Check Qdrant Connection

```bash
python -c "from src.retrieval import VectorRetriever; r = VectorRetriever(); print('✅ Qdrant connected')"
```

**Expected**: `✅ Qdrant connected`

---

## 🧪 Testing the System

### Option 1: Quick Test Script

Create `test_quick.py`:

```python
from src.graph import app

# Test query
query = "What schemes are available for women entrepreneurs?"

print(f"Testing query: {query}\n")

result = app.invoke({"query": query})

print(f"Intent: {result['intent']}")
print(f"Retrieved: {len(result['retrieved_docs'])} documents")
print(f"\nAnswer:\n{result['answer']}")
print(f"\nNeeded reflection: {result.get('needs_reflection', False)}")
print(f"Needed correction: {result.get('needs_correction', False)}")
```

Run:
```bash
python test_quick.py
```

**Expected output**:
```
Testing query: What schemes are available for women entrepreneurs?

Intent: DISCOVERY
Retrieved: 5 documents

Answer:
Here are relevant government schemes for women entrepreneurs:

1. **Prime Minister Employment Generation Programme (PMEGP)**
   - Provides subsidy up to 35% for women entrepreneurs
   - Maximum project cost: ₹50 lakh
   ...

Needed reflection: False
Needed correction: False
```

### Option 2: Start API Server

```bash
python -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

#### Test with cURL

```bash
# Health check
curl http://localhost:8000/health

# Test query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "subsidy schemes for manufacturing",
    "top_k": 5
  }'
```

#### Test with Browser

Open: http://localhost:8000/docs

1. Click on **POST /query**
2. Click **Try it out**
3. Enter test query:
   ```json
   {
     "query": "What is PMEGP scheme?",
     "top_k": 5
   }
   ```
4. Click **Execute**

### Option 3: Interactive Python Session

```bash
python
```

```python
>>> from src.graph import app
>>> 
>>> # Test 1: Simple query
>>> result = app.invoke({"query": "Manufacturing schemes in India"})
>>> print(result['intent'])
DISCOVERY
>>> 
>>> # Test 2: Eligibility query
>>> result = app.invoke({"query": "Can I apply for PMEGP as a graduate?"})
>>> print(result['intent'])
ELIGIBILITY
>>> 
>>> # Test 3: Benefits query
>>> result = app.invoke({"query": "How much subsidy in Startup India?"})
>>> print(result['intent'])
BENEFITS
```

---

## 📊 Test Scenarios

### Scenario 1: Discovery Intent

**Query**: "List all schemes for small businesses"

**Expected**:
- Intent: `DISCOVERY`
- Top_k: 8 documents
- Answer lists multiple schemes

### Scenario 2: Eligibility Intent

**Query**: "Am I eligible for PMEGP if I am 25 years old?"

**Expected**:
- Intent: `ELIGIBILITY`
- Top_k: 5 documents
- Answer starts with "Yes" or "No"

### Scenario 3: Benefits Intent

**Query**: "What financial assistance does MSME scheme provide?"

**Expected**:
- Intent: `BENEFITS`
- Top_k: 5 documents
- Answer includes specific amounts

### Scenario 4: Comparison Intent

**Query**: "Compare PMEGP and Startup India schemes"

**Expected**:
- Intent: `COMPARISON`
- Top_k: 10 documents
- Answer compares both schemes side-by-side

### Scenario 5: Procedure Intent

**Query**: "How to apply for CGTMSE loan guarantee?"

**Expected**:
- Intent: `PROCEDURE`
- Top_k: 6 documents
- Answer provides step-by-step process

### Scenario 6: Self-RAG Trigger

**Query**: "xyz random gibberish query"

**Expected**:
- First retrieval returns low-relevance docs
- `needs_reflection: True`
- Query gets refined
- Second retrieval attempts better results

### Scenario 7: Corrective RAG Trigger

**Query**: "Very vague scheme question"

**Expected**:
- Answer generated but inadequate
- `needs_correction: True`
- Corrective query generated
- Re-retrieval and new answer

---

## 🔍 Debugging

### Check Logs

```bash
# View real-time logs
tail -f logs/rag_system.log

# Search for errors
grep ERROR logs/rag_system.log

# Search for specific query
grep "women entrepreneurs" logs/rag_system.log
```

### Common Issues

#### 1. Ollama Not Running

**Error**: `Connection refused to localhost:11434`

**Fix**:
```bash
# Check if Ollama is running
ps aux | grep ollama  # Linux/macOS
tasklist | findstr ollama  # Windows

# Start Ollama
ollama serve
```

#### 2. Groq API Key Invalid

**Error**: `401 Unauthorized`

**Fix**:
- Verify key in `.env` file
- Check key at https://console.groq.com
- Ensure no extra spaces in `.env`

#### 3. Qdrant Connection Failed

**Error**: `Could not connect to Qdrant`

**Fix**:
- Verify URL and API key in `.env`
- Check Qdrant cluster status at https://cloud.qdrant.io
- Ensure collection exists: `govt_schemes`

#### 4. Model Not Found

**Error**: `Model 'deepseek-r1:8b' not found`

**Fix**:
```bash
# List available models
ollama list

# Pull missing model
ollama pull deepseek-r1:8b
```

#### 5. Import Errors

**Error**: `ModuleNotFoundError: No module named 'langchain'`

**Fix**:
```bash
# Ensure venv is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

---

## 📈 Performance Testing

### Test Latency

Create `test_performance.py`:

```python
import time
from src.graph import app

queries = [
    "What is PMEGP?",
    "Eligibility for Startup India",
    "Compare MSME vs PMEGP"
]

for query in queries:
    start = time.time()
    result = app.invoke({"query": query})
    elapsed = time.time() - start
    
    print(f"Query: {query}")
    print(f"Intent: {result['intent']}")
    print(f"Time: {elapsed:.2f}s")
    print(f"Reflection: {result.get('needs_reflection', False)}")
    print(f"Correction: {result.get('needs_correction', False)}")
    print("-" * 50)
```

**Expected latency**:
- Simple queries: 1.5-2.5s
- With reflection: 3.5-4.5s
- With correction: 4.5-5.5s

---

## ✅ Success Checklist

Before considering your system "working":

- [ ] Ollama running and model pulled
- [ ] `.env` file configured with valid keys
- [ ] Qdrant collection exists with data
- [ ] Python imports work without errors
- [ ] Health check returns `200 OK`
- [ ] Test query returns valid intent
- [ ] Retrieved documents > 0
- [ ] Answer is coherent and on-topic
- [ ] API Swagger docs accessible
- [ ] Logs show no critical errors

---

## 🎯 Next Steps

Once testing is successful:

1. **Run full evaluation**: Test all 6 intent types
2. **Test edge cases**: Empty queries, very long queries
3. **Monitor costs**: Check Groq API usage
4. **Optimize**: Tune thresholds if needed
5. **Deploy**: Use Docker or AWS deployment

---

## 💡 Tips

1. **First run is slower**: BGE-M3 model downloads (~2GB)
2. **Use `--reload` in dev**: Auto-restarts on code changes
3. **Check Groq limits**: Free tier = 30 requests/min
4. **Ollama RAM usage**: ~4-6GB when model loaded
5. **Qdrant free tier**: 1GB storage, usually enough for 10k chunks

---

## 📞 Getting Help

If issues persist:

1. Check logs: `logs/rag_system.log`
2. Verify all prerequisites
3. Test each component individually
4. Check GitHub issues
5. Review error messages carefully

---

**Happy Testing! 🚀**