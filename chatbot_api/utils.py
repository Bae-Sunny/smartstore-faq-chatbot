import os
import chromadb
from openai import OpenAI

# 설정값들
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CHROMA_N_RESULTS = 5
SIMILARITY_THRESHOLD = 1.1

# OpenAI API 설정
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY가 없어요... 확인해주세요.")
    client = None
else:
    client = OpenAI(api_key=api_key)

# ChromaDB 연결
chroma = chromadb.HttpClient(host="chromadb", port=8000)
COLLECTION = "smartstore_faq_collection"
try:
    faq_collection = chroma.get_collection(name=COLLECTION)
except Exception as e:
    print("ChromaDB 컬렉션 연결 실패:", e)
    faq_collection = None

def get_rag_response(user_query: str, conversation_messages: list = None):
    if not client:
        return "OpenAI API 키가 설정되어 있지 않습니다."

    # 기본 시스템 프롬프트
    messages = [{
        "role": "system",
        "content": (
            "당신은 스마트스토어 FAQ만을 기반으로 질문에 답하는 챗봇입니다.\n\n"
            "**반드시 다음 지침을 엄수하세요:**\n"
            "1. **[FAQ 지식]에서 질문과 가장 유사하거나 관련된 내용을 찾아 답변합니다.**\n"
            "2. FAQ에 없으면 '해당 내용은 FAQ에서 찾을 수 없습니다. 고객센터로 문의해주세요.' 라고 답변합니다.\n"
            "3. 스마트스토어와 무관한 질문엔 '스마트스토어 관련 질문을 해주세요.' 라고만 답변합니다.\n"
            "4. 추측이나 외부 지식 사용은 절대 금지입니다.\n\n"
            "**답변 스타일:**\n"
            "- 친절하고 정중하게.\n"
            "- 중요한 건 **굵게**, 필요한 경우 줄바꿈 활용.\n\n"
            "**항상 관련 질문 2개 추천으로 마무리하세요.**"
        )
    }]

    if conversation_messages:
        messages.extend(conversation_messages)

    context = []
    retrieved_chunks = []

    if faq_collection:
        try:
            embed = client.embeddings.create(input=[user_query], model=EMBEDDING_MODEL).data[0].embedding
            result = faq_collection.query(
                query_embeddings=[embed],
                n_results=CHROMA_N_RESULTS,
                include=["documents", "metadatas", "distances"]
            )

            print(f"\n--- 관련 FAQ {len(result['documents'][0])}개 찾았어요 (threshold: {SIMILARITY_THRESHOLD}) ---")
            for i in range(len(result["documents"][0])):
                doc = result["documents"][0][i]
                meta = result["metadatas"][0][i]
                dist = result["distances"][0][i]
                doc_id = result["ids"][0][i]

                print(f"{i+1}) ID: {doc_id}, 거리: {dist:.4f}, 내용 일부: '{doc[:50]}...'")

                question = meta.get("original_question", "질문 없음")
                if dist < SIMILARITY_THRESHOLD:
                    context.append(f"[FAQ 지식]\n원문 질문: {question}\n내용: {doc}\n")

                retrieved_chunks.append({
                    "doc": doc,
                    "meta": meta,
                    "dist": dist
                })
            print("------------------------------------------------\n")

        except Exception as e:
            print("FAQ 검색 실패:", e)
            messages.append({"role": "system", "content": "FAQ 검색 중 문제가 생겼습니다."})
            return "죄송합니다. FAQ 검색 도중 문제가 발생했어요."

    else:
        messages.append({"role": "system", "content": "FAQ 데이터베이스에 연결할 수 없습니다."})
        return "죄송합니다. 시스템에 문제가 있어요. 관리자에게 알려주세요."

    if context:
        context_message = "다음은 관련된 FAQ 정보입니다:\n\n" + "\n".join(context)
        messages.append({"role": "system", "content": context_message})
    else:
        if retrieved_chunks:
            fallback = "다음은 질문과 관련 있어 보이는 FAQ 정보입니다. 정보가 부족할 수도 있으니 고객센터 안내도 함께 해주세요.\n\n"
            for item in retrieved_chunks:
                q = item["meta"].get("original_question", "질문 없음")
                fallback += f"[FAQ 지식 - 거리: {item['dist']:.4f}]\n원문 질문: {q}\n내용: {item['doc']}\n\n"
            messages.append({"role": "system", "content": fallback.strip()})
        else:
            messages.append({"role": "system", "content": "관련된 FAQ 정보를 찾지 못했습니다."})

    messages.append({"role": "user", "content": user_query})

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=600,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print("답변 생성 실패:", e)
        return "죄송합니다. 답변 생성 중 문제가 생겼어요."
