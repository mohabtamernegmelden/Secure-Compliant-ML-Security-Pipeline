# Secure & Compliant ML Security Pipeline

## Local development

1. Create and activate a Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Start the backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. Start the frontend: `cd frontend && npm install && npm run dev`

## Docker run

```bash
docker build -t ml-security-pipeline .
docker run --rm -p 8000:8000 -e PORT=8000 ml-security-pipeline
```

## Azure deployment

See [azure-deploy.md](azure-deploy.md) for copy-pasteable Azure CLI commands.
