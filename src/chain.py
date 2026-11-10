import json

from langchain_core.runnables import RunnableLambda

from retrieval import retrieve
from tools import extract_game_loop, generate_answer, get_stats


def prepare_query(question):
    # 第一步，复用T04的模型参数提取，建立后续步骤共用的字典。
    game_loop = extract_game_loop(question)
    return {"question": question, "game_loop": game_loop}


def query_stats(state):
    # 第二步，查询真实数值，将结果加入字典。
    state["stats"] = get_stats(state["game_loop"])
    print("查询结果")
    print(json.dumps(state["stats"], ensure_ascii=False, indent=2))
    return state


def retrieve_notes(state):
    # 第三步，根据原问题检索说明，将结果继续加入字典。
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


# RunnableLambda把普通函数接入LangChain，竖线按顺序连接步骤。
chain = (
    RunnableLambda(prepare_query)
    | RunnableLambda(query_stats)
    | RunnableLambda(retrieve_notes)
    | RunnableLambda(write_answer)
)


if __name__ == "__main__":
    question = "1920采样点双方当前矿分别是多少？当前矿表示什么？"
    try:
        answer = chain.invoke(question)
        print("最终回答")
        print(answer)
    except ValueError as error:
        print("处理失败", error)
