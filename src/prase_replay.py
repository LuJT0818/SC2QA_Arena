import json
import os
import sc2reader
import sc2reader.events.tracker as tracker
from collections import defaultdict

# ==========================================
# 1. 配置与常量
# ==========================================
DEFAULT_REPLAY_PATH = 'data/raw/SvS_G2.SC2Replay'
DEFAULT_TARGET_SECONDS = [120, 300, 480]
DEFAULT_PIDS = [1, 2]
STATS_FIELDS = ["minerals_current", "vespene_current", 
                "workers_active_count", "food_used", "food_made"]


# ==========================================
# 2. 工具函数
# ==========================================
def safe_extract_event_data(event):
    """
    安全提取事件数据。
    因为 sc2reader 的 Event 类使用了 __slots__，没有 __dict__，
    直接使用 vars(event) 会报错，这里做了兼容处理。
    """
    data = {}
    # 提取普通属性
    for key in STATS_FIELDS:
        val = getattr(event, key, None)
        if val is not None:
            data[key] = val
            
    # 提取 data 字典（如果存在）
    if hasattr(event, 'data') and isinstance(event.data, dict):
        data.update(event.data)
        
    return data


def save_to_json(data, filepath):
    """将数据保存为 JSON 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"已保存文件: {filepath}")


# ==========================================
# 3. 核心逻辑
# ==========================================
def load_and_extract_info(replay_path):
    """加载回放并打印基础信息"""
    replay = sc2reader.load_replay(replay_path, load_map=True)
    
    print(f"地图: {replay.map_name}")
    print(f"时长(秒): {replay.length}")
    print(f"游戏类型: {replay.game_type}")
    print(f"资料片: {replay.expansion}")
    
    for player in replay.players:
        print(f"PID: {player.pid}, 名称: {player.name}, 种族: {player.play_race}, "
              f"队伍: {player.team_id}, 结果: {player.result}")
              
    return replay


def group_stats_events(replay):
    """从回放中过滤出 PlayerStatsEvent 并按 PID 分组"""
    stats_events = [e for e in replay.events if isinstance(e, tracker.PlayerStatsEvent)]
    by_player = defaultdict(list)
    for e in stats_events:
        by_player[e.pid].append(e)
    return by_player


def find_candidates(by_player, pid, sec, tolerance=1):
    """查找某个玩家在某个时间点附近的候选事件"""
    return [e for e in by_player.get(pid, []) if abs(e.second - sec) < tolerance]


def build_organized_records(by_player, target_seconds, pids):
    """构建整理后的六条记录（缺失值保留为 None）"""
    records = []
    for pid in pids:
        for sec in target_seconds:
            candidates = find_candidates(by_player, pid, sec)
            if candidates:
                e = candidates[0] # 默认取第一条
                record = {"pid": pid, "second": e.second, "frame": e.frame}
                for field in STATS_FIELDS:
                    record[field] = getattr(e, field, None)
                records.append(record)
            else:
                # 缺失值保留为空
                record = {"pid": pid, "second": sec, "frame": None}
                for field in STATS_FIELDS:
                    record[field] = None
                records.append(record)
    return records


def build_raw_events_records(by_player, target_seconds, pids):
    """保存所选事件的原始统计值（包含所有候选事件）"""
    raw_events = []
    for pid in pids:
        for sec in target_seconds:
            for e in find_candidates(by_player, pid, sec):
                raw_events.append({
                    "pid": e.pid,
                    "second": e.second,
                    "frame": e.frame,
                    "data": safe_extract_event_data(e)
                })
    return raw_events


def detect_stat_conflicts(by_player, target_seconds, pids):
    """检测同一玩家同一时刻出现的多条不同记录（冲突）"""
    conflicts = []
    for pid in pids:
        for sec in target_seconds:
            candidates = find_candidates(by_player, pid, sec)
            if len(candidates) > 1:
                values = set()
                for e in candidates:
                    vals = tuple(getattr(e, f, None) for f in 
                                 ["minerals_current", "workers_active_count", "food_used"])
                    values.add(vals)
                
                # 如果同一时刻的统计值不一致，则标记为冲突
                if len(values) > 1:
                    conflicts.append({
                        "pid": pid, 
                        "second": sec,
                        "count": len(candidates),
                        "reason": "同一时刻多条事件且统计值不同"
                    })
    return conflicts


# ==========================================
# 4. 主流程
# ==========================================
def run_analysis(replay_path=DEFAULT_REPLAY_PATH, 
                 target_seconds=None, 
                 pids=None,
                 output_dir="data/processed"):
    """执行完整的回放分析流程"""
    target_seconds = target_seconds or DEFAULT_TARGET_SECONDS
    pids = pids or DEFAULT_PIDS

    print("--- 1. 读取回放与玩家信息 ---")
    replay = load_and_extract_info(replay_path)
    
    print("\n--- 2. 提取并分组 Stats 事件 ---")
    by_player = group_stats_events(replay)
    print(f"提取到 {sum(len(v) for v in by_player.values())} 条 PlayerStatsEvent")
    
    print("\n--- 3. 整理记录与保存 ---")
    records = build_organized_records(by_player, target_seconds, pids)
    raw_events = build_raw_events_records(by_player, target_seconds, pids)
    
    save_to_json(raw_events, os.path.join(output_dir, "raw_stats_events.json"))
    save_to_json(records, os.path.join(output_dir, "organized_records.json"))
    
    print("\n--- 4. 冲突检测 ---")
    conflicts = detect_stat_conflicts(by_player, target_seconds, pids)
    if conflicts:
        print(f"⚠️ 发现 {len(conflicts)} 个冲突:")
        save_to_json(conflicts, os.path.join(output_dir, "conflicts.json"))
    else:
        print("✅ 未发现冲突数据。")

# 测试入口
if __name__ == "__main__":
    run_analysis()