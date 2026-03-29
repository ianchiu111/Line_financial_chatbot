
"""
Static RAG helper for an existing OpenAI Vector Store.

Usage:
1. Set OPENAI_API_KEY in your environment.
2. Put your vector store ID in VECTOR_STORE_ID below.
3. Edit the questions list in __main__.
4. Run the script.

Example:
    export OPENAI_API_KEY="sk-..."
    python openai_vectorstore_rag_static.py
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, List
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(".env")


# ====== Static settings ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")
MODEL_NAME = "gpt-4o-mini"
MAX_NUM_RESULTS = 5
SHOW_RETRIEVED_CHUNKS = True
# ============================


@dataclass
class RetrievedChunk:
    file_id: str | None
    filename: str | None
    score: float | None
    text: str

    def preview(self, limit: int = 250) -> str:
        clean = " ".join(self.text.split())
        return clean if len(clean) <= limit else clean[:limit] + "..."


def build_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY. Please set it in your environment.")
    return OpenAI(api_key=OPENAI_API_KEY)


def _extract_text_from_content(content: Any) -> str:
    parts: List[str] = []

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
                    continue

                if isinstance(text_value, dict):
                    nested = text_value.get("value")
                    if isinstance(nested, str):
                        parts.append(nested)
                        continue

                value = item.get("value")
                if isinstance(value, str):
                    parts.append(value)
                    continue

            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str):
                parts.append(text_attr)
                continue

            if hasattr(text_attr, "value") and isinstance(text_attr.value, str):
                parts.append(text_attr.value)
                continue

            value_attr = getattr(item, "value", None)
            if isinstance(value_attr, str):
                parts.append(value_attr)

    return "\n".join(p for p in parts if p).strip()


def search_vector_store(
    client: OpenAI,
    query: str,
    vector_store_id: str = VECTOR_STORE_ID,
    max_num_results: int = MAX_NUM_RESULTS,
) -> List[RetrievedChunk]:
    result = client.vector_stores.search(
        vector_store_id=vector_store_id,
        query=query,
        max_num_results=max_num_results,
    )

    data = getattr(result, "data", None)
    if data is None and isinstance(result, dict):
        data = result.get("data", [])

    chunks: List[RetrievedChunk] = []
    for item in data or []:
        file_id = getattr(item, "file_id", None)
        filename = getattr(item, "filename", None)
        score = getattr(item, "score", None)
        content = getattr(item, "content", None)

        if isinstance(item, dict):
            file_id = item.get("file_id", file_id)
            filename = item.get("filename", filename)
            score = item.get("score", score)
            content = item.get("content", content)

        text = _extract_text_from_content(content)
        if text:
            chunks.append(
                RetrievedChunk(
                    file_id=file_id,
                    filename=filename,
                    score=score,
                    text=text,
                )
            )

    return chunks


def build_context(chunks: List[RetrievedChunk]) -> str:
    sections: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        header = f"[Chunk {idx}]"
        if chunk.filename:
            header += f" file={chunk.filename}"
        if chunk.score is not None:
            header += f" score={chunk.score:.4f}"
        sections.append(f"{header}\n{chunk.text}")
    return "\n\n".join(sections)


def generate_rag_response(
    client: OpenAI,
    question: str,
    chunks: List[RetrievedChunk],
    model: str = MODEL_NAME,
) -> str:
    if not chunks:
        return "找不到相關知識，請換個問法試試看。"

    context = build_context(chunks)

    prompt = f"""你是一個財經名詞助理。
請只根據下面提供的知識片段回答，不要自行補充片段中沒有的事實。

請用繁體中文回答，並盡量用簡單、清楚的方式說明。
回答格式：
1. 先用一句話直接回答
2. 再用 2~4 點補充

如果知識片段不足以回答使用者的問題，則回覆「訊息不足，請聯繫工程師。」

使用者問題：
{question}

知識片段：
{context}
"""

    response = client.responses.create(
        model=model,
        input=prompt,
    )
    return response.output_text.strip()


def ask_question(
    question: str,
    show_chunks: bool = SHOW_RETRIEVED_CHUNKS,
) -> str:
    client = build_client()
    chunks = search_vector_store(client=client, query=question)

    if show_chunks:
        print("=" * 80)
        print(f"Question: {question}")
        print("-" * 80)
        print("Retrieved chunks:")
        if not chunks:
            print("No relevant chunks found.")
        else:
            for idx, chunk in enumerate(chunks, start=1):
                print(f"\n[{idx}] filename={chunk.filename} score={chunk.score}")
                print(chunk.preview(500))
        print("-" * 80)

    answer = generate_rag_response(
        client=client,
        question=question,
        chunks=chunks,
    )
    return answer


# if __name__ == "__main__":
#     questions = [
#         # "什麼是股息？",
#         # "什麼是股東？",
#         "",
#     ]

#     for q in questions:
#         result = ask_question(q)
#         print("RAG Response:")
#         print(result)
#         print("=" * 80)
#         print()