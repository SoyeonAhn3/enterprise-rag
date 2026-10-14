"""Resources shared by Streamlit reruns; UI-independent request handling."""

import atexit
from threading import RLock

from config import DOCUMENTS_DIR, INDEX_DIR, Settings
from deployment import ensure_index
from llm import ClaudeClient
from rag import RAGAssistant, Retriever
from tracing import LangSmithTracer

EXAMPLE_QUESTIONS = (
    "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?",
    "공급가액 180만원인 업무용 노트북을 구매할 때 최종 결재권자와 사전 보안검토 필요 여부를 알려주세요.",
    "가온비즈 직원 식당에서 채식 메뉴는 매주 몇 번 제공하나요?",
)


class AppResources:
    def __init__(self, settings: Settings):
        self.lock = RLock()
        self.client = self.retriever = self.tracer = None
        self.closed = False
        try:
            self.client = ClaudeClient(settings)
            ensure_index(INDEX_DIR, DOCUMENTS_DIR, settings)
            self.retriever = Retriever(settings)
            self.tracer = LangSmithTracer(settings)
            self.assistant = RAGAssistant(self.retriever, self.client, tracer=self.tracer)
        except Exception:
            self.close()
            raise
        atexit.register(self.close)

    def answer(self, question: str) -> dict:
        # The small demo serializes access to the shared embedding/index objects.
        with self.lock:
            return self.assistant.answer(question)

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for resource in (self.tracer, self.client, self.retriever):
                if resource is not None:
                    resource.close()
