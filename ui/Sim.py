import math
import os
import sys
import tkinter as tk
import random
import threading
import datetime
import json

from matplotlib import container

# Ensure the project root is on sys.path when running ui/Sim.py directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tkinter import ttk, messagebox

from models.driver import Driver
from models.team import Team
from models.race_state import RaceState
from config.Tracks import TRACKS
from config.Teams import TEAMS
from config.Drivers import DRIVERS
from config.Tires import TIRES
from config.General import SIMULATION_RUNS
from simulation.race_simulator import simulate_race, process_pit_stops, get_num_rec_pit_stops, get_pit_window

from ui.dashboard import (
    print_standings,
    print_tires,
    print_strategy,
    plot_positions,
    plot_lap_times,
)


# ─────────────────────────────────────────────
#  Grid factory
# ─────────────────────────────────────────────
def generate_starting_grid(drivers):
    """Generate a randomized starting grid of drivers based on the DRIVERS config. 
        Each driver is assigned a position, team, and initial tire compound."""
    
    for driver in drivers:
        qual_score = (
            driver.qualifying * 100
            + driver.skill * 50
            + random.gauss(0, 3)
        )

        driver.qualifying_score = qual_score

    drivers.sort(
        key=lambda d: d.qualifying_score,
        reverse=True
    )
    
    return drivers

def create_grid():
    """Create the initial grid of drivers for the race. This function initializes the teams and 
        drivers based on the configuration files, assigns them to their respective teams, 
        and generates the starting grid positions based on their qualifying scores."""
    
    teams = {
        name: Team(
            name,
            base_pace=data["base_pace"],
            pit_stop_avg=data["pit_stop_avg"],
            reliability=data.get("reliability", 1.0),
            tire_management=data.get("tire_management", 1.0),
        )
        for name, data in TEAMS.items()
    }

    drivers = []

    for code, data in DRIVERS.items():
        driver = Driver(code, teams[data["team"]])
        driver.skill = data["skill"]
        driver.qualifying = data["qualifying"]
        driver.racecraft = data["racecraft"]
        driver.tire_management = data["tire_management"]
        driver.wet_skill = data["wet_skill"]
        driver.consistency = data["consistency"]
        driver.aggression = data["aggression"]
        # give drivers slightly different starting compounds and wear behavior
        driver.current_compound = random.choices(["SOFT", "MEDIUM", "HARD"], weights=[0.2, 0.6, 0.2])[0]
        # wear_factor: >1 means faster wear, <1 means better preservation
        driver.wear_factor = max(0.75, min(1.3, 1.0 + (1.0 - driver.tire_management) * 0.6 + random.gauss(0, 0.03)))
        drivers.append(driver)

    generate_starting_grid(drivers)

    return drivers


def race_laps(track):
    """Calculate the number of laps for a given track."""

    from config.General import DEFAULT_RACE_DISTANCE_KM, MONACO_RACE_DISTANCE_KM
    race_distance = (
        MONACO_RACE_DISTANCE_KM
        if track.get("name") == "Monaco"
        else DEFAULT_RACE_DISTANCE_KM
    )
    return track.get("laps", math.ceil(race_distance / track["length_km"]))


# ─────────────────────────────────────────────
#  Strategy planner — applied before sim runs
# ─────────────────────────────────────────────
class StrategyPlan:
    """
    Holds a list of pit stops: [(lap, new_compound), ...]
    The simulator's process_pit_stops fires automatically when
    tire_distance >= max_distance.  This plan *overrides* that
    by pre-scheduling stops and injecting them during the race loop.
    """

    def __init__(self):
        self.stops: list[tuple[int, str]] = []   # (lap_number, compound)

    def add_stop(self, lap: int, compound: str):
        self.stops.append((lap, compound))
        self.stops.sort(key=lambda x: x[0])

    def remove_stop(self, index: int):
        if 0 <= index < len(self.stops):
            self.stops.pop(index)

    def clear(self):
        self.stops.clear()

    def next_stop_for_lap(self, lap: int):
        """Return (compound) if a stop is scheduled this lap, else None."""
        for stop_lap, compound in self.stops:
            if stop_lap == lap:
                return compound
        return None


# ─────────────────────────────────────────────
#  Patched simulate_race that respects a plan
# ─────────────────────────────────────────────
def simulate_race_with_strategy(drivers, track, race_state, history, plan: StrategyPlan, player_code: str):
    """
    Wraps simulate_race but intercepts pit stops for the player driver
    according to the StrategyPlan instead of the automatic degradation trigger.
    """
    from simulation.race_simulator import (
        simulate_lap, update_positions, process_overtakes, update_weather, record_history
    )
    from simulation.pit_stop_model import perform_stop

    total_laps = race_laps(track)
    player_driver = next((d for d in drivers if d.code == player_code), None)
    required_stops = track["reccommended_pit_stops"]
    
    while race_state.current_lap <= total_laps:
        update_weather(race_state)
        simulate_lap(drivers, track, race_state, total_laps)
        update_positions(drivers)
        process_overtakes(drivers, track)

        # ── Pit stops ──────────────────────────────────────────
        # Player uses the StrategyPlan; AI drivers use the full pit logic
        if player_driver and plan.stops:
            # Scheduled stop
            scheduled_compound = plan.next_stop_for_lap(race_state.current_lap)
            if scheduled_compound and player_driver.laps_since_last_pit > 10:
                perform_stop(player_driver, track, scheduled_compound, race_state)

            # Emergency wet/dry swap regardless of plan
            wet = race_state.track_wetness
            current = player_driver.current_compound
            if wet > 0.6 and current in ("SOFT", "MEDIUM", "HARD"):
                compound = "WET" if wet > 0.85 else "INTERMEDIATE"
                perform_stop(player_driver, track, compound, race_state)
            elif wet < 0.2 and current in ("WET", "INTERMEDIATE"):
                perform_stop(player_driver, track, "MEDIUM", race_state)

        process_pit_stops(drivers, track, race_state, skip_codes={player_code})
        record_history(history, race_state, drivers)
        race_state.current_lap += 1

    return drivers


# ─────────────────────────────────────────────
#  Console runner (kept for headless use)
# ─────────────────────────────────────────────
def run_console_simulation(track_name="Italy", player_code=None, plan: StrategyPlan = None):
    """Run a full race simulation in the console, optionally with a player driver and strategy plan."""

    track = TRACKS[track_name]
    race_state = RaceState()
    drivers = create_grid()

    history = {
        "laps": [], "positions": {}, "lap_times": {},
        "tire_distance": {}, "compounds": {}, "gaps": {}
    }

    if plan and player_code:
        (drivers, track, race_state, history, plan, player_code)
    else:
        simulate_race(drivers, track, race_state, history)

    print_standings(drivers)
    print_tires(drivers)
    print_strategy(drivers)
    plot_positions(history)
    plot_lap_times(history)

    return drivers, history


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────

COMPOUND_COLORS = {
    "SOFT":         "#e74c3c",
    "MEDIUM":       "#f39c12",
    "HARD":         "#bdc3c7",
    "INTERMEDIATE": "#2ecc71",
    "WET":          "#3498db",
}

COMPOUND_SHORT = {
    "SOFT": "S", "MEDIUM": "M", "HARD": "H",
    "INTERMEDIATE": "I", "WET": "W",
}

class StrategyGUI(tk.Tk):
    def __init__(self):
        """Initialize the main application window, set up the title, size, and background color."""

        super().__init__()
        self.title("F1 Race Strategy Planner")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")
        self.geometry("1400x900")

        self.plan = StrategyPlan()
        self._stop_rows: list[dict] = []   # tracks widgets per stop row

        self._build_ui()
        self._refresh_laps()

    # ── Layout ────────────────────────────────

    def _build_ui(self):
        """Set up the main layout of the application, including the top bar, main columns, and
           sections for race setup, strategy planning, and results display."""
        
        # Top bar
        topbar = tk.Frame(self, bg="#16213e", pady=8)
        topbar.pack(fill="x")
        tk.Label(topbar, text="F1 Strategy Planner", font=("Helvetica", 16, "bold"),
                 fg="white", bg="#16213e").pack(side="left", padx=16)

        # Main columns
        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(main, bg="#1a1a2e", width=420)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side="left", fill="both", expand=True)

        self._build_setup_panel(left)
        self.build_weather_panel(left)
        self._build_strategy_panel(left)
        self._build_results_panel(right)

    def _section(self, parent, title):
        """Helper to create a styled section frame with a title."""

        frame = tk.LabelFrame(parent, text=title, fg="#aaaaaa",
                              bg="#16213e", bd=1, relief="flat",
                              font=("Helvetica", 9, "bold"), padx=10, pady=8)
        frame.pack(fill="x", pady=(0, 10))
        return frame

    # ── Setup panel ───────────────────────────
    def _build_setup_panel(self, parent):
        """Create the race setup section, allowing the user to select the track, player driver, 
            starting compound, and grid position."""
        
        f = self._section(parent, "Race Setup")

        # Track
        tk.Label(f, text="Track", fg="#aaaaaa", bg="#16213e", font=("Helvetica", 9)).grid(
            row=0, column=0, sticky="w", pady=2)
        self.track_var = tk.StringVar(value="Italy")
        track_cb = ttk.Combobox(f, textvariable=self.track_var,
                                values=sorted(TRACKS.keys()), state="readonly", width=22)
        track_cb.grid(row=0, column=1, padx=(8, 0), pady=2)
        track_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_laps())

        # Player driver
        tk.Label(f, text="Driver", fg="#aaaaaa", bg="#16213e", font=("Helvetica", 9)).grid(
            row=1, column=0, sticky="w", pady=2)
        self.driver_var = tk.StringVar(value=list(DRIVERS.keys())[0])
        ttk.Combobox(f, textvariable=self.driver_var,
                     values=list(DRIVERS.keys()), state="readonly", width=22).grid(
            row=1, column=1, padx=(8, 0), pady=2)

        # Starting compound
        tk.Label(f, text="Start compound", fg="#aaaaaa", bg="#16213e", font=("Helvetica", 9)).grid(
            row=2, column=0, sticky="w", pady=2)
        self.start_compound_var = tk.StringVar(value="MEDIUM")
        ttk.Combobox(f, textvariable=self.start_compound_var,
                     values=list(TIRES.keys()), state="readonly", width=22).grid(
            row=2, column=1, padx=(8, 0), pady=2)

        # Grid position (used as fallback default only; grid window overrides)
        tk.Label(f, text="Grid position", fg="#aaaaaa", bg="#16213e", font=("Helvetica", 9)).grid(
            row=3, column=0, sticky="w", pady=2)
        self.grid_pos_var = tk.IntVar(value=1)
        ttk.Spinbox(f, from_=1, to=20, textvariable=self.grid_pos_var, width=5).grid(
            row=3, column=1, sticky="w", padx=(8, 0), pady=2)

        # Lap count display
        self.laps_label = tk.Label(f, text="", fg="#00d4ff", bg="#16213e", font=("Helvetica", 9))
        self.laps_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

    
    def build_weather_panel(self, parent):
        """Fetch and display real historical weather for the selected track and a user-specified date."""

        f = self._section(parent, "Track Weather")

        # Date entry
        tk.Label(f, text="Race date (YYYY-MM-DD)", fg="#aaaaaa", bg="#16213e",
                font=("Helvetica", 9)).grid(row=0, column=0, sticky="w", pady=2)
        self.weather_date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        tk.Entry(f, textvariable=self.weather_date_var, width=14,
                bg="#0d0d1a", fg="white", insertbackground="white",
                relief="flat").grid(row=0, column=1, padx=(8, 0), pady=2)

        tk.Button(f, text="Fetch Weather", command=self._fetch_weather,
                bg="#0f3460", fg="white", relief="flat", cursor="hand2",
                font=("Helvetica", 9), padx=8, pady=3).grid(
                    row=1, column=0, columnspan=2, sticky="w", pady=(6, 4))

        # Result labels
        self.weather_labels = {}
        fields = ["Date", "High", "Low", "Humidity", "Rainfall", "Condition", "Location"]
        for i, field in enumerate(fields):
            tk.Label(f, text=f"{field}:", fg="#666666", bg="#16213e",
                    font=("Helvetica", 9)).grid(row=i + 2, column=0, sticky="w", pady=1)
            lbl = tk.Label(f, text="—", fg="#00d4ff", bg="#16213e",
                        font=("Helvetica", 9, "bold"))
            lbl.grid(row=i + 2, column=1, sticky="w", padx=(8, 0), pady=1)
            self.weather_labels[field] = lbl

    def _fetch_weather(self):
        """Fetch weather data from Open-Meteo for the selected track and date."""

        track_name = self.track_var.get()
        track = TRACKS[track_name]

        lat = track.get("latitude")
        lon = track.get("longitude")
        date = self.weather_date_var.get().strip()

        if not lat or not lon:
            self.weather_labels["Condition"].config(text="No coords for track", fg="#e74c3c")
            return

        def fetch():
            try:
                import requests
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": date,
                    "end_date": date,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "hourly": "relative_humidity_2m",
                    "timezone": "auto",
                    "temperature_unit": "fahrenheit",
                    "precipitation_unit": "mm"
                }
                data = requests.get(
                    "https://archive-api.open-meteo.com/v1/archive",
                    params=params
                ).json()

                location = track.get("name", track_name)

                high = data["daily"]["temperature_2m_max"][0]
                low = data["daily"]["temperature_2m_min"][0]
                rain = data["daily"]["precipitation_sum"][0]
                humidity = data["hourly"]["relative_humidity_2m"]
                avg_humidity = sum(humidity) / len(humidity)
                condition = "WET" if rain > 0 else "DRY"
                condition_color = "#3498db" if condition == "WET" else "#f39c12"

                self.after(0, lambda: self._update_weather_labels(
                    date, high, low, avg_humidity, rain, condition, condition_color, location
                ))

            except Exception as e:
                self.after(0, lambda: self.weather_labels["Condition"].config(
                    text=f"Error: {e}", fg="#e74c3c"
                ))

        threading.Thread(target=fetch, daemon=True).start()

    def _update_weather_labels(self, date, high, low, humidity, rain, condition, condition_color, location):
        self.weather_labels["Date"].config(text=date)
        self.weather_labels["High"].config(text=f"{high:.1f}°F")
        self.weather_labels["Low"].config(text=f"{low:.1f}°F")
        self.weather_labels["Humidity"].config(text=f"{humidity:.1f}%")
        self.weather_labels["Rainfall"].config(text=f"{rain:.1f} mm")
        self.weather_labels["Condition"].config(text=condition, fg=condition_color)
        self.weather_labels["Location"].config(text=location)

    # ── Strategy panel ────────────────────────
    def _build_strategy_panel(self, parent):
        """Create the pit stop strategy section, allowing the user to plan their pit stops."""

        f = self._section(
            parent, 
            "Pit Stop Strategy"
        )

        # Header row
        hdr = tk.Frame(f, bg="#16213e")
        hdr.pack(fill="x")
        for col, w in [("Lap", 60), ("Compound", 120), ("", 30)]:
            tk.Label(hdr, text=col, fg="#777777", bg="#16213e",
                     font=("Helvetica", 8), width=w // 8).pack(side="left")

        # Scrollable stops container
        self.stops_frame = tk.Frame(f, bg="#16213e")
        self.stops_frame.pack(fill="x", pady=(4, 6))

        # Stint preview canvas
        self.canvas_frame = tk.Frame(f, bg="#16213e")
        self.canvas_frame.pack(fill="x", pady=(0, 6))
        tk.Label(self.canvas_frame, text="Stint preview", fg="#666666",
                 bg="#16213e", font=("Helvetica", 8)).pack(anchor="w")
        self.stint_canvas = tk.Canvas(self.canvas_frame, height=22, bg="#0d0d1a",
                                      highlightthickness=0)
        self.stint_canvas.pack(fill="x")

        # Buttons
        btn_row = tk.Frame(f, bg="#16213e")
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="+ Add stop", command=self._add_stop,
                  bg="#0f3460", fg="white", relief="flat", cursor="hand2",
                  font=("Helvetica", 9), padx=10, pady=4).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="Clear all", command=self._clear_stops,
                  bg="#2c2c3e", fg="#aaaaaa", relief="flat", cursor="hand2",
                  font=("Helvetica", 9), padx=10, pady=4).pack(side="left")

        # Run button
        self.run_btn = tk.Button(parent, text="▶  Simulate Race",
                                 command=self._run_threaded,
                                 bg="#e74c3c", fg="white", relief="flat",
                                 cursor="hand2", font=("Helvetica", 12, "bold"),
                                 pady=10)
        self.run_btn.pack(fill="x", pady=(4, 0))

        # Run Monte Carlo Button
        self.monte_carlo = tk.Button(
            parent, text="▶  Simulate x1000", command=self._run_monte_carlo_threaded,
            bg="#e74c3c", fg="white", relief="flat",
            cursor="hand2", font=("Helvetica", 12, "bold"),
            pady=10)
        self.monte_carlo.pack(fill="x", pady=(4, 0))
        

        self.status_label = tk.Label(parent, text="", fg="#00d4ff",
                                     bg="#1a1a2e", font=("Helvetica", 9))
        self.status_label.pack(anchor="w", pady=(4, 0))

    def _build_results_panel(self, parent):
        """Create the results display section, which uses a notebook to show the standings, 
            strategy, and race info."""
        
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)

        self.tab_standings = tk.Frame(self.notebook, bg="#1a1a2e")
        self.tab_strategy  = tk.Frame(self.notebook, bg="#1a1a2e")
        self.tab_weather   = tk.Frame(self.notebook, bg="#1a1a2e")

        self.notebook.add(self.tab_standings, text="  Standings  ")
        self.notebook.add(self.tab_strategy,  text="  Strategy   ")
        self.notebook.add(self.tab_weather,   text="  Race Info  ")

        self._build_standings_tab()
        self._build_strategy_tab()
        self._build_info_tab()

    def _build_standings_tab(self):
        """Set up the standings tab with a Treeview to display the race results, 
            including position, driver, team"""
        
        cols = ("Pos", "Driver", "Team", "Race Time", "Gap", "Fastest Lap", "Pits", "Final Compound")
        self.standings_tree = ttk.Treeview(self.tab_standings, columns=cols,
                                           show="headings", height=20)
        widths = [40, 70, 120, 100, 90, 100, 50, 130]
        for col, w in zip(cols, widths):
            self.standings_tree.heading(col, text=col)
            self.standings_tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(self.tab_standings, orient="vertical",
                            command=self.standings_tree.yview)
        self.standings_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.standings_tree.pack(fill="both", expand=True)

        self.standings_tree.tag_configure("player", foreground="#00d4ff", font=("Helvetica", 10, "bold"))
        self.standings_tree.tag_configure("podium", foreground="#f1c40f")
        self.standings_tree.tag_configure("even",   background="#141428", foreground="#cccccc")
        self.standings_tree.tag_configure("odd",    background="#1a1a2e", foreground="#cccccc")
        
    def _build_strategy_tab(self):
        """Set up the strategy tab, which currently just has a canvas to visualize the 
            planned stints and compounds."""
        
        self.strategy_canvas = tk.Canvas(self.tab_strategy, bg="#1a1a2e",
                                         highlightthickness=0)
        vsb = ttk.Scrollbar(self.tab_strategy, orient="vertical",
                            command=self.strategy_canvas.yview)
        self.strategy_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.strategy_canvas.pack(fill="both", expand=True)

    def _build_info_tab(self):
        """Set up the race info tab with a text widget to display weather and track information."""

        self.info_text = tk.Text(self.tab_weather, bg="#0d0d1a", fg="#cccccc",
                                 font=("Courier", 10), state="disabled",
                                 relief="flat", padx=12, pady=10)
        self.info_text.pack(fill="both", expand=True)

    # ── Stop row management ───────────────────

    def _refresh_laps(self):
        """Update the lap count and track info display based on the selected track."""

        track = TRACKS[self.track_var.get()]
        laps = race_laps(track)
        pit_stop_amount = track["reccommended_pit_stops"]

        if pit_stop_amount == 1.5:
            pit_text = "1-2"
        else:
            pit_text = pit_stop_amount

        self.laps_label.config(text=f"{laps} laps · {track['length_km']} km · pit Δ {track['pit_delta']}s · rec. stops: {pit_text}")
        self._redraw_stint_preview()

    def _add_stop(self):
        """Add a new pit stop row to the strategy plan, allowing the user to specify the lap and 
            compound for the stop."""
        
        track = TRACKS[self.track_var.get()]
        total = race_laps(track)
        drivers = create_grid()
        driver = next((d for d in drivers if d.code == self.driver_var.get()), None)

        pit_stop_amount = get_num_rec_pit_stops(track, driver)
        pit_window = get_pit_window(track, driver)

        for i in range(pit_stop_amount):
            self._add_stop_row(pit_window[i], "HARD")
        

    def _add_stop_row(self, lap: int, compound: str):
        """Helper to add a single stop row with the given lap and compound defaults."""
        
        track = TRACKS[self.track_var.get()]
        total = race_laps(track)

        row_frame = tk.Frame(self.stops_frame, bg="#16213e")
        row_frame.pack(fill="x", pady=2)

        lap_var = tk.IntVar(value=lap)
        compound_var = tk.StringVar(value=compound)

        lap_spin = ttk.Spinbox(row_frame, from_=1, to=total - 1,
                               textvariable=lap_var, width=6)
        lap_spin.pack(side="left", padx=(0, 6))

        compound_cb = ttk.Combobox(row_frame, textvariable=compound_var,
                                   values=list(TIRES.keys()), state="readonly", width=14)
        compound_cb.pack(side="left", padx=(0, 6))

        def remove(rf=row_frame, lv=lap_var, cv=compound_var):
            rf.destroy()
            self._stop_rows[:] = [r for r in self._stop_rows
                                  if r["frame"] is not rf]
            self._sync_plan()

        tk.Button(row_frame, text="✕", command=remove,
                  bg="#2c2c3e", fg="#e74c3c", relief="flat",
                  cursor="hand2", font=("Helvetica", 9), width=2).pack(side="left")

        row = {"frame": row_frame, "lap_var": lap_var, "compound_var": compound_var}
        self._stop_rows.append(row)

        lap_var.trace_add("write", lambda *_: self._sync_plan())
        compound_var.trace_add("write", lambda *_: self._sync_plan())

        self._sync_plan()

    def _clear_stops(self):
        """"Remove all planned stops from the strategy plan and clear the UI rows."""

        for row in self._stop_rows:
            row["frame"].destroy()
        self._stop_rows.clear()
        self._sync_plan()

    def _sync_plan(self):
        """Sync the StrategyPlan with the current state of the stop rows in the UI. 
            This reads the lap and compound values from each row and updates the plan 
            accordingly, then redraws the stint preview."""
        
        self.plan.clear()
        for row in self._stop_rows:
            try:
                lap = int(row["lap_var"].get())
                compound = row["compound_var"].get()
                self.plan.add_stop(lap, compound)
            except (ValueError, tk.TclError):
                pass
        self._redraw_stint_preview()

    def _redraw_stint_preview(self):
        """Redraw the stint preview canvas to visually represent the planned stints and compounds 
            based on the current StrategyPlan."""
        
        c = self.stint_canvas
        c.delete("all")
        c.update_idletasks()
        w = c.winfo_width() or 280
        h = 22

        track = TRACKS[self.track_var.get()]
        total = race_laps(track)
        start_c = self.start_compound_var.get()

        # Build stints from plan
        stints = []
        lap = 1
        compound = start_c
        for stop_lap, next_c in self.plan.stops:
            if stop_lap > lap:
                stints.append((lap, stop_lap - 1, compound))
            lap = stop_lap
            compound = next_c
        stints.append((lap, total, compound))

        for start, end, comp in stints:
            x1 = (start - 1) / total * w
            x2 = end / total * w
            color = COMPOUND_COLORS.get(comp, "#888888")
            c.create_rectangle(x1, 2, x2 - 1, h - 2, fill=color, outline="")
            if x2 - x1 > 18:
                c.create_text((x1 + x2) / 2, h / 2,
                              text=COMPOUND_SHORT.get(comp, comp[0]),
                              fill="white", font=("Helvetica", 8, "bold"))

    # ── Simulation ────────────────────────────

    def _run_simulation(self, grid_order: list = None):
        """Run the race simulation with the current setup and strategy plan.
           grid_order: optional list of driver codes in starting order (index 0 = P1).
           If None, falls back to the auto-generated qualifying order."""
        
        try:
            track_name = self.track_var.get()
            player_code = self.driver_var.get()

            track = TRACKS[track_name]
            race_state = RaceState()
            drivers = create_grid()

            if grid_order is not None:
                # Manual grid: sort drivers by the explicit order supplied from the grid window
                code_to_pos = {code: idx for idx, code in enumerate(grid_order)}
                drivers.sort(key=lambda d: code_to_pos.get(d.code, 99))
            else:
                # Automatic fallback: honour the grid_pos_var spinbox for the player only
                grid_pos = int(self.grid_pos_var.get())
                sorted_codes = [d.code for d in drivers]
                if player_code in sorted_codes:
                    sorted_codes.remove(player_code)
                    sorted_codes.insert(grid_pos - 1, player_code)
                drivers.sort(
                    key=lambda d: sorted_codes.index(d.code)
                    if d.code in sorted_codes else 99
                )

            for i, driver in enumerate(drivers, start=1):
                driver.position = i

            # Apply starting compound to player
            player_driver = next(d for d in drivers if d.code == player_code)
            player_driver.current_compound = self.start_compound_var.get()

            history = {
                "laps": [], "positions": {}, "lap_times": {},
                "tire_distance": {}, "compounds": {}, "gaps": {}
            }

            result_drivers = simulate_race_with_strategy(
                drivers, track, race_state, history, self.plan, player_code
            )

            self.after(0, lambda: self._show_results(result_drivers, history, track, track_name, player_code))

        except Exception as exc:
            import traceback
            err = traceback.format_exc()
            self.after(0, lambda: self._show_error(err))

    def _save_grid(self, grid_order: list):
        """Save the grid order to a file."""
        path = os.path.join(os.path.dirname(__file__), "saved_grid.json")
        with open(path, "w") as f:
            json.dump({
                "track": self.track_var.get(),
                "grid_order": grid_order
            }, f)

    def _load_grid(self):
        """Load the saved grid order from file, returns None if not found."""
        path = os.path.join(os.path.dirname(__file__), "saved_grid.json")
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        
    def _run_threaded(self):
        """Start the simulation in a separate thread to keep the UI responsive."""

        self.run_btn.config(state="disabled", text="Simulating…")
        self.status_label.config(text="")
        self._show_starting_grid()

    def _run_monte_carlo(self, runs=1000, grid_order: list = None):
        track_name = self.track_var.get()
        player_code = self.driver_var.get()
        track = TRACKS[track_name]

        all_codes = [d.code for d in create_grid()]
        position_counts = {code: [0] * len(all_codes) for code in all_codes}
        win_counts = {code: 0 for code in all_codes}
        podium_counts = {code: 0 for code in all_codes}

        for _ in range(runs):
            drivers = create_grid()
            race_state = RaceState()

            if grid_order is not None:
                code_to_pos = {code: idx for idx, code in enumerate(grid_order)}
                drivers.sort(key=lambda d: code_to_pos.get(d.code, 99))

            for i, driver in enumerate(drivers, start=1):
                driver.position = i
                driver.race_time += (i - 1) * 0.5

            player_driver = next(d for d in drivers if d.code == player_code)
            player_driver.current_compound = self.start_compound_var.get()

            history = {
                "laps": [], "positions": {}, "lap_times": {},
                "tire_distance": {}, "compounds": {}, "gaps": {}
            }

            result = simulate_race_with_strategy(
                drivers, track, race_state, history, self.plan, player_code
            )

            sorted_drivers = sorted(result, key=lambda d: d.race_time)
            for pos, driver in enumerate(sorted_drivers, start=1):
                if driver.code in position_counts:
                    position_counts[driver.code][pos - 1] += 1
                if pos == 1 and driver.code in win_counts:
                    win_counts[driver.code] += 1
                if pos <= 3 and driver.code in podium_counts:
                    podium_counts[driver.code] += 1

        self.after(0, lambda: self.monte_carlo.config(state="normal", text="▶  Simulate x1000"))
        self.after(0, lambda: self._show_monte_carlo_results(
            position_counts, win_counts, podium_counts, runs, player_code
        ))

    def _show_monte_carlo_results(self, position_counts, win_counts, podium_counts, runs, player_code):
        win = tk.Toplevel(self)
        win.title("Monte Carlo Results")
        win.configure(bg="#1a1a2e")
        win.geometry("600x500")

        tk.Label(
            win,
            text=f"Monte Carlo - {runs} simulation",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg="#1a1a2e",
        ).pack(pady=(16, 4))

        cols = ("Driver", "Win %", "Podium %", "Most Likely Pos")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="center")
        
        tree.tag_configure("player", foreground="#00d4ff", font=("Helvetica", 10, "bold"))

        sorted_codes = sorted(DRIVERS.keys(), key=lambda c: win_counts[c], reverse=True)
        for code in sorted_codes:
           win_pct = win_counts[code] / runs * 100
           podium_pct = podium_counts[code] / runs * 100
           most_likely = position_counts[code].index(max(position_counts[code])) + 1
           tags = ("player",) if code == player_code else ()
           tree.insert("", "end", values=(
               code,
               f"{win_pct:.1f}%",
               f"{podium_pct:.1f}%",
               f"P{most_likely}",
           ), tags=tags) 

        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _run_monte_carlo_threaded(self):
        self.monte_carlo.config(state="disabled", text="Simulating…")
        self._show_monte_carlo_grid()

    def _show_monte_carlo_grid(self):
        """Show the starting grid window before running Monte Carlo."""
        
        track_name = self.track_var.get()
        player_code = self.driver_var.get()
        grid_pos = int(self.grid_pos_var.get())

        drivers = create_grid()
        sorted_codes = [d.code for d in drivers]
        if player_code in sorted_codes:
            sorted_codes.remove(player_code)
            sorted_codes.insert(grid_pos - 1, player_code)
        sorted_drivers = sorted(
            drivers,
            key=lambda d: sorted_codes.index(d.code) if d.code in sorted_codes else 99
        )

        # Reuse the same grid window as the single race
        win = tk.Toplevel(self)
        win.title("Starting Grid — Monte Carlo")
        win.configure(bg="#1a1a2e")
        win.geometry("560x620")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text=f"Starting Grid — {track_name}",
                font=("Helvetica", 14, "bold"), fg="white", bg="#1a1a2e").pack(pady=(16, 2))
        tk.Label(win, text="Set the grid, then run 1000 simulations from this position.",
                font=("Helvetica", 8), fg="#555577", bg="#1a1a2e").pack(pady=(0, 8))

        outer = tk.Frame(win, bg="#1a1a2e")
        outer.pack(fill="both", expand=True, padx=20)

        canvas = tk.Canvas(outer, bg="#1a1a2e", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(canvas, bg="#1a1a2e")
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        pos_vars = []
    
        def _build_rows(driver_list):
            for widget in frame.winfo_children():
                widget.destroy()
            for col_idx, col in enumerate(["POS", "DRIVER", "TEAM", "COMPOUND"]):
                tk.Label(frame, text=col, fg="#555555", bg="#1a1a2e",
                        font=("Helvetica", 8, "bold")).grid(
                            row=0, column=col_idx, sticky="w", padx=(0, 20), pady=(0, 6))
            pos_vars.clear()
            for i, driver in enumerate(driver_list):
                r = i + 1
                is_player = driver.code == player_code
                fg = "#00d4ff" if is_player else ("#f1c40f" if i < 3 else "#cccccc")
                bg_row = "#16213e" if i % 2 == 0 else "#1a1a2e"

                pos_var = tk.IntVar(value=i + 1)
                pos_vars.append((pos_var, driver.code))

                ttk.Spinbox(frame, from_=1, to=len(driver_list),
                            textvariable=pos_var, width=4).grid(
                                row=r, column=0, sticky="w", padx=(0, 20), pady=1)
                tk.Label(frame, text=driver.code, fg=fg, bg=bg_row,
                        font=("Helvetica", 9, "bold" if is_player else "normal")).grid(
                            row=r, column=1, sticky="w", padx=(0, 20), pady=1)
                tk.Label(frame, text=driver.team.name[:18], fg="#888888", bg=bg_row,
                        font=("Helvetica", 9)).grid(
                            row=r, column=2, sticky="w", padx=(0, 20), pady=1)
                comp = driver.current_compound
                marker = "  ◀ YOU" if is_player else ""
                tk.Label(frame, text=f"● {comp}{marker}",
                        fg="#00d4ff" if is_player else COMPOUND_COLORS.get(comp, "#888888"),
                        bg=bg_row, font=("Helvetica", 9)).grid(
                            row=r, column=3, sticky="w", pady=1)
                
        saved = self._load_grid()
        if saved and saved.get("track") == track_name:
            def load_saved():
                saved_order = saved["grid_order"]
                code_to_driver = {d.code: d for d in sorted_drivers}
                new_order = [code_to_driver[c] for c in saved_order if c in code_to_driver]
                sorted_drivers[:] = new_order
                _build_rows(sorted_drivers)

            tk.Button(win, text="↩  Load Saved Grid", command=load_saved,
                    bg="#2c2c3e", fg="#aaaaaa", relief="flat", cursor="hand2",
                    font=("Helvetica", 10), padx=12, pady=6).pack(
                        fill="x", padx=20, pady=(0, 2))
            
        _build_rows(sorted_drivers)

        def apply_order():
            order = []
            for idx, (pv, code) in enumerate(pos_vars):
                try:
                    p = int(pv.get())
                except (ValueError, tk.TclError):
                    p = idx + 1
                order.append((p, idx, code))
            order.sort(key=lambda x: (x[0], x[1]))
            code_to_driver = {d.code: d for d in sorted_drivers}
            sorted_drivers[:] = [code_to_driver[code] for _, _, code in order]
            _build_rows(sorted_drivers)

        tk.Button(win, text="↕  Apply Order", command=apply_order,
                bg="#0f3460", fg="white", relief="flat", cursor="hand2",
                font=("Helvetica", 10, "bold"), padx=12, pady=6).pack(
                    fill="x", padx=20, pady=(6, 2))

        btn_frame = tk.Frame(win, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=(4, 16))

        def start():
            final_order = [d.code for d in sorted_drivers]
            self._save_grid(final_order)
            win.destroy()
            self.status_label.config(text="Running Monte Carlo…")
            threading.Thread(
                target=self._run_monte_carlo,
                kwargs={"grid_order": final_order},
                daemon=True,
            ).start()

        def cancel():
            win.destroy()
            self.monte_carlo.config(state="normal", text="▶  Simulate x1000")

        tk.Button(btn_frame, text="▶  Run x1000", command=start,
                bg="#e74c3c", fg="white", relief="flat", cursor="hand2",
                font=("Helvetica", 11, "bold"), padx=16, pady=8).pack(side="left")
        tk.Button(btn_frame, text="Cancel", command=cancel,
                bg="#2c2c3e", fg="#aaaaaa", relief="flat", cursor="hand2",
                font=("Helvetica", 10), padx=12, pady=8).pack(side="left", padx=(10, 0))

    def _show_starting_grid(self):
        """Show the starting grid window.  Drivers can be reordered by editing the position
           spinboxes and clicking 'Apply Order'.  Clicking 'Start Race' locks in the grid and
           begins the simulation."""

        track_name = self.track_var.get()
        player_code = self.driver_var.get()
        grid_pos = int(self.grid_pos_var.get())

        # Build the auto grid, then honour the player's chosen grid position
        drivers = create_grid()
        sorted_codes = [d.code for d in drivers]
        if player_code in sorted_codes:
            sorted_codes.remove(player_code)
            sorted_codes.insert(grid_pos - 1, player_code)
        sorted_drivers = sorted(
            drivers,
            key=lambda d: sorted_codes.index(d.code) if d.code in sorted_codes else 99
        )

        # ── Toplevel window ──────────────────────────────────────
        win = tk.Toplevel(self)
        win.title("Starting Grid")
        win.configure(bg="#1a1a2e")
        win.geometry("560x620")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text=f"Starting Grid — {track_name}",
                 font=("Helvetica", 14, "bold"), fg="white", bg="#1a1a2e"
                 ).pack(pady=(16, 2))
        tk.Label(win, text=TRACKS[track_name].get("name", track_name),
                 font=("Helvetica", 9), fg="#666666", bg="#1a1a2e"
                 ).pack(pady=(0, 4))
        tk.Label(win, text="Edit position numbers then click  'Apply Order'  to reorder the grid.",
                 font=("Helvetica", 8), fg="#555577", bg="#1a1a2e"
                 ).pack(pady=(0, 8))

        # ── Scrollable grid rows ─────────────────────────────────
        outer = tk.Frame(win, bg="#1a1a2e")
        outer.pack(fill="both", expand=True, padx=20)

        canvas = tk.Canvas(outer, bg="#1a1a2e", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(canvas, bg="#1a1a2e")
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")
            
        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        frame.bind("<Configure>", _on_configure)

        # Column headers
        for col_idx, col in enumerate(["POS", "DRIVER", "TEAM", "COMPOUND"]):
            tk.Label(frame, text=col, fg="#555555", bg="#1a1a2e",
                     font=("Helvetica", 8, "bold")).grid(
                         row=0, column=col_idx, sticky="w", padx=(0, 20), pady=(0, 6))

        # One IntVar per driver to hold their editable position
        pos_vars: list[tuple[tk.IntVar, str]] = []  # (IntVar, driver_code)
        row_labels: dict[str, tk.Label] = {}         # code -> position badge label

        def _build_rows(driver_list):
            """Render all grid rows; called initially and after every apply."""
            for widget in frame.winfo_children():
                # Clear all rows except the header (row 0 is rebuilt too)
                widget.destroy()

            # Re-draw headers
            for col_idx, col in enumerate(["POS", "DRIVER", "TEAM", "COMPOUND"]):
                tk.Label(frame, text=col, fg="#555555", bg="#1a1a2e",
                         font=("Helvetica", 8, "bold")).grid(
                             row=0, column=col_idx, sticky="w", padx=(0, 20), pady=(0, 6))

            pos_vars.clear()

            for i, driver in enumerate(driver_list):
                r = i + 1
                is_player = driver.code == player_code
                fg = "#00d4ff" if is_player else ("#f1c40f" if i < 3 else "#cccccc")
                bg_row = "#16213e" if i % 2 == 0 else "#1a1a2e"

                # Editable position spinbox
                pos_var = tk.IntVar(value=i + 1)
                pos_vars.append((pos_var, driver.code))

                pos_spin = ttk.Spinbox(frame, from_=1, to=len(driver_list),
                                       textvariable=pos_var, width=4)
                pos_spin.grid(row=r, column=0, sticky="w", padx=(0, 20), pady=1)

                tk.Label(frame, text=driver.code, fg=fg, bg=bg_row,
                         font=("Helvetica", 9, "bold" if is_player else "normal")).grid(
                             row=r, column=1, sticky="w", padx=(0, 20), pady=1)

                tk.Label(frame, text=driver.team.name[:18], fg="#888888", bg=bg_row,
                         font=("Helvetica", 9)).grid(
                             row=r, column=2, sticky="w", padx=(0, 20), pady=1)

                comp = driver.current_compound
                comp_color = COMPOUND_COLORS.get(comp, "#888888")
                marker = "  ◀ YOU" if is_player else ""
                tk.Label(frame, text=f"● {comp}{marker}",
                         fg="#00d4ff" if is_player else comp_color, bg=bg_row,
                         font=("Helvetica", 9)).grid(
                             row=r, column=3, sticky="w", pady=1)

        saved = self._load_grid()
        if saved and saved.get("track") == track_name:
            def load_saved():
                saved_order = saved["grid_order"]
                code_to_driver = {d.code: d for d in sorted_drivers}
                new_order = [code_to_driver[c] for c in saved_order if c in code_to_driver]
                sorted_drivers[:] = new_order
                _build_rows(sorted_drivers)

            tk.Button(win, text="↩  Load Saved Grid", command=load_saved,
                    bg="#2c2c3e", fg="#aaaaaa", relief="flat", cursor="hand2",
                    font=("Helvetica", 10), padx=12, pady=6).pack(
                        fill="x", padx=20, pady=(0, 2))

        _build_rows(sorted_drivers)

        # ── Apply Order button ───────────────────────────────────
        def apply_order():
            """Re-sort sorted_drivers according to the position spinboxes, resolve ties by
               current order, then redraw the rows."""
            # Read positions; if duplicate or out of range, fall back to current index
            order = []
            for idx, (pv, code) in enumerate(pos_vars):
                try:
                    p = int(pv.get())
                except (ValueError, tk.TclError):
                    p = idx + 1
                order.append((p, idx, code))

            order.sort(key=lambda x: (x[0], x[1]))  # stable sort: pos first, then original idx

            # Re-map sorted_drivers to match the new order
            code_to_driver = {d.code: d for d in sorted_drivers}
            new_order = [code_to_driver[code] for _, _, code in order]
            sorted_drivers[:] = new_order
            _build_rows(sorted_drivers)

        apply_btn = tk.Button(win, text="↕  Apply Order", command=apply_order,
                              bg="#0f3460", fg="white", relief="flat", cursor="hand2",
                              font=("Helvetica", 10, "bold"), padx=12, pady=6)
        apply_btn.pack(fill="x", padx=20, pady=(6, 2))

        # ── Start / Cancel buttons ───────────────────────────────
        btn_frame = tk.Frame(win, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=(4, 16))

        def start():
            # Capture the final ordered list of codes to pass to the simulation
            final_order = [d.code for d in sorted_drivers]
            self._save_grid(final_order)
            win.destroy()
            self.status_label.config(text="Running simulation…")
            threading.Thread(
                target=self._run_simulation,
                kwargs={"grid_order": final_order},
                daemon=True,
            ).start()

        def cancel():
            win.destroy()
            self.run_btn.config(state="normal", text="▶  Simulate Race")

        tk.Button(btn_frame, text="▶  Start Race", command=start,
                  bg="#e74c3c", fg="white", relief="flat", cursor="hand2",
                  font=("Helvetica", 11, "bold"), padx=16, pady=8).pack(side="left")
        tk.Button(btn_frame, text="Cancel", command=cancel,
                  bg="#2c2c3e", fg="#aaaaaa", relief="flat", cursor="hand2",
                  font=("Helvetica", 10), padx=12, pady=8).pack(side="left", padx=(10, 0))

    def _show_error(self, msg):
        self.run_btn.config(state="normal", text="▶  Simulate Race")
        self.status_label.config(text="Error — see console")
        messagebox.showerror("Simulation Error", msg)

    # ── Result rendering ──────────────────────

    def _show_results(self, drivers, history, track, track_name, player_code):
        self.run_btn.config(state="normal", text="▶  Simulate Race")

        sorted_drivers = sorted(drivers, key=lambda d: d.race_time)
        leader_time = sorted_drivers[0].race_time

        # ── Standings tab ──
        for row in self.standings_tree.get_children():
            self.standings_tree.delete(row)

        for pos, driver in enumerate(sorted_drivers, start=1):
            gap = "LEADER" if pos == 1 else f"+{driver.race_time - leader_time:.3f}s"
            fl = f"{driver.fastest_lap:.3f}s" if driver.fastest_lap else "—"
            race_mins = int(driver.race_time // 60)
            race_secs = driver.race_time % 60
            race_time_str = f"{race_mins}:{race_secs:06.3f}"

            tags = []
            if driver.code == player_code:
                tags.append("player")
            elif pos <= 3:
                tags.append("podium")
            else:
                tags.append("even" if pos % 2 == 0 else "odd")

            self.standings_tree.insert("", "end", values=(
                pos,
                driver.code,
                driver.team.name,
                race_time_str,
                gap,
                fl,
                driver.pit_stops,
                driver.current_compound,
            ), tags=tags)

        # ── Strategy tab ──
        self._draw_strategy_chart(sorted_drivers, history, track, player_code)

        # ── Info tab ──
        self._update_info_tab(track, track_name, sorted_drivers, player_code)

        player = next((d for d in sorted_drivers if d.code == player_code), None)
        if player:
            pos = sorted_drivers.index(player) + 1
            self.status_label.config(
                text=f"Finished P{pos}  |  Race time {int(player.race_time//60)}:{player.race_time%60:06.3f}"
            )

        self.notebook.select(0)

    def _draw_strategy_chart(self, sorted_drivers, history, track, player_code):
        """Draw the strategy chart on the strategy tab canvas, showing the stint compounds and 
            pit stops for each driver across the laps."""
        
        c = self.strategy_canvas
        c.delete("all")
        c.update_idletasks()

        if not history.get("laps"):
            return

        total_laps = max(history["laps"])
        canvas_w = max(c.winfo_width(), 600)
        row_h = 28
        pad_left = 60
        pad_right = 16
        chart_w = canvas_w - pad_left - pad_right
        total_height = len(sorted_drivers) * row_h + 40

        c.configure(scrollregion=(0, 0, canvas_w, total_height))

        # Lap axis ticks
        tick_every = max(1, total_laps // 10)
        for lap in range(0, total_laps + 1, tick_every):
            x = pad_left + lap / total_laps * chart_w
            c.create_line(x, 0, x, total_height, fill="#2a2a3e", width=1)
            c.create_text(x, total_height - 10, text=str(lap),
                          fill="#555555", font=("Helvetica", 7))

        for row_idx, driver in enumerate(sorted_drivers):
            y = row_idx * row_h + 6
            code = driver.code
            is_player = code == player_code

            label_color = "#00d4ff" if is_player else "#888888"
            c.create_text(pad_left - 6, y + row_h // 2 - 4, text=code,
                          anchor="e", fill=label_color,
                          font=("Helvetica", 9, "bold" if is_player else "normal"))

            compounds_by_lap = history.get("compounds", {}).get(code, [])
            if not compounds_by_lap:
                continue

            stint_start = 0
            prev_c = compounds_by_lap[0]
            for i, comp in enumerate(compounds_by_lap):
                if comp != prev_c or i == len(compounds_by_lap) - 1:
                    end_i = i if comp != prev_c else i + 1
                    x1 = pad_left + stint_start / total_laps * chart_w
                    x2 = pad_left + end_i / total_laps * chart_w
                    color = COMPOUND_COLORS.get(prev_c, "#888888")
                    c.create_rectangle(x1, y, x2 - 1, y + row_h - 6,
                                       fill=color, outline="")
                    if x2 - x1 > 14:
                        c.create_text((x1 + x2) / 2, y + (row_h - 6) / 2,
                                      text=COMPOUND_SHORT.get(prev_c, prev_c[0]),
                                      fill="white", font=("Helvetica", 7, "bold"))
                    stint_start = i
                    prev_c = comp

            pit_laps = history.get("pit_laps", {}).get(code, [])
            for pit_lap in pit_laps:
                try:
                    lap_num = int(pit_lap)
                except Exception:
                    continue
                if lap_num < 1 or lap_num > total_laps:
                    continue
                x = pad_left + lap_num / total_laps * chart_w
                yc = y + (row_h - 6) / 2
                r = 5
                c.create_oval(x - r, yc - r, x + r, yc + r, fill="#ffffff", outline="#000000")

        legend_x = pad_left
        c.create_text(legend_x, total_height - 24, text="Compounds: ",
                      anchor="w", fill="#666666", font=("Helvetica", 8))
        legend_x += 72
        for comp, color in COMPOUND_COLORS.items():
            c.create_rectangle(legend_x, total_height - 28, legend_x + 12,
                               total_height - 16, fill=color, outline="")
            c.create_text(legend_x + 16, total_height - 22, text=comp,
                          anchor="w", fill="#666666", font=("Helvetica", 8))
            legend_x += 80

    def _update_info_tab(self, track, track_name, sorted_drivers, player_code):
        """Update the info tab with detailed information about the track, weather, and the 
            driver's performance."""
        
        player = next((d for d in sorted_drivers if d.code == player_code), None)
        pos = sorted_drivers.index(player) + 1 if player else "?"

        lines = [
            f"Track:           {track_name}",
            f"Length:          {track['length_km']} km",
            f"Pit delta:       {track['pit_delta']}s",
            f"Tire stress:     {track['tire_stress']}",
            f"SC chance:       {track['safety_car_chance']*100:.0f}%",
            f"Overtake diff:   {track['overtaking_difficulty']*100:.0f}%",
            f"DRS effect:      {track['drs_effect']}",
            f"Avg temp:        {track['avg_temp']}°C",
            f"Rain prob:       {track['rain_probability']*100:.0f}%",
            "",
            "─" * 38,
            f"  Player result: P{pos}  ({player_code})",
        ]
        if player:
            lines += [
                f"  Race time:     {int(player.race_time//60)}:{player.race_time%60:06.3f}",
                f"  Fastest lap:   {player.fastest_lap:.3f}s" if player.fastest_lap else "  Fastest lap:   —",
                f"  Pit stops:     {player.pit_stops}",
                f"  Final tyre:    {player.current_compound}",
            ]
        lines += [
            "",
            "─" * 38,
            "  Full standings:",
        ]
        leader_time = sorted_drivers[0].race_time
        for i, d in enumerate(sorted_drivers, 1):
            gap = "LEADER" if i == 1 else f"+{d.race_time - leader_time:.3f}s"
            marker = " ◀" if d.code == player_code else ""
            lines.append(f"  P{i:<3} {d.code:<4}  {gap}{marker}")

        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("end", "\n".join(lines))
        self.info_text.config(state="disabled")


# ─────────────────────────────────────────────
#  Entry points
# ─────────────────────────────────────────────

def launch_strategy_gui():
    """Launch the strategy planner GUI application."""

    app = StrategyGUI()
    app.mainloop()


def main():
    launch_strategy_gui()

if __name__ == "__main__":
    main()