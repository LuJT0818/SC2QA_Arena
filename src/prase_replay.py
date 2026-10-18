import json
import sc2reader
import sc2reader.events.tracker as tracker
from collections import defaultdict

replay = sc2reader.load_replay('SvS_G2.SC2Replay', load_map = True)

# 比赛基础信息
print("地图:", replay.map_name)
print("时长(秒):", replay.length)
print("游戏类型:", replay.game_type)
print("资料片:", replay.expansion)

# 参赛玩家信息
for player in replay.players:
    print(f"PID: {player.pid}, 名称: {player.name}, 种族: {player.play_race}, "
          f"队伍: {player.team_id}, 结果: {player.result}")

stats_events = [e for e in replay.events if isinstance(e, tracker.PlayerStatsEvent)]

# 按玩家分组
by_player = defaultdict(list)
for e in stats_events:
    by_player[e.pid].append(e)

# 选择三个双方都有记录的时间点（以 second 为准）
target_seconds = [120, 300, 480]  # 示例

records = []
for pid in [1, 2]:
    for sec in target_seconds:
        candidates = [e for e in by_player[pid]
                      if abs(e.second - sec) < 1]  # 允许1秒误差
        if candidates:
            e = candidates[0]  # 若同一时刻有多条，先取第一条
            records.append({
                "pid": pid,
                "second": e.second,
                "frame": e.frame,
                "minerals_current": getattr(e, "minerals_current", None),
                "vespene_current": getattr(e, "vespene_current", None),
                "workers_active_count": getattr(e, "workers_active_count", None),
                "food_used": getattr(e, "food_used", None),
                "food_made": getattr(e, "food_made", None),
            })
        else:
            records.append({
                "pid": pid,
                "second": sec,
                "frame": None,
                "minerals_current": None,
                "vespene_current": None,
                "workers_active_count": None,
                "food_used": None,
                "food_made": None,
            })

raw_events = []
for pid in [1, 2]:
    for sec in target_seconds:
        for e in by_player[pid]:
            if abs(e.second - sec) < 1:
                raw_events.append({
                    "pid": e.pid,
                    "second": e.second,
                    "frame": e.frame,
                    "data": {k: v for k, v in vars(e).items()
                             if not k.startswith('_')}
                })

with open("raw_stats_events.json", "w") as f:
    json.dump(raw_events, f, indent=2, default=str)

with open("organized_records.json", "w") as f:
    json.dump(records, f, indent=2, default=str)