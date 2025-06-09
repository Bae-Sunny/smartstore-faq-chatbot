import uuid
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import ChatSession, ChatMessage
from .utils import get_rag_response

MAX_CONTEXT_MESSAGES = 5

class ChatbotAPIView(APIView):
    def post(self, request, *args, **kwargs):
        user_input = request.data.get("message")
        session_id = request.data.get("session_id")

        # 사용자 입력 확인
        if not user_input:
            return Response(
                {"error": "메시지를 입력해 주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 세션 확인 또는 새로 생성
        try:
            if session_id:
                session = ChatSession.objects.get(session_id=session_id)
                session.updated_at = timezone.now()
                session.save()
            else:
                session_id = str(uuid.uuid4())
                session = ChatSession.objects.create(session_id=session_id)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "유효하지 않은 세션입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 사용자 메시지 저장
        ChatMessage.objects.create(
            session=session,
            sender="user",
            message_text=user_input
        )

        # 대화 기록 조회 (최신순 → 시간순으로 정렬)
        history = ChatMessage.objects.filter(session=session).order_by("-timestamp")[:MAX_CONTEXT_MESSAGES * 2]
        messages = [
            {"role": msg.sender, "content": msg.message_text}
            for msg in reversed(history)
        ]

        # LLM 호출 (RAG 응답 생성)
        bot_reply = get_rag_response(
            user_query=user_input,
            conversation_messages=messages
        )

        # 챗봇 응답 저장
        ChatMessage.objects.create(
            session=session,
            sender="assistant",
            message_text=bot_reply
        )

        # 응답 반환
        return Response({
            "session_id": session_id,
            "user_message": user_input,
            "bot_response": bot_reply
        }, status=status.HTTP_200_OK)