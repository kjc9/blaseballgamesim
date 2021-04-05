from decimal import Decimal
from os import path
from typing import Any, Dict
import os
import json
import threading
import time

from src.common import get_stlats_for_season, blood_name_map, PlayerBuff, enabled_player_buffs, convert_keys
from src.common import BlaseballStatistics as Stats
from src.common import ForbiddenKnowledge as FK
from src.common import BloodType, Team, team_id_map, blood_id_map, fk_key, Weather, team_name_map
from src.stadium import Stadium
from src.team_state import TeamState, DEF_ID
from src.game_state import GameState, InningHalf

lineups_by_team: Dict[str, Dict[int, str]] = {}
stlats_by_team: Dict[str, Dict[str, Dict[FK, float]]] = {}
buffs_by_team: Dict[str, Dict[str, Dict[PlayerBuff, int]]] = {}
game_stats_by_team: Dict[str, Dict[str, Dict[Stats, float]]] = {}
segmented_stats_by_team: Dict[str, Dict[int, Dict[str, Dict[Stats, float]]]] = {}
names_by_team: Dict[str, Dict[str, str]] = {}
blood_by_team: Dict[str, Dict[str, BloodType]] = {}
team_states: Dict[Team, TeamState] = {}
rotations_by_team: Dict[str, Dict[int, str]] = {}
default_stadium: Stadium = Stadium(
    "team_id",
    "stadium_id",
    "stadium_name",
    0.5,
    0.5,
    0.5,
    0.5,
    0.5,
    0.5,
    0.5,
)

day_lineup = {}
day_stlats = {}
day_buffs = {}
day_names = {}
day_blood = {}
day_rotations = {}
stadiums = {}


def process_game(game: GameState, day: int, home_team_name: str, away_team_name: str):
    try:
        home_wins, away_wins = 0, 0
        for x in range(0, iterations):
            home_win = game.simulate_game()
            if home_win:
                home_wins += 1
            else:
                away_wins += 1
            game.reset_game_state()
        print(f"{home_team_name}: {home_wins} ({home_wins / iterations}) "
              f"{away_team_name}: {away_wins} ({away_wins / iterations})")
    except KeyError:
        print(f"failed to sim day {day} {home_team_name} vs {away_team_name} game")


def setup_season(season:int, stats_segment_size:int):
    with open(os.path.join('..', 'season_sim', 'season_data', f"season{season + 1}.json"), 'r', encoding='utf8') as json_file:
        raw_season_data = json.load(json_file)
        failed = 0
        cur_day = 0
        threads = []
        for game in raw_season_data:
            home_team_name = game["homeTeamName"]
            away_team_name = game["awayTeamName"]
            game_id = game["id"]
            day = int(game["day"])
            home_pitcher = game["homePitcher"]
            away_pitcher = game["awayPitcher"]
            home_team = game["homeTeam"]
            away_team = game["awayTeam"]
            weather = Weather(game["weather"])
            if day == 99:
                break
            try:
                if day != cur_day:
                    for curThread in threads:
                        curThread.start()
                    for curThread in threads:
                        curThread.join()
                    cur_day = day
                    print("moving on...")
                    threads = []
                print(f'Day {day}, Weather {weather.name}: {away_team_name} at {home_team_name}')
                update_team_states(season, day, home_team, home_pitcher, weather, True, stats_segment_size)
                home_team_state = team_states[team_id_map[home_team]]
                update_team_states(season, day, away_team, away_pitcher, weather, False, stats_segment_size)
                away_team_state = team_states[team_id_map[away_team]]
                game = GameState(
                    game_id=game_id,
                    season=season,
                    day=day,
                    stadium=home_team_state.stadium,
                    home_team=home_team_state,
                    away_team=away_team_state,
                    home_score=Decimal("0"),
                    away_score=Decimal("0"),
                    inning=1,
                    half=InningHalf.TOP,
                    outs=0,
                    strikes=0,
                    balls=0,
                    weather=weather
                )
                threads.append(threading.Thread(target=process_game, args=(game, day, home_team_name, away_team_name)))
            except KeyError:
                failed += 1
                print(f"failed to sim day {day} {home_team_name} vs {away_team_name} game")
        print(f"{failed} games failed to sim")


def load_all_state(season: int):
    if not path.exists(os.path.join('..', 'season_sim', 'stlats', f"s{season}_d98_stlats.json")):
        get_stlats_for_season(season)

    with open(os.path.join('..', 'season_sim', "ballparks.json"), 'r', encoding='utf8') as json_file:
        ballparks = json.load(json_file)
    for team in ballparks.keys():
        stadium = Stadium.from_ballpark_json(ballparks[team])
        stadiums[team] = stadium

    for day in range(0, 99):
        reset_daily_cache()
        filename = os.path.join('..', 'season_sim', 'stlats', f"s{season}_d{day}_stlats.json")
        with open(filename, 'r', encoding='utf8') as json_file:
            player_stlats_list = json.load(json_file)
        for player in player_stlats_list:
            if day == 6 and player["team_id"] == "105bc3ff-1320-4e37-8ef0-8d595cb95dd0":
                x = 1
            team_id = player["team_id"]
            player_id = player["player_id"]
            pos = int(player["position_id"]) + 1
            if "position_type_id" in player:
                if player["position_type_id"] == "0":
                    if team_id not in lineups_by_team:
                        lineups_by_team[team_id] = {}
                    lineups_by_team[team_id][pos] = player_id
                else:
                    if team_id not in rotations_by_team:
                        rotations_by_team[team_id] = {}
                    rotations_by_team[team_id][pos] = player_id
            else:
                if player["position_type"] == "BATTER":
                    if team_id not in lineups_by_team:
                        lineups_by_team[team_id] = {}
                    lineups_by_team[team_id][pos] = player_id
                else:
                    if team_id not in rotations_by_team:
                        rotations_by_team[team_id] = {}
                    rotations_by_team[team_id][pos] = player_id
            if team_id not in stlats_by_team:
                stlats_by_team[team_id] = {}
            stlats_by_team[team_id][player_id] = get_stlat_dict(player)

            mods = player["modifications"]
            cur_mod_dict = {}
            if mods:
                for mod in mods:
                    if mod in enabled_player_buffs:
                        cur_mod_dict[PlayerBuff[mod]] = 1
                if player_id == "4b3e8e9b-6de1-4840-8751-b1fb45dc5605":
                    cur_mod_dict[PlayerBuff.BLASERUNNING] = 1
            if team_id not in buffs_by_team:
                buffs_by_team[team_id] = {}
            buffs_by_team[team_id][player_id] = cur_mod_dict

            if team_id not in game_stats_by_team:
                game_stats_by_team[team_id] = {}
                game_stats_by_team[team_id][DEF_ID] = {}
            game_stats_by_team[team_id][player_id] = {}

            if team_id not in segmented_stats_by_team:
                segmented_stats_by_team[team_id] = {}

            if team_id not in names_by_team:
                names_by_team[team_id] = {}
            names_by_team[team_id][player_id] = player["player_name"]

            if team_id not in blood_by_team:
                blood_by_team[team_id] = {}
            try:
                blood_by_team[team_id][player_id] = blood_id_map[int(player["blood"])]
            except ValueError:
                blood_by_team[team_id][player_id] = blood_name_map[player["blood"]]

        if day > 0 and (len(lineups_by_team) != len(day_lineup[day - 1]) or (len(rotations_by_team) != len(day_rotations[day - 1]))):
            day_lineup[day] = day_lineup[day-1]
            day_stlats[day] = day_stlats[day-1]
            day_buffs[day] = day_buffs[day-1]
            day_names[day] = day_names[day-1]
            day_blood[day] = day_blood[day-1]
            day_rotations[day] = day_rotations[day - 1]
        else:
            day_lineup[day] = lineups_by_team
            day_stlats[day] = stlats_by_team
            day_buffs[day] = buffs_by_team
            day_names[day] = names_by_team
            day_blood[day] = blood_by_team
            day_rotations[day] = rotations_by_team


def reset_daily_cache():
    global lineups_by_team
    global rotations_by_team
    global game_stats_by_team
    global segmented_stats_by_team
    global stlats_by_team
    global names_by_team
    global blood_by_team
    lineups_by_team = {}
    rotations_by_team = {}
    stlats_by_team = {}
    names_by_team = {}
    blood_by_team = {}


def get_stlat_dict(player: Dict[str, Any]) -> Dict[FK, float]:
    ret_val: Dict[FK, float] = {}
    for k in fk_key:
        str_name = fk_key[k]
        ret_val[k] = float(player[str_name])
    return ret_val


def update_team_states(season: int, day: int, team: str, starting_pitcher: str,
                       weather: Weather, is_home: bool, stats_segment_size: int):
    if team_id_map[team] not in team_states:
        if team in stadiums:
            stadium = stadiums[team]
        else:
            stadium = default_stadium
        team_states[team_id_map[team]] = TeamState(
            team_id=team,
            season=season,
            day=day,
            stadium=stadium,
            weather=weather,
            is_home=is_home,
            num_bases=4,
            balls_for_walk=4,
            strikes_for_out=3,
            outs_for_inning=3,
            lineup=day_lineup[day][team],
            rotation=day_rotations[day][team],
            starting_pitcher=starting_pitcher,
            stlats=day_stlats[day][team],
            buffs=day_buffs[day][team],
            game_stats=game_stats_by_team[team],
            segmented_stats=segmented_stats_by_team[team],
            blood=day_blood[day][team],
            player_names=day_names[day][team],
            cur_batter_pos=1,
            segment_size=stats_segment_size,
        )
    else:
        team_states[team_id_map[team]].day = day
        team_states[team_id_map[team]].weather = weather
        team_states[team_id_map[team]].is_home = is_home
        # lineup_changed = False
        # if team_states[team_id_map[team]].lineup != day_lineup[day][team]:
        #     lineup_changed = True
        team_states[team_id_map[team]].lineup = day_lineup[day][team]
        team_states[team_id_map[team]].rotation = day_rotations[day][team]
        team_states[team_id_map[team]].starting_pitcher = starting_pitcher
        team_states[team_id_map[team]].stlats = day_stlats[day][team]
        team_states[team_id_map[team]].player_buffs = day_buffs[day][team]
        team_states[team_id_map[team]].blood = day_blood[day][team]
        #team_states[team_id_map[team]].player_names = day_names[day][team]
        team_states[team_id_map[team]].update_player_names(day_names[day][team])
        team_states[team_id_map[team]].reset_team_state(lineup_changed=True)


def print_leaders():
    strikeouts = []
    hrs = []
    avg = []
    all_segmented_stats = {}
    for cur_team in team_states.keys():
        for player in team_states[cur_team].game_stats.keys():
            if Stats.PITCHER_STRIKEOUTS in team_states[cur_team].game_stats[player]:
                player_name = team_states[cur_team].player_names[player]
                value = team_states[cur_team].game_stats[player][Stats.PITCHER_STRIKEOUTS] / float(iterations)
                strikeouts.append((value, player_name))
            if Stats.BATTER_HRS in team_states[cur_team].game_stats[player]:
                player_name = team_states[cur_team].player_names[player]
                value = team_states[cur_team].game_stats[player][Stats.BATTER_HRS] / float(iterations)
                hrs.append((value, player_name))
            if Stats.BATTER_HITS in team_states[cur_team].game_stats[player]:
                player_name = team_states[cur_team].player_names[player]
                hits = team_states[cur_team].game_stats[player][Stats.BATTER_HITS]
                abs = team_states[cur_team].game_stats[player][Stats.BATTER_AT_BATS]
                value = hits / abs
                avg.append((value, player_name))
        for day, stats in team_states[cur_team].segmented_stats.items():
            if day not in all_segmented_stats:
                all_segmented_stats[day] = {}
            for player_id, player_stats in stats.items():
                if player_id not in team_states[cur_team].player_names:
                    continue
                all_segmented_stats[day][player_id] = {"name": team_states[cur_team].player_names[player_id]}
                for stat in [Stats.PITCHER_STRIKEOUTS, Stats.BATTER_HITS, Stats.BATTER_HRS, Stats.STOLEN_BASES]:
                    if stat in player_stats:
                        all_segmented_stats[day][player_id][stat] = player_stats[stat] / float(iterations)
    filename = os.path.join("..", "season_sim", "results", f"{round(time.time())}_all_segmented_stats.json")
    with open(filename, 'w') as f:
        json.dump(convert_keys(all_segmented_stats), f)

    print("STRIKEOUTS")
    count = 0
    for value, name in reversed(sorted(strikeouts)):
        if count == 10:
            break
        print(f'\t{name}: {value}')
        count += 1
    print("HRS")
    count = 0
    for value, name in reversed(sorted(hrs)):
        if count == 10:
            break
        print(f'\t{name}: {value}')
        count += 1
    print("avg")
    count = 0
    for value, name in reversed(sorted(avg)):
        if count == 10:
            break
        print(f'\t{name}: {value:.3f}')
        count += 1

    with open(os.path.join('..', 'season_sim', 'results', "1616749629_top_hrs.txt"), 'w',
              encoding='utf8') as json_file:
        json_file.write(top_hrs)
    with open(os.path.join('..', 'season_sim', 'results', "1616749629_top_sbs.txt"), 'w',
              encoding='utf8') as json_file:
        json_file.write(top_sbs)

iterations = 10
season = 13
stats_segment_size = 3
#print_info()
load_all_state(season)
setup_season(season, stats_segment_size)
print_leaders()
