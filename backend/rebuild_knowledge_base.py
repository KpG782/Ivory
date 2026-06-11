from __future__ import annotations

from services.vectorstore import ingest_knowledge_base


def main() -> None:
    report = ingest_knowledge_base()
    print("Ivory knowledge base rebuilt")
    print(f"Documents: {report.document_count}")
    print(f"Chunks: {report.chunk_count}")
    print(f"Backend: {report.backend}")
    print(f"Persist dir: {report.persist_dir}")


if __name__ == "__main__":
    main()
