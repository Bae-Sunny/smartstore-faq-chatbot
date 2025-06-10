const chatMessages = document.getElementById("chat-messages");
const userInput = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");

let sessionId = null;
let isLoading = false;

// 마크다운을 HTML로 변환하는 함수
function renderMarkdown(text) {
    return text
        // 굵은 글씨: **text** → <strong>text</strong>
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // 이탤릭: *text* → <em>text</em>
        .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
        // 대괄호 하이라이트: [text] → 하이라이트
        .replace(/\[([^\]]+)\]/g, '<span class="section-title">[$1]</span>')
        // 번호 목록 강조: "1. " → 강조된 번호
        .replace(/^(\d+\.\s)/gm, '<span class="step-number">$1</span>')
        // 줄바꿈: \n → <br>
        .replace(/\n/g, '<br>')
        // 특수 강조: 「text」 → 하이라이트
        .replace(/「([^」]+)」/g, '<span class="highlight">$1</span>');
}

function addMessage(sender, text, isMarkdown = false) {
    const box = document.createElement("div");
    box.className = `message-box ${sender}`;
    const msg = document.createElement("div");
    msg.className = "message-text";

    if (isMarkdown && sender === 'bot') {
        msg.innerHTML = renderMarkdown(text);
    } else {
        msg.textContent = text;
    }

    box.appendChild(msg);
    chatMessages.appendChild(box);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showLoading() {
    const box = document.createElement("div");
    box.className = "message-box bot";
    box.id = "loading-message";
    const msg = document.createElement("div");
    msg.className = "message-text";
    msg.innerHTML = `
    <div class="loading">
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
      <div class="loading-dot"></div>
    </div>
  `;
    box.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight; // 로딩 메시지 추가 후 스크롤
}

function hideLoading() {
    const loadingMessage = document.getElementById("loading-message");
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || isLoading) return;

    addMessage("user", message);
    userInput.value = "";
    isLoading = true;
    sendButton.disabled = true;
    sendButton.textContent = "전송중...";

    showLoading();

    const body = {
        message: message,
        ...(sessionId && { session_id: sessionId })
    };

    try {
        const res = await fetch("http://localhost:8000/api/chat/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        const data = await res.json();
        hideLoading();

        if (res.ok) {
            sessionId = data.session_id;
            addMessage("bot", data.bot_response, true);
        } else {
            addMessage("bot", `오류 발생: ${data.error || "서버 오류"}`);
        }
    } catch (err) {
        hideLoading();
        addMessage("bot", `⚠️ 네트워크 오류: ${err.message}`);
    } finally {
        isLoading = false;
        sendButton.disabled = false;
        sendButton.textContent = "보내기";
    }
}

sendButton.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});
