import json

from langchain_core.runnables import RunnableLambda
from requests.exceptions import RequestException

from answer import generate_answer
from context import apply_context, clear_session, create_session, prepare_context
from retrieval import retrieve
from tools import get_stats


def prepare_query(input_data):
    # 字符串用于单次调用；连续对话传入问题和同一个会话字典。
    if isinstance(input_data, str):
        input_data = {"question": input_data, "session": create_session()}
    return prepare_context(input_data)


def query_stats(state):
    # 第二步，查询真实数值，将结果加入字典。
    state["stats"] = get_stats(state["game_loop"])
    print("查询结果")
    print(json.dumps(state["stats"], ensure_ascii=False, indent=2))
    return state


def retrieve_notes(state):
    # 第三步，根据问题检索说明，将结果继续加入字典。
    state["notes"] = retrieve(state["question"])
    print("检索说明")
    print(json.dumps(state["notes"], ensure_ascii=False, indent=2))
    return state


def write_answer(state):
    # 第四步，统一模板同时使用数值和说明，生成一次最终回答。
    return generate_answer(
        state["question"],
        stats=state["stats"],
        notes=state["notes"],
    )


# 只在这里定义问答流程，模块提供的函数按顺序连接。
chain = (
    RunnableLambda(prepare_query)
    | RunnableLambda(query_stats)
    | RunnableLambda(apply_context)
    | RunnableLambda(retrieve_notes)
    | RunnableLambda(write_answer)
)


def chat(question, session=None):
    if session is None:
        session = create_session()
    return chain.invoke({"question": question, "session": session})


def main():
    session = create_session()
    print("输入问题开始对话，输入clear清空会话，输入exit退出。")
    while True:
        try:
            question = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question == "exit":
            break
        if question == "clear":
            clear_session(session)
            print("会话已清空")
            continue
        if not question:
            continue
        try:
            answer = chat(question, session)
            print("助手：", answer)
        except (ValueError, RequestException) as error:
            print("提示：", error)


if __name__ == "__main__":
    main()
