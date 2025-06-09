from django.db import models

class ChatSession(models.Model):
    """
    사용자와 챗봇 간 대화 세션을 관리하는 모델
    """
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "챗 세션"
        verbose_name_plural = "챗 세션들"


class ChatMessage(models.Model):
    """
    개별 메시지를 저장하는 모델 (사용자 또는 챗봇의 발화)
    """
    SENDER_CHOICES = [
        ("user", "사용자"),
        ("assistant", "챗봇"),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.session.session_id}] {self.sender}: {self.message_text[:30]}..."

    class Meta:
        ordering = ['timestamp']
        verbose_name = "챗 메시지"
        verbose_name_plural = "챗 메시지들"
