import config.Tracks, pathlib
path = pathlib.Path(config.Tracks.__file__)
print('module file', config.Tracks.__file__)
lines = path.read_text().splitlines()
for i, line in enumerate(lines[300:390], start=301):
    print(f'{i}: {line!r}')
print('---')
for name in ['Italy', 'Monaco', 'Bahrain', 'Australia']:
    t = config.Tracks.TRACKS.get(name)
    print(name, 'exists', t is not None)
    if t is not None:
        print('has reccommended_pit_stops', 'reccommended_pit_stops' in t)
        if 'reccommended_pit_stops' in t:
            print('value', t['reccommended_pit_stops'])
        print('repr keys:', sorted(t.keys()))
