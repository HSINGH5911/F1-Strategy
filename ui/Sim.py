import math
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from models.driver import Driver
from models.team import Team
from models.race_state import RaceState
from config.Tracks import TRACKS
from config.Teams import TEAMS
from config.Drivers import DRIVERS
from config.Tires import TIRES
from simulation.race_simulator import simulate_race

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

def create_grid():
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
        drivers.append(driver)
    return drivers


def race_laps(track):
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

    while race_state.current_lap <= total_laps:
        simulate_lap(drivers, track, race_state, total_laps)
        update_positions(drivers)
        process_overtakes(drivers, track)

        # ── Pit stops ──────────────────────────────────────────
        for driver in drivers:
            if driver is player_driver and plan.stops:
                # Player: use the strategy plan
                scheduled_compound = plan.next_stop_for_lap(race_state.current_lap)
                if scheduled_compound:
                    perform_stop(driver, track, scheduled_compound, race_state)
            else:
                # AI drivers: keep the automatic degradation logic
                tire_data = TIRES[driver.current_compound]
                if driver.tire_distance >= tire_data["max_distance"]:
                    perform_stop(driver, track, "HARD", race_state)

        update_weather(race_state)
        record_history(history, race_state, drivers)
        race_state.current_lap += 1

    return drivers


# ─────────────────────────────────────────────
#  Console runner (kept for headless use)
# ─────────────────────────────────────────────

def run_console_simulation(track_name="Italy", player_code=None, plan: StrategyPlan = None):
    track = TRACKS[track_name]
    race_state = RaceState()
    drivers = create_grid()

    history = {
        "laps": [], "positions": {}, "lap_times": {},
        "tire_distance": {}, "compounds": {}, "gaps": {}
    }

    if plan and player_code:
        simulate_race_with_strategy(drivers, track, race_state, history, plan, player_code)
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
        super().__init__()
        self.title("F1 Race Strategy Planner")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")
        self.geometry("1100x720")

        self.plan = StrategyPlan()
        self._stop_rows: list[dict] = []   # tracks widgets per stop row

        self._build_ui()
        self._refresh_laps()

    # ── Layout ────────────────────────────────

    def _build_ui(self):
        # Top bar
        topbar = tk.Frame(self, bg="#16213e", pady=8)
        topbar.pack(fill="x")
        tk.Label(topbar, text="F1 Strategy Planner", font=("Helvetica", 16, "bold"),
                 fg="white", bg="#16213e").pack(side="left", padx=16)

        # Main columns
        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(main, bg="#1a1a2e", width=340)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side="left", fill="both", expand=True)

        self._build_setup_panel(left)
        self._build_strategy_panel(left)
        self._build_results_panel(right)

    def _section(self, parent, title):
        frame = tk.LabelFrame(parent, text=title, fg="#aaaaaa",
                              bg="#16213e", bd=1, relief="flat",
                              font=("Helvetica", 9, "bold"), padx=10, pady=8)
        frame.pack(fill="x", pady=(0, 10))
        return frame

    # ── Setup panel ───────────────────────────

    def _build_setup_panel(self, parent):
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

        # Grid position
        tk.Label(f, text="Grid position", fg="#aaaaaa", bg="#16213e", font=("Helvetica", 9)).grid(
            row=3, column=0, sticky="w", pady=2)
        self.grid_pos_var = tk.IntVar(value=1)
        ttk.Spinbox(f, from_=1, to=20, textvariable=self.grid_pos_var, width=5).grid(
            row=3, column=1, sticky="w", padx=(8, 0), pady=2)

        # Lap count display
        self.laps_label = tk.Label(f, text="", fg="#00d4ff", bg="#16213e", font=("Helvetica", 9))
        self.laps_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

    # ── Strategy panel ────────────────────────

    def _build_strategy_panel(self, parent):
        f = self._section(parent, "Pit Stop Strategy")

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

        self.status_label = tk.Label(parent, text="", fg="#00d4ff",
                                     bg="#1a1a2e", font=("Helvetica", 9))
        self.status_label.pack(anchor="w", pady=(4, 0))

    def _build_results_panel(self, parent):
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
        self.standings_tree.tag_configure("even",   background="#141428")
        self.standings_tree.tag_configure("odd",    background="#1a1a2e")

    def _build_strategy_tab(self):
        self.strategy_canvas = tk.Canvas(self.tab_strategy, bg="#1a1a2e",
                                         highlightthickness=0)
        vsb = ttk.Scrollbar(self.tab_strategy, orient="vertical",
                            command=self.strategy_canvas.yview)
        self.strategy_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.strategy_canvas.pack(fill="both", expand=True)

    def _build_info_tab(self):
        self.info_text = tk.Text(self.tab_weather, bg="#0d0d1a", fg="#cccccc",
                                 font=("Courier", 10), state="disabled",
                                 relief="flat", padx=12, pady=10)
        self.info_text.pack(fill="both", expand=True)

    # ── Stop row management ───────────────────

    def _refresh_laps(self):
        track = TRACKS[self.track_var.get()]
        laps = race_laps(track)
        self.laps_label.config(text=f"{laps} laps · {track['length_km']} km · pit Δ {track['pit_delta']}s")
        self._redraw_stint_preview()

    def _add_stop(self):
        track = TRACKS[self.track_var.get()]
        total = race_laps(track)
        default_lap = max(1, total // (len(self._stop_rows) + 2))
        self._add_stop_row(default_lap, "HARD")

    def _add_stop_row(self, lap: int, compound: str):
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
        for row in self._stop_rows:
            row["frame"].destroy()
        self._stop_rows.clear()
        self._sync_plan()

    def _sync_plan(self):
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

    def _run_threaded(self):
        self.run_btn.config(state="disabled", text="Simulating…")
        self.status_label.config(text="Running simulation…")
        thread = threading.Thread(target=self._run_simulation, daemon=True)
        thread.start()

    def _run_simulation(self):
        try:
            track_name = self.track_var.get()
            player_code = self.driver_var.get()
            grid_pos = int(self.grid_pos_var.get())

            track = TRACKS[track_name]
            race_state = RaceState()
            drivers = create_grid()

            # Set grid positions: player first, then AI in order
            sorted_codes = [d.code for d in drivers]
            if player_code in sorted_codes:
                sorted_codes.remove(player_code)
                sorted_codes.insert(grid_pos - 1, player_code)
            for i, driver in enumerate(
                sorted(drivers, key=lambda d: sorted_codes.index(d.code)
                       if d.code in sorted_codes else 99), start=1
            ):
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

            # Driver label
            label_color = "#00d4ff" if is_player else "#888888"
            c.create_text(pad_left - 6, y + row_h // 2 - 4, text=code,
                          anchor="e", fill=label_color,
                          font=("Helvetica", 9, "bold" if is_player else "normal"))

            compounds_by_lap = history.get("compounds", {}).get(code, [])
            if not compounds_by_lap:
                continue

            # Draw stint segments
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

        # Legend
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
    app = StrategyGUI()
    app.mainloop()


def main():
    launch_strategy_gui()


if __name__ == "__main__":
    main()
