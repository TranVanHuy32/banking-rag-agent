# Banking RAG Agent

A Retrieval-Augmented Generation (RAG) system tailored for banking and financial document processing and querying.

## Features

- Document ingestion for various file formats (PDF, DOCX, etc.)
- Advanced text processing and semantic chunking
- Vector-based document retrieval
- Integration with LLMs (Gemini, OpenAI, etc.)
- API endpoint for querying the knowledge base

## Prerequisites

- Python 3.8+
- Poetry (for dependency management)
- Docker (optional, for running services)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/banking-rag-agent.git
   cd banking-rag-agent
   ```

2. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

## Usage

### Running the ETL Pipeline

```bash
python -m src.ingestion.pipeline --input-dir ./data/raw --output-dir ./data/processed
```

### Starting the API Server

```bash
uvicorn api.main:app --reload
```

### Running with Docker

```bash
docker-compose up -d
```

## Project Structure

```
banking-rag-agent/
├── config/           # Configuration files
├── data/             # Data storage
├── notebooks/        # Jupyter notebooks for exploration
├── src/              # Source code
├── tests/            # Test files
└── api/              # API implementation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

MIT
