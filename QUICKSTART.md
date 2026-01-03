# Quick Start - 5 Minutes to First Query

Get the system running in 5 minutes (assuming you already have Python and Git installed).

---

## 🚀 Prerequisites (One-Time Setup)

### 1. Install Ollama

**Windows/macOS/Linux**:
```bash
# Visit: https://ollama.ai/download
# Download and install for your OS

# Verify installation
ollama --version

# Pull the model (4.7GB download)
ollama pull deepseek-r1:8b
```

### 2. Get API Keys (Free Tier)

1. **Groq**: https://console.groq.com (30 req/min free)
2. **Qdrant**: https://cloud.qdrant.io (1GB free)

---

## ⚡ Quick Setup (5 Minutes)

### Step 1: Clone & Install (2 min)

```bash
# Clone repository
git clone https://github.com/pranaya-mathur/govt-schemes-rag.git
cd govt-schemes-rag

# Create virtual environment
python -m venv venv

# Activate (choose your OS)
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment (1 min)

```bash
# Copy template
cp .env.example .env

# Edit .env file with your keys
nano .env  # or use any text editor
```

**Minimum required in `.env`**:
```ini
GROQ_API_KEY=your_groq_key_here
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key_here
COLLECTION_NAME=govt_schemes
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 3: Start Ollama (30 sec)

```bash
# In a separate terminal
ollama serve
```

Keep this terminal open!

### Step 4: Test System (1 min)

```bash
# Run automated test
python test_system.py
```

**Expected output**:
```
✅ All imports successful
✅ Qdrant connected successfully
✅ Ollama connected successfully
✅ Groq connected successfully
✅ Retrieved 3 documents
✅ RAG pipeline completed successfully!
✅ ALL TESTS PASSED!
```

### Step 5: Start API (30 sec)

```bash
python -m uvicorn api.app:app --reload
```

**API ready at**: http://localhost:8000

---

## 🧪 Testing Options

### Option 1: Browser (Easiest)

1. Open: http://localhost:8000/docs
2. Click on **POST /query**
3. Click **Try it out**
4. Enter:
   ```json
   {
     "query": "What is PMEGP scheme?",
     "top_k": 5
   }
   ```
5. Click **Execute**

### Option 2: cURL

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Manufacturing schemes for small businesses",
    "top_k": 5
  }'
```

### Option 3: Python Script

Create `test_query.py`:
```python
from src.graph import app

result = app.invoke({"query": "What schemes are available for women entrepreneurs?"})

print(f"Intent: {result['intent']}")
print(f"\nAnswer:\n{result['answer']}")
```

Run:
```bash
python test_query.py
```

---

## 💡 Sample Queries to Try

```python
# Discovery
"List all manufacturing schemes in India"

# Eligibility
"Can women apply for PMEGP scheme?"

# Benefits
"How much subsidy does Startup India provide?"

# Comparison
"Compare PMEGP vs Mudra Yojana"

# Procedure
"How to apply for CGTMSE loan guarantee?"

# General
"What is the purpose of MSME schemes?"
```

---

## 🔧 Common Issues

### Ollama Not Running
```bash
# Error: Connection refused to localhost:11434
# Fix: Start Ollama
ollama serve
```

### Model Not Found
```bash
# Error: Model 'deepseek-r1:8b' not found
# Fix: Pull the model
ollama pull deepseek-r1:8b
```

### Import Errors
```bash
# Error: ModuleNotFoundError
# Fix: Activate venv and reinstall
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### API Keys Invalid
```bash
# Error: 401 Unauthorized
# Fix: Check .env file for correct keys (no extra spaces)
```

---

## 📊 Expected Performance

| Query Type | Time | Behavior |
|------------|------|----------|
| **Simple** | 1.5-2.5s | Direct answer |
| **With Self-RAG** | 3.5-4.5s | Query refinement |
| **With Corrective RAG** | 4.5-5.5s | Answer re-generation |

---

## 📚 Next Steps

Once testing works:

1. **Read full guide**: [TESTING_GUIDE.md](TESTING_GUIDE.md)
2. **Process your data**: See [data_pipeline/README.md](data_pipeline/README.md)
3. **Deploy to cloud**: See [README.md#deployment](README.md#deployment)
4. **Monitor usage**: Check `logs/rag_system.log`

---

## ✅ Success Criteria

Your system is working if:

- ✅ `python test_system.py` passes all tests
- ✅ API returns status 200 at `/health`
- ✅ Test query returns coherent answer
- ✅ Intent classification works (6 types)
- ✅ Documents retrieved (count > 0)
- ✅ No errors in `logs/rag_system.log`

---

**Need help?** See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed troubleshooting.

**Ready to deploy?** See [README.md](README.md) for Docker and AWS instructions.
