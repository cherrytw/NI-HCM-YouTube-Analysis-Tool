# YouTube Video Analysis Tool

Command-line tool for analyzing YouTube videos using Llama 3. Features include video metadata extraction, transcript analysis, sentiment analysis of comments, and relevance scoring.

## Demo
![](https://github.com/cherrytw/NI-HCM-YouTube-Analysis-Tool/blob/main/presentation/demo.gif)

## Prerequisites

### Setting up Llama 3 8b
1. Install Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. Pull and run Llama 3:
```bash
ollama run llama3
```

### Python Requirements
- Python 3.9
- Required packages:
```bash
pip install google-api-python-client
pip install youtube-transcript-api
pip install deep-translator
pip install langdetect
pip install thefuzz
pip install rich
pip install transformers
pip install torch
```

## Usage
Run the analysis tool:
```bash
python main.py
```

Enter a YouTube URL when prompted.

## Features
- Video metadata extraction
- Transcript analysis
- Comment sentiment analysis
- Multi-language support
- Topic classification
- Relevance scoring
