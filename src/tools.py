import json
from pathlib import Path

if __package__:
    from .model_client import ask
else:
    from model_client import ask


DATA_FILE = Path(__file__).resolve().parent.parent / "data/processed/organized_records.json"
FIELDS = ["minerals_current", "vespene_current", "workers_active_count"]


def get_stats(game_loop):
    # 1. 读取现有统计表。
    with DATA_FILE.open(encoding="utf-8") as file:
        records = json.load(file)

    # 2. 分别查找这个采样点的两名玩家，每人必须只有一条记录。
    players = {}
    for pid in (1, 2):
        matches = []
        for record in records:
            if record["frame"] == game_loop and record["pid"] == pid:
                matches.append(record)

        if len(matches) != 1:
            raise ValueError(f"采样点 {game_loop} 的玩家 {pid} 记录缺失或重复，请换一个采样点。")

        players[pid] = {}
        for field in FIELDS:
            players[pid][field] = matches[0].get(field)

    # 3. 用Python计算玩家1减玩家2，缺失项保留为空。
    difference = {}
    for field in FIELDS:
        value1 = players[1][field]
        value2 = players[2][field]
        if value1 is None or value2 is None:
            difference[field] = None
        else:
            difference[field] = value1 - value2

    # 4. 返回字典，后续可将它放入回答提示词。
    return {
        "game_loop": game_loop,
        "player1": players[1],
        "player2": players[2],
        "difference_player1_minus_player2": difference,
        "source": f"{DATA_FILE.name}，frame={game_loop}，pid=1和2",
    }

def answer_stats(question, game_loop):
    # 1. 调用已有函数查询真实数据。
    result = get_stats(game_loop)
    print("查询结果：", json.dumps(result, ensure_ascii=False))

    # 2. 读取T03的回答要求。
    prompt_file = DATA_FILE.parent.parent.parent / "prompts/rules.txt"
    rules = prompt_file.read_text(encoding="utf-8")

    # 3. 把要求、问题和数据拼在一起，再通过T02客户端调用模型。
    data_text = json.dumps(result, ensure_ascii=False, indent=2)
    prompt = f"{rules}\n\n问题：{question}\n本次数据：\n{data_text}"
    return ask(prompt)


def answer_question(question):
    # 1. 第一次调用模型，让它提取采样点编号。
    prompt = (
        "请从用户问题中提取采样点编号game_loop，只输出一个JSON对象，不要解释或使用代码块。\n"
        '输出格式：{"game_loop":编号}，其中1920仅为格式示例，请使用用户指定的编号。\n'
        "只提取用户明确给出的采样点编号，不推测编号，不把分钟或秒直接当作编号。\n"
        "如果用户没有明确给出采样点编号，将game_loop设为null。\n"
        f"用户问题：{question}"
    )
    request_text = ask(prompt)
    print("模型提取的查询参数：", request_text)

    # 2. 解析JSON，读取采样点编号。
    try:
        request = json.loads(request_text)
    except json.JSONDecodeError as error:
        raise ValueError("模型返回的查询请求不是有效JSON。") from error

    if not isinstance(request, dict):
        raise ValueError("模型需要返回包含game_loop的JSON对象。")

    game_loop = request.get("game_loop")
    if type(game_loop) is not int or game_loop < 0:
        raise ValueError("请在问题中明确指定采样点编号，例如1920。")

    # 3. 复用已有流程：真实查询、拼接证据、第二次调用模型回答。
    return answer_stats(question, game_loop)


if __name__ == "__main__":
    question = "1920采样点双方当前矿分别是多少，谁更多，多多少？"
    try:
        answer = answer_question(question)
        print("最终回答：", answer)
    except ValueError as error:
        print("查询失败：", error)
