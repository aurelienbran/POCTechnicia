# Server Implementation Guide

This document outlines the steps required to make the POCTechnicia project work on a server environment.

## Prerequisites

- Docker installed for running Qdrant vector database
- Python 3.10+ for the backend
- Node.js 18+ for the frontend

## Installation Steps

### 1. Fix Dependencies

Add the following dependencies to requirements.txt:
```
tiktoken==0.5.2  # For token encoding and size measurement
```

If using a newer version of Qdrant, you may need to downgrade the client:
```
qdrant-client==1.6.0  # For compatibility with certain Qdrant server versions
```

### 2. Fix Anthropic Client Issues

Due to compatibility issues with the Anthropic Python SDK, create a custom minimal client implementation:

```python
class MinimalAnthropicClient:
    def __init__(self, api_key):
        self.api_key = api_key
        import httpx
        # Create HTTP client without problematic options
        self.http = httpx.Client(timeout=60.0)
        
    def messages_create(self, model, messages, max_tokens=1000, temperature=0):
        """Minimal version of the messages API."""
        import json
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API Error: {response.status_code}")
            
        return response.json()
```

This custom client should be used in the `llm_interface.py` and `question_classifier.py` files.

### 3. Make VectorStore Robust to Version Mismatches

Update the VectorStore to handle validation errors from the Qdrant client:

```python
async def initialize(self) -> None:
    """Initialize the VectorStore."""
    try:
        # Initialize collection
        # ...
        
        # Handle collection info retrieval errors
        try:
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(f"Collection state: {collection_info}")
        except Exception as validation_error:
            logger.warning(f"Cannot retrieve collection info (version issue): {str(validation_error)}")
            
        self._initialized = True
        
    except Exception as e:
        logger.error(f"Error initializing collection: {str(e)}")
        # Try to continue despite the error to allow startup
        if "validation error" in str(e).lower() or "Extra inputs are not permitted" in str(e):
            logger.warning(f"Qdrant version incompatibility detected, but continuing: {str(e)}")
            self._initialized = True
        else:
            raise e
```

Also update the `get_collection_info` method to handle validation errors.

### 4. Use Correct Host Configuration for Backend

Ensure the uvicorn server binds to 0.0.0.0 instead of default 127.0.0.1 to allow external connections:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Update the `start_all.sh` script to include the `--host 0.0.0.0` parameter.

## Deployment Process

1. Start Qdrant with Docker:
   ```bash
   docker start qdrant || docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v $(pwd)/storage:/qdrant/storage qdrant/qdrant
   ```

2. Initialize the Qdrant collection:
   ```bash
   python init_qdrant.py
   ```

3. Start the backend:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. Start the frontend:
   ```bash
   cd frontend && npm run dev
   ```

Alternatively, use the provided `start_all.sh` script which has been updated with these configurations.

## Troubleshooting

- If you encounter Qdrant validation errors: These are often related to version mismatches between the client and server. The workarounds in this guide should handle most cases.
- If Anthropic API calls fail: Check API keys and the custom client implementation.
- If the backend isn't accessible: Verify it's running with the correct host binding (0.0.0.0).