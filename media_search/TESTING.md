# Media Search Testing Suite

This directory contains comprehensive tests for the media search service, demonstrating the semantic search capabilities with real-world scenarios.

## Test Files Overview

### 🧪 `test_e2e_v1.py` - End-to-End Test V1: Pacific Ocean vs Volcano
**Purpose**: Tests semantic search precision by distinguishing between related and unrelated content.

**Test Scenario**:
- ✅ Adds 3 Pacific Ocean files (whales, coral reef, surfing)
- ✅ Adds 1 volcano file (control/negative case)
- ✅ Tests Pacific Ocean queries return only relevant files
- ✅ Validates semantic similarity scores

**Key Features Tested**:
- Dual vector search (summary + frame details)
- Multi-user support with private indexes
- Semantic similarity scoring accuracy
- Content filtering precision

### 🗑️ `test_e2e_file_crud_v1.py` - End-to-End File CRUD Test V1: FAISS Synchronization
**Purpose**: Tests that file CRUD operations properly synchronize with FAISS indexes.

**Test Scenario**:
- ✅ Creates a test user with private indexes
- ✅ Adds a test file and verifies it's searchable
- ✅ Deletes the file and verifies it's removed from FAISS
- ✅ Ensures complete cleanup of both database and FAISS data

**Key Features Tested**:
- File addition and indexing
- FAISS index synchronization
- File deletion and cleanup
- Complete data removal verification

### 🚀 `run_e2e_test.sh` - Quick Test Runner (Semantic Search)
**Purpose**: Easy script to run the Pacific Ocean vs Volcano test.

```bash
./run_e2e_test.sh
```

### 🧹 `run_crud_test.sh` - Quick CRUD Test Runner
**Purpose**: Easy script to run the FAISS synchronization test.

```bash
./run_crud_test.sh
```

### 📊 `test_full_workflow.py` - Comprehensive API Testing
**Purpose**: Tests all API endpoints and full workflow with hardcoded realistic data.

```bash
python run_tests.py
```

## Running Tests

### Prerequisites
1. Ensure media search service is running:
   ```bash
   docker-compose up -d media_search
   ```

2. Verify service health:
   ```bash
   curl http://localhost:5001/health
   ```

### Test Execution

**Option 1: Run E2E Test V1 - Semantic Search Precision (Recommended)**
```bash
# Using the script
./run_e2e_test.sh

# Or directly
python test_e2e_v1.py --url http://localhost:5001
```

**Option 2: Run CRUD Test V1 - FAISS Synchronization**
```bash
# Using the script
./run_crud_test.sh

# Or directly
python test_e2e_file_crud_v1.py --url http://localhost:5001
```

**Option 3: Run Full Workflow Test**
```bash
python run_tests.py
```

### Test Results Interpretation

**✅ Perfect Results** should show:

**E2E Test V1 (Semantic Search)**:
- Pacific Ocean queries return scores 0.4-0.7 for relevant content
- Volcano content scores near 0 for Pacific Ocean queries
- Frame details search completely filters out unrelated content
- Control queries (volcano) return volcano content with high scores

**CRUD Test V1 (FAISS Synchronization)**:
- File addition creates searchable content with high scores
- File found in all search types (summary, frame details, combined)
- File deletion removes content from all FAISS indexes
- Post-deletion searches return 0 results

**Example Output - Semantic Search**:
```
🔎 Testing query: 'Pacific Ocean marine life whales'
  📊 Summary search results:
    - #1: humpback_whales_pacific.mp4 (score: 0.634)
    - #2: great_barrier_reef_pacific.mp4 (score: 0.486)
    - #3: big_wave_surfing_pacific.mp4 (score: 0.357)
  ✅ Perfect filtering: 3 Pacific files, 0 volcano files
```

**Example Output - FAISS Synchronization**:
```
🔍 Verifying file is searchable...
✅ File found in summary search with score: 0.830
✅ File found in frame details search with score: 0.679

🗑️ Deleting test file...
✅ File deleted successfully

🔍 Verifying file is NOT searchable after deletion...
✅ File correctly removed from summary search (found 0 other results)
✅ File correctly removed from frame details search (found 0 other results)
✅ File is completely removed from all FAISS indexes
```

## Test Data

### Pacific Ocean Files
1. **Humpback Whales** - Migration documentary
2. **Great Barrier Reef** - Coral ecosystem exploration
3. **Big Wave Surfing** - Pacific coast extreme sports

### Control File
1. **Mount Vesuvius** - Volcanic eruption documentary

## Performance Benchmarks

Based on test results, the semantic search achieves:
- **High precision**: 0.6+ scores for highly relevant content
- **Good filtering**: 0.3-0.5 scores for moderately relevant content
- **Excellent separation**: <0.1 scores for unrelated content
- **Fast execution**: ~1.1 seconds for full test suite

## Troubleshooting

### Service Not Running
```bash
# Check service status
docker-compose ps media_search

# Start service
docker-compose up -d media_search

# Check logs
docker-compose logs media_search
```

### Port Issues
If port 5001 is occupied:
```bash
# Check what's using the port
lsof -i :5001

# Update docker-compose.yml port mapping if needed
```

### Test Failures
- Review test output for specific error messages
- Check service logs for backend issues
- Verify test data was properly indexed
- Ensure semantic model is fully loaded

## Adding New Tests

To create additional test scenarios:

1. **Create new test file**: `test_your_scenario.py`
2. **Use the E2E V1 template**: Copy the structure from `test_e2e_v1.py`
3. **Define test data**: Create realistic media files with good descriptions
4. **Test specific queries**: Focus on your use case requirements
5. **Add cleanup**: Always clean up test data after tests

### Example Test Structure
```python
class YourTestCase:
    def test_health_check(self):
        # Verify service is running
        
    def add_test_files(self):
        # Add your test media files
        
    def test_your_queries(self):
        # Test your specific search scenarios
        
    def cleanup(self):
        # Clean up test data
```

## CPU-Only & Offline Support

The tests verify that the semantic search works:
- ✅ **CPU-only**: No GPU dependencies
- ✅ **Offline**: After initial model download
- ✅ **Fast**: Sub-second response times
- ✅ **Accurate**: High semantic similarity precision

This makes it perfect for local development and offline applications. 