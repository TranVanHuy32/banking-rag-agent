# setup.py
# setup.py
from setuptools import setup, find_packages

setup(
    name="banking-rag-agent",
    version="0.1.0",
    packages=find_packages(include=['src', 'src.*']),
    install_requires=[
        'fastapi>=0.68.0',
        'uvicorn>=0.15.0',
        'python-dotenv>=0.19.0',
        'pydantic>=1.8.0',
        'google-cloud-texttospeech>=2.0.0',
        'gtts>=2.3.0',
        'SpeechRecognition>=3.8.0',
        'pyaudio>=0.2.11',
        'playsound>=1.3.0',
        'customtkinter>=5.2.0',
        'requests>=2.26.0',
        'numpy>=1.21.0',
        'sentence-transformers>=2.2.0',
        'langchain>=0.0.200',
        'langchain-google-genai>=0.0.7',
        'faiss-cpu>=1.7.4',
        'chromadb>=0.4.0',
    ],
    python_requires='>=3.8',
    package_dir={"": "."},
    include_package_data=True,
)
