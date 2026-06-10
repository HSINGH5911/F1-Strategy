import random
import copy
from config.Tracks import TRACKS
from config.Drivers import DRIVERS
from config.Teams import TEAMS
from models.driver import Driver
from models.team import Team
from models.race_state import RaceState
from simulation.race_simulator import simulate_race

teams = {
    name: Team(name, base_pace=data['base_pace'], pit_stop_avg=data['pit_stop_avg'], reliability=data.get('reliability',1.0), tire_management=data.get('tire_management',1.0))
    for name, data in TEAMS.items()
}
drivers = []
for code, data in DRIVERS.items():
    d = Driver(code, teams[data['team']])
    d.skill = data['skill']
    d.qualifying = data['qualifying']
    d.racecraft = data['racecraft']
    d.tire_management = data['tire_management']
    d.wet_skill = data['wet_skill']
    d.consistency = data['consistency']
    d.aggression = data['aggression']
    noise = random.gauss(0, 0.8)
    d.position = max(1, d.position + round(noise))
    drivers.append(d)

for i in range(3):
    sim_drivers = copy.deepcopy(drivers)
    race_state = RaceState()
    history = {'laps': [], 'positions': {}, 'lap_times': {}, 'tire_distance': {}, 'compounds': {}, 'gaps': {}}
    simulate_race(sim_drivers, TRACKS['Italy'], race_state, history)
    print(i, sim_drivers[0].code, sim_drivers[0].race_time, sim_drivers[1].code, sim_drivers[1].race_time)
