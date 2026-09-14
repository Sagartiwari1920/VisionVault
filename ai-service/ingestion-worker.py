import os
import json
import pika
from minio import Minio
from qdrant_client import QdrantClient

# LangChain Imports
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

# 1. Initialize MinIO and Qdrant base clients
minio_client = Minio(
    "localhost:9000", 
    access_key=os.getenv("MINIO_ROOT_USER", "admin"), 
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "password123"), 
    secure=False
)

qdrant_url = "http://localhost:6333"
qdrant_client = QdrantClient(url=qdrant_url,api_key=os.getenv("QDRANT_API_KEY"))

# 2. Setup LangChain Embedder (using local Ollama)
embedder = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
COLLECTION_NAME = "ollama_learning_3_genai_optimized"

def process_document(ch, method, properties, body):
    message = json.loads(body)
    document_id = message.get("documentId")
    bucket_name = message.get("bucketName")
    local_path = f"./{document_id}"

    try:
        print(f"[*] Downloading {document_id} from MinIO...")
        minio_client.fget_object(bucket_name, document_id, local_path)

        # 3. LangChain Document Loading
        print(f"[*] Extracting text using PyMuPDFLoader...")
        loader = PyMuPDFLoader(file_path=local_path)
        docs = loader.load()

        # 4. LangChain Text Splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=200
        )
        split_docs = text_splitter.split_documents(documents=docs)

        # Inject the document_id into metadata so you can trace chunks back to the source file
        for doc in split_docs:
            doc.metadata["document_id"] = document_id

        if split_docs:
            print(f"[*] Storing {len(split_docs)} chunks in Qdrant via LangChain...")
            
            # 5. LangChain Qdrant Ingestion
            if qdrant_client.collection_exists(COLLECTION_NAME):
                vector_store = QdrantVectorStore.from_existing_collection(
                    embedding=embedder,
                    url=qdrant_url,
                    collection_name=COLLECTION_NAME
                )
                vector_store.add_documents(split_docs)
            else:
                QdrantVectorStore.from_documents(
                    documents=split_docs,
                    embedding=embedder,
                    url=qdrant_url,
                    collection_name=COLLECTION_NAME 
                )

        # Clean up local file
        if os.path.exists(local_path):
            os.remove(local_path)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"[+] Successfully processed and ingested {document_id}\n")

    except Exception as e:
        print(f"[-] Error processing {document_id}: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# Connect to RabbitMQ
credentials = pika.PlainCredentials('admin', 'password123')
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', credentials))
channel = connection.channel()

channel.queue_declare(queue='document_processing', durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='document_processing', on_message_callback=process_document)

print("[*] LangChain Worker is running and waiting for messages. To exit press CTRL+C")
channel.start_consuming()