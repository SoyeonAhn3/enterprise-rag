"""Korean Streamlit interface for the fixed-corpus RAG demonstration."""

import streamlit as st

from app_runtime import AppResources, EXAMPLE_QUESTIONS
from config import ConfigurationError, MAX_QUESTION_LENGTH, load_settings
from embeddings import EmbeddingError
from grounding import AnswerValidationError
from index_store import IndexErrorBase
from llm import ClaudeError
from rag import RetrievalError, validate_question


@st.cache_resource(show_spinner=False)
def get_resources():
    # Keys are read only on the server, never included in cache keys or output.
    return AppResources(server_settings())


def server_settings():
    try:
        secrets = st.secrets.to_dict()
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        secrets = {}
    return load_settings(secrets=secrets)


def render_answer(result: dict):
    st.markdown(result["answer"])
    for source in result["sources"]:
        with st.expander(f"[{source['source_id']}] {source['document']} · {source['page']}쪽"):
            st.text(source["excerpt"])
    st.caption(f"응답 시간 {result['latency_ms'] / 1000:.2f}초")


def main():
    st.set_page_config(page_title="가온비즈 업무 도우미", page_icon="📚", layout="centered")
    st.title("가온비즈 업무 도우미")
    st.caption("구매·결재·IT 보안·계약 규정을 문서 근거와 함께 확인하세요.")
    st.info("가상 기업의 공개 데모 문서 4개를 사용합니다. 개인정보나 회사 기밀을 입력하지 마세요.")
    st.caption("질문과 관련 문서 발췌는 Claude로 전달되며, 운영자가 추적을 켠 경우 LangSmith에도 기록됩니다.")
    try:
        settings = server_settings()
    except ConfigurationError:
        st.error("서버 설정을 확인해야 합니다. 운영자에게 문의해 주세요.")
        st.stop()
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("question_count", 0)
    limit = settings.session_question_limit
    exhausted = st.session_state.question_count >= limit
    st.caption(f"이번 세션 질문 {st.session_state.question_count}/{limit}회 · 질문당 최대 {MAX_QUESTION_LENGTH}자")
    with st.expander("예시 질문", expanded=not st.session_state.messages):
        selected = st.selectbox("질문을 선택하세요", EXAMPLE_QUESTIONS)
        use_example = st.button("이 질문 보내기", disabled=exhausted)
    for message in st.session_state.messages:
        with st.chat_message("user"):
            st.write(message["question"])
        with st.chat_message("assistant"):
            if "result" in message:
                render_answer(message["result"])
            else:
                st.error(message["error"])
    if exhausted:
        st.warning("이번 세션의 질문 한도에 도달했습니다.")
    entered = st.chat_input("업무 규정에 대해 질문하세요", max_chars=MAX_QUESTION_LENGTH, disabled=exhausted)
    question = selected if use_example else entered
    if not question or exhausted:
        return
    try:
        question = validate_question(question)
    except ValueError:
        st.warning(f"1~{MAX_QUESTION_LENGTH}자의 질문을 입력해 주세요.")
        return
    st.session_state.question_count += 1  # Failed attempts also consume a slot.
    message = {"question": question}
    try:
        with st.spinner("문서 근거를 확인하고 있습니다…"):
            result = get_resources().answer(question)
        message["result"] = result
    except ConfigurationError:
        message["error"] = "답변 서비스 설정이 준비되지 않았습니다. 운영자에게 문의해 주세요."
    except (IndexErrorBase, EmbeddingError, RetrievalError):
        message["error"] = "문서 검색을 준비하지 못했습니다. 잠시 후 다시 시도해 주세요."
    except ClaudeError:
        message["error"] = "답변 서비스에 연결하지 못했거나 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요."
    except AnswerValidationError:
        message["error"] = "답변의 근거를 검증하지 못했습니다. 질문을 구체적으로 바꿔 다시 시도해 주세요."
    except Exception:
        message["error"] = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."
    st.session_state.messages.append(message)
    st.rerun()


if __name__ == "__main__":
    main()
