import os
import chromadb
from openai import OpenAI

# 기본 설정
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CHROMA_N_RESULTS = 2
SIMILARITY_THRESHOLD = 0.7

# OpenAI API 설정
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# ChromaDB 설정
chroma = chromadb.HttpClient(host="chromadb", port=8000)
COLLECTION = "smartstore_faq_collection"

try:
    faq_collection = chroma.get_collection(name=COLLECTION)
except Exception:
    faq_collection = None  # 컬렉션 연결 실패 시 None 처리

def get_rag_response(user_query: str, conversation_messages: list = None):
    """
    사용자 질문과 이전 대화 기록을 바탕으로 FAQ 기반 LLM 응답 생성
    """
    if not client:
        return "OpenAI API 키가 설정되어 있지 않습니다."

    # 시스템 프롬프트 정의
    messages = [{
        "role": "system",
        "content": (
            "당신은 스마트스토어 FAQ만을 기반으로 질문에 답하는 챗봇입니다.\n\n"
            "반드시 다음 규칙을 지키세요:\n"
            "- [FAQ 지식]에 기반한 질문에만 답변합니다.\n"
            "- 스마트스토어와 무관하거나 관련 정보가 없는 경우, "
            "'저는 스마트 스토어 FAQ를 위한 챗봇입니다. 스마트 스토어에 대한 질문을 해주세요.'라고 답변합니다.\n"
            "- 추측, 일반 상식, 외부 정보는 절대 포함하지 마세요.\n\n"
            "답변은 줄바꿈(\\n)을 활용해 가독성 있게 작성하고,\n"
            "답변 이후에는 관련 질문 2가지를 다음 형식으로 제안하세요:\n"
            "1. ...\n"
            "2. ..."
        )
    }]

    if conversation_messages:
        messages.extend(conversation_messages)

    # 관련 FAQ 검색
    context = []
    if faq_collection:
        try:
            embed = client.embeddings.create(input=[user_query], model=EMBEDDING_MODEL).data[0].embedding
            result = faq_collection.query(
                query_embeddings=[embed],
                n_results=CHROMA_N_RESULTS,
                include=["documents", "metadatas", "distances"]
            )

            for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
                if dist < SIMILARITY_THRESHOLD:
                    question = meta.get("original_question", "질문 없음")
                    context.append(f"[FAQ 지식]\n{question}\n{doc}\n")

        except Exception as e:
            print("ChromaDB 검색 중 오류:", e)

    if context:
        messages.append({"role": "system", "content": "\n".join(context)})

    # 사용자 질문 추가
    messages.append({"role": "user", "content": user_query})

    # OpenAI LLM 호출
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print("OpenAI 응답 실패:", e)
        return "죄송합니다. 답변 생성 중 문제가 발생했습니다. 다시 시도해 주세요."