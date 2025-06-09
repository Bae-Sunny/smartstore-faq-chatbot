import pickle
import os
import chromadb
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY가 없습니다... 확인해주세요.")
    exit()

client = OpenAI(api_key=api_key)

try:
    with open("/app/final_result.pkl", "rb") as f:
        raw_data = pickle.load(f)
        print("FAQ 데이터 로딩 완료!")
except Exception as e:
    print("FAQ 로딩 실패:", e)
    exit()

footers = [
    "도움말이 도움이 되었나요?", "별점1점", "별점2점", "별점3점", "별점4점", "별점5점",
    "소중한 의견을 남겨주시면 보완하도록 노력하겠습니다.",
    "보내기", "관련 도움말/키워드", "도움말 닫기"
]

cleaned = {}
for q, a in raw_data.items():
    if not isinstance(a, str):
        print(f"문자열 아닌 항목 있음 (key: {q})")
        continue
    for f in footers:
        if f in a:
            a = a.split(f, 1)[0]
    cleaned[q] = a.strip().replace("\n\n\n", "\n\n")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=700,
    chunk_overlap=70,
    length_function=len,
    add_start_index=True
)

chunks, metas, ids = [], [], []
idx = 0
for q, a in cleaned.items():
    pieces = splitter.split_text(a)
    for i, p in enumerate(pieces):
        chunks.append(p)
        metas.append({"original_question": q, "chunk_index": i + 1})
        ids.append(f"faq_{idx}")
        idx += 1

print(f"총 청크 수: {len(chunks)}")

model = "text-embedding-3-small"
embeddings = []
batch_size = 50

for i in range(0, len(chunks), batch_size):
    try:
        batch = chunks[i:i + batch_size]
        res = client.embeddings.create(input=batch, model=model)
        embs = [x.embedding for x in res.data]
        embeddings.extend(embs)
        print(f"{i + len(embs)}개 임베딩 생성함!")
    except Exception as e:
        print("임베딩 실패:", e)
        exit()

if len(embeddings) != len(chunks):
    print("임베딩 수 안 맞음... 뭔가 이상함")
    exit()

print("ChromaDB 연결 중...")
chroma = chromadb.HttpClient(host="chromadb", port=8000)
col_name = "smartstore_faq_collection"

try:
    existing = [c.name for c in chroma.list_collections()]
    if col_name in existing:
        chroma.delete_collection(name=col_name)
        print("기존 컬렉션 지웠어요")

    col = chroma.create_collection(name=col_name)
    for i in range(0, len(chunks), batch_size):
        col.add(
            documents=chunks[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            metadatas=metas[i:i + batch_size],
            ids=ids[i:i + batch_size]
        )
        print(f"{i + batch_size}개 저장됨!")

except Exception as e:
    print("ChromaDB 저장 실패...:", e)
    exit()