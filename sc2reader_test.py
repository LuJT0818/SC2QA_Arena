import sc2reader

replay = sc2reader.load_replay('SvS_G2.SC2Replay', load_map = True)
replay.load_map()
print(replay.map_name, replay.length)
print(type(replay))
print([x for x in dir(replay) if not x.startswith('_')])
print(vars(replay).keys())
print(replay.player)