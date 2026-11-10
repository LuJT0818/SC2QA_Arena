import json
from pathlib import Path

from answer import generate_answer
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
    result = get_stats(game_loop)
    print("查询结果：", json.dumps(result, ensure_ascii=False))
    return generate_answer(question, stats=result)


def extract_game_loop(question, allow_missing=False):
    # 1. 第一次调用模型，让它提取采样点编号。
    prompt = (
        "任务：从最后的用户问题中原样提取采样点编号，填入game_loop。\n"
        "采样点编号可以写成“1920采样点”“采样点1920”“game_loop=1920”或“第1920帧”。\n"
        "出现明确编号时，输出该整数，不检查这个编号是否有数据。\n"
        "仅当没有明确编号时输出null。玩家编号、分钟和秒不属于采样点编号，不进行时间换算。\n"
        "只输出一个合法JSON对象，不输出解释或代码块。\n\n"
        "示例一\n问题：4800采样点双方有多少矿？\n"
        '输出：{"game_loop":4800}\n'
        "示例二\n问题：查询采样点7680的气。\n"
        '输出：{"game_loop":7680}\n'
        "示例三\n问题：game_loop=3200时的数据是多少？\n"
        '输出：{"game_loop":3200}\n'
        "示例四\n问题：玩家1有多少矿？\n"
        '输出：{"game_loop":null}\n'
        "示例五\n问题：那气呢？\n"
        '输出：{"game_loop":null}\n\n'
        f"用户问题：{question}\n输出："
    )
    request_text = ask(prompt)
    print("模型提取的查询参数：", request_text)

    # 2. 解析JSON，读取采样点编号。
    try:
        request = json.loads(request_text)
    except json.JSONDecodeError as error:
        raise ValueError("模型返回的查询请求不是有效JSON。") from error

    if not isinstance(request, dict) or "game_loop" not in request:
        raise ValueError("模型需要返回包含game_loop的JSON对象。")

    game_loop = request.get("game_loop")
    if game_loop is None and allow_missing:
        return None
    if type(game_loop) is not int or game_loop < 0:
        raise ValueError("请在问题中明确指定采样点编号，例如1920。")

    return game_loop


def answer_question(question):
    game_loop = extract_game_loop(question)
    return answer_stats(question, game_loop)


