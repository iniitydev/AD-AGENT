import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings

def get_llm(model="gpt-4o", temperature=0):
    """
    Returns a language model client.

    Checks for OPENAI_API_KEY environment variable. If it exists, returns
    a ChatOpenAI client. Otherwise, returns a ChatOllama client.
    """
    if os.environ.get("OPENAI_API_KEY"):
        print("Using OpenAI model.")
        return ChatOpenAI(model=model, temperature=temperature)
    else:
        print("Using local Ollama model.")
        return ChatOllama(model="phi3", temperature=temperature)

def get_embedding_model():
    """
    Returns an embedding model client.

    Checks for OPENAI_API_KEY environment variable. If it exists, returns
    an OpenAIEmbeddings client. Otherwise, returns an OllamaEmbeddings client.
    """
    if os.environ.get("OPENAI_API_KEY"):
        print("Using OpenAI embeddings.")
        return OpenAIEmbeddings()
    else:
        print("Using local Ollama embeddings.")
        # Using a small, efficient model for local embeddings
        return OllamaEmbeddings(model="nomic-embed-text")

def query_llm(messages, model="gpt-4o"):
    """
    A simple wrapper to query the selected LLM.
    This replaces the old `query_openai` function.
    """
    llm = get_llm(model=model)
    response = llm.invoke(messages)
    return response.content
