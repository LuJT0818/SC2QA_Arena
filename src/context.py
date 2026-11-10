import re

from tools import FIELDS, extract_game_loop


FIELD_LABELS = {
    "minerals_current": "当前矿",
    "vespene_current": "当前气",
    "workers_active_count": "活跃工人数",
}


def create_session():
    return {"game_loop": None, "pid": None, "metric": None}


def clear_session(session):
    session.update(create_session())


def resolve_query(question, session):
    # 1. 采样点：本次明确提供时优先使用，否则沿用会话中的编号。
    game_loop = extract_game_loop(question, allow_missing=True)
    if game_loop is None:
        game_loop = session.get("game_loop")
    if game_loop is None:
        raise ValueError("请先提供采样点编号，例如1920。")

    # 2. 玩家：优先使用本次明确指定的玩家，再处理“另一方”和“他”。
    player_ids = []
    for number in re.findall(r"玩家\s*([0-9一二]+)", question):
        mapping = {"1": 1, "2": 2, "一": 1, "二": 2}
        if number not in mapping:
            raise ValueError("当前只支持玩家1和玩家2。")
        player_ids.append(mapping[number])

    if any(word in question for word in ("双方", "两人", "他们")) or len(set(player_ids)) == 2:
        pid = "both"
    elif player_ids:
        pid = player_ids[0]
    elif any(word in question for word in ("另一方", "另一个玩家", "对方")):
        previous_pid = session.get("pid")
        if previous_pid not in (1, 2):
            raise ValueError("请先明确一名玩家，才能确定另一方。")
        pid = 3 - previous_pid
    elif any(word in question for word in ("他", "她", "该玩家", "同一方")):
        pid = session.get("pid")
        if pid not in (1, 2):
            raise ValueError("请明确指的是玩家1还是玩家2。")
    else:
        pid = session.get("pid") or "both"

    # 3. 指标：本次提到的指标优先，否则沿用会话中的指标列表。
    keywords = {
        "minerals_current": ("矿", "minerals_current"),
        "vespene_current": ("气", "瓦斯", "vespene_current"),
        "workers_active_count": ("工人", "workers_active_count"),
    }
    metrics = []
    for field, words in keywords.items():
        if any(word in question for word in words):
            metrics.append(field)

    if any(word in question for word in ("全部指标", "所有指标", "三项", "数据")) and not metrics:
        metrics = FIELDS.copy()
    if not metrics:
        metrics = session.get("metric")
    if not metrics:
        raise ValueError("请指定要查矿、气还是活跃工人数。")
    return game_loop, pid, metrics.copy()


def prepare_context(input_data):
    question = input_data["question"]
    session = input_data["session"]
    game_loop, pid, metrics = resolve_query(question, session)

    player_text = "双方" if pid == "both" else f"玩家{pid}"
    metric_text = "、".join(FIELD_LABELS[field] for field in metrics)
    
    resolved_question = (
        f"本次查询game_loop={game_loop}，查询对象为{player_text}，指标为{metric_text}。\n"
        f"请按上述已补齐的条件回答。用户原问题：{question}"
    )
    print("补齐后的问题", resolved_question)
    return {
        "question": resolved_question, "game_loop": game_loop,
        "pid": pid, "metric": metrics, "session": session,
    }


def apply_context(state):
    # 前一步查询成功后，保存本轮条件。
    state["session"]["game_loop"] = state["game_loop"]
    state["session"]["pid"] = state["pid"]
    state["session"]["metric"] = state["metric"].copy()

    # 按当前玩家和指标筛选交给回答模型的证据。
    stats = {"game_loop": state["game_loop"], "source": state["stats"]["source"]}
    player_ids = [1, 2] if state["pid"] == "both" else [state["pid"]]
    for pid in player_ids:
        player_key = f"player{pid}"
        stats[player_key] = {}
        for field in state["metric"]:
            stats[player_key][field] = state["stats"][player_key][field]
    if state["pid"] == "both":
        difference = {}
        for field in state["metric"]:
            difference[field] = state["stats"]["difference_player1_minus_player2"][field]
        stats["difference_player1_minus_player2"] = difference
    state["stats"] = stats
    return state


