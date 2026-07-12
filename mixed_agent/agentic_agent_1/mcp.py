from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
import chromadb
import PyPDF2

mcp = FastMCP("AdvancedDataExplorer")

# --- Setup Databases ---
# Replace with your actual credentials
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="pdf_knowledge")

@mcp.tool()
def query_graph_neo4j(cypher_query: str) -> str:
    """Query the Neo4j graph to find relationships between entities."""
    with neo4j_driver.session() as session:
        result = session.run(cypher_query)
        return str([record.data() for record in result])

@mcp.tool()
def search_vector_db(query_text: str, n_results: int = 3) -> str:
    """Search the Vector DB (Chroma) for specific text snippets related to a topic."""
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return str(results['documents'])

@mcp.tool()
def ingest_pdf_to_vector_db(file_path: str) -> str:
    """Read a PDF, chunk it, and save it into the Vector Database."""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                collection.add(
                    documents=[text],
                    ids=[f"page_{i}_{file_path}"]
                )
        return f"Successfully ingested {file_path} into Vector DB."
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run()
