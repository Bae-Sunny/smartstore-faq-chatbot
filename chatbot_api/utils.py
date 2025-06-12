import os
import chromadb
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CHROMA_N_RESULTS = 5
SIMILARITY_THRESHOLD = 1.1

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

chroma = chromadb.HttpClient(host="chromadb", port=8000)
COLLECTION = "smartstore_faq_collection"

try:
    faq_collection = chroma.get_collection(name=COLLECTION)
except Exception:
    faq_collection = None

def get_rag_response(user_query: str, conversation_messages: list = None):
    if not client:
        return "OpenAI API 키가 설정되어 있지 않습니다."

    messages = [{
        "role": "system",
        "content": (
            "당신은 스마트스토어 FAQ만을 기반으로 질문에 답하는 챗봇입니다.\n\n"
            "**반드시 다음 지침을 엄수하세요:**\n"
            "1. **[FAQ 지식]에서 질문과 가장 유사하거나 관련된 내용을 찾아 답변합니다.**\n"
            "2. 스마트스토어 관련 질문이지만 [FAQ 지식]에서 답변할 수 있는 **유사한 정보조차 찾을 수 없으면**, '해당 내용은 FAQ에서 찾을 수 없습니다. 고객센터로 문의해주세요.' 라고 답변합니다.\n"
            "3. 스마트스토어와 완전히 무관한 질문에는 '저는 스마트스토어 전용 챗봇입니다. 스마트스토어 관련 질문을 해주세요.' 라고 답변합니다.\n"
            "4. FAQ에 없는 내용을 추측하거나, 일반 상식/외부 지식을 사용하거나, 불확실한 정보를 제공하는 것을 **절대 금지합니다.**\n\n"
            "**답변 스타일 및 형식:**\n"
            "- 친근하고 정중한 어조를 사용하세요.\n"
            "- 필요한 경우 단계별로 명확하게 설명하고, 중요한 내용은 **굵게** 강조하세요.\n"
            "- 가독성을 위해 적절한 줄바꿈(\\n\\n)을 사용하세요.\n\n"
            "**답변 마무리:**\n"
            "답변 후에는 항상 다음 형식으로 관련 질문 2개를 추천합니다:\n"
            "\n**[관련 질문 추천]**\n"
            "1. [구체적인 관련 질문]\n"
            "2. [구체적인 관련 질문]"
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

            for i in range(len(result["documents"][0])):
                doc = result["documents"][0][i]
                meta = result["metadatas"][0][i]
                dist = result["distances"][0][i]
                question = meta.get("original_question", "질문 없음")

                if dist < SIMILARITY_THRESHOLD:
                    context.append(f"[FAQ 지식]\n원문 질문: {question}\n내용: {doc}\n")

                retrieved_chunks.append({
                    "doc": doc,
                    "meta": meta,
                    "dist": dist
                })

        except Exception as e:
            messages.append({"role": "system", "content": "FAQ 검색 시스템 오류로 정보를 가져오지 못했습니다."})
            return "죄송합니다. FAQ 정보를 검색하는 도중 오류가 발생했습니다."
    else:
        messages.append({"role": "system", "content": "FAQ 데이터베이스에 연결할 수 없습니다."})
        return "죄송합니다. 챗봇 시스템에 문제가 있습니다. 관리자에게 문의해주세요."

    if context:
        context_message = "다음은 관련된 FAQ 정보입니다:\n\n" + "\n".join(context)
        messages.append({"role": "system", "content": context_message})
    else:
        if retrieved_chunks:
            fallback_context_message = "다음은 질문과 관련된 것으로 보이는 FAQ 정보입니다. 정보가 충분하지 않을 수 있으니, 이 정보를 바탕으로 답변을 시도하거나, 정보가 부족하다면 고객센터로 문의하라는 안내를 해주세요.\n\n"
            for item in retrieved_chunks:
                question = item["meta"].get("original_question", "질문 없음")
                fallback_context_message += f"[FAQ 지식 - 검색 거리: {item['dist']:.4f}]\n원문 질문: {question}\n내용: {item['doc']}\n\n"
            messages.append({"role": "system", "content": fallback_context_message.strip()})
        else:
            messages.append({"role": "system", "content": "관련된 FAQ 정보를 찾을 수 없습니다."})

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
        return "죄송합니다. 답변 생성 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
