import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from config.Tracks import TRACKS
from config.Tires import TIRES
from strategy.predictor import (
    predict_strategies,
    race_laps,
    recommended_starting_compound,
)


COMPOUND_COLORS = {
    "SOFT": "#d92f2f",
    "MEDIUM": "#e2bf2f",
    "HARD": "#d8dbe2",
    "INTERMEDIATE": "#42a85f",
    "WET": "#2d76d2",
}

class StrategyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("F1 Strategy Predictor")
        self.geometry("1220x760")
        self.minsize(1060, 680)

        self.results = []
        self.selected_result = None

        self._configure_style()
        self._build_variables()
        self._build_layout()
        self._update_lap_hint()
        self.predict()

    def _configure_style(self):
        self.configure(bg="#f4f5f7")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f5f7")
        style.configure("Panel.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f4f5f7", foreground="#20242c")
        style.configure("Panel.TLabel", background="#ffffff", foreground="#20242c")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background="#f4f5f7")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), background="#ffffff")
        style.configure("TButton", padding=(12, 7))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_variables(self):
        self.track_var = tk.StringVar(value="Italy")
        self.start_compound_var = tk.StringVar(value="MEDIUM")
        self.team_pace_var = tk.DoubleVar(value=-0.3)
        self.pit_stop_var = tk.DoubleVar(value=2.4)
        self.wetness_var = tk.DoubleVar(value=0.0)
        self.max_stops_var = tk.IntVar(value=2)
        self.laps_override_var = tk.StringVar(value="")
        self.lap_hint_var = tk.StringVar()

    def _build_layout(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(header, text="F1 Strategy Predictor", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            header,
            textvariable=self.lap_hint_var,
            font=("Segoe UI", 10),
            foreground="#5d6470",
        ).pack(side=tk.RIGHT)

        controls = ttk.Frame(root, style="Panel.TFrame", padding=16)
        controls.grid(row=1, column=0, sticky="nsw", padx=(0, 14))
        controls.columnconfigure(1, weight=1)

        self._build_controls(controls)

        content = ttk.Frame(root)
        content.grid(row=1, column=1, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        content.columnconfigure(0, weight=1)

        self._build_table(content)
        self._build_charts(content)

    def _build_controls(self, parent):
        ttk.Label(parent, text="Race Setup", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        self._label(parent, "Track", 1)
        track_box = ttk.Combobox(
            parent,
            textvariable=self.track_var,
            values=sorted(TRACKS.keys()),
            state="readonly",
            width=22,
        )
        track_box.grid(row=1, column=1, sticky="ew", pady=5)
        track_box.bind("<<ComboboxSelected>>", lambda _event: self._update_lap_hint())

        self._label(parent, "Starting tyre", 2)
        ttk.Combobox(
            parent,
            textvariable=self.start_compound_var,
            values=list(TIRES.keys()),
            state="readonly",
            width=22,
        ).grid(row=2, column=1, sticky="ew", pady=5)

        self._label(parent, "Team pace", 3)
        ttk.Spinbox(
            parent,
            textvariable=self.team_pace_var,
            from_=-2.0,
            to=2.0,
            increment=0.1,
            width=8,
        ).grid(row=3, column=1, sticky="ew", pady=5)

        self._label(parent, "Pit stop avg", 4)
        ttk.Spinbox(
            parent,
            textvariable=self.pit_stop_var,
            from_=1.8,
            to=5.0,
            increment=0.1,
            width=8,
        ).grid(row=4, column=1, sticky="ew", pady=5)

        self._label(parent, "Track wetness", 5)
        wetness = ttk.Scale(
            parent,
            variable=self.wetness_var,
            from_=0,
            to=1,
            orient=tk.HORIZONTAL,
            command=self._on_wetness_changed,
        )
        wetness.grid(row=5, column=1, sticky="ew", pady=5)

        self._label(parent, "Max stops", 6)
        ttk.Spinbox(
            parent,
            textvariable=self.max_stops_var,
            from_=0,
            to=2,
            increment=1,
            width=8,
        ).grid(row=6, column=1, sticky="ew", pady=5)

        self._label(parent, "Laps override", 7)
        override = ttk.Entry(parent, textvariable=self.laps_override_var, width=8)
        override.grid(row=7, column=1, sticky="ew", pady=5)
        override.bind("<KeyRelease>", lambda _event: self._update_lap_hint())

        ttk.Button(parent, text="Predict Strategies", command=self.predict).grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=(18, 8)
        )
        ttk.Button(parent, text="Reset Inputs", command=self.reset_inputs).grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=(0, 16)
        )

        ttk.Separator(parent).grid(row=10, column=0, columnspan=2, sticky="ew", pady=12)

        ttk.Label(parent, text="Selected Plan", style="Section.TLabel").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        self.summary_text = tk.Text(
            parent,
            height=14,
            width=34,
            wrap=tk.WORD,
            borderwidth=0,
            padx=10,
            pady=10,
            bg="#f7f8fa",
            fg="#20242c",
            font=("Segoe UI", 10),
        )
        self.summary_text.grid(row=12, column=0, columnspan=2, sticky="nsew")
        self.summary_text.configure(state=tk.DISABLED)

    def _label(self, parent, text, row):
        ttk.Label(parent, text=text, style="Panel.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=5
        )

    def _build_table(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        frame.grid(row=0, column=0, sticky="nsew", pady=(0, 14))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Ranked Strategy Predictions", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        columns = ("rank", "strategy", "stops", "pit_laps", "time", "gap", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "rank": "#",
            "strategy": "Compounds",
            "stops": "Stops",
            "pit_laps": "Pit Laps",
            "time": "Race Time",
            "gap": "Gap",
            "status": "Status",
        }
        widths = {
            "rank": 46,
            "strategy": 190,
            "stops": 64,
            "pit_laps": 140,
            "time": 110,
            "gap": 90,
            "status": 110,
        }

        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor=tk.CENTER)

        self.tree.column("strategy", anchor=tk.W)
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_strategy_selected)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _build_charts(self, parent):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Strategy View", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        self.figure = Figure(figsize=(8.4, 4.2), dpi=100)
        self.stint_axis = self.figure.add_subplot(211)
        self.lap_axis = self.figure.add_subplot(212)
        self.figure.tight_layout(pad=2.2)

        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

    def _parse_laps_override(self):
        value = self.laps_override_var.get().strip()

        if not value:
            return None

        try:
            laps = int(value)
        except ValueError:
            raise ValueError("Laps override must be a whole number.")

        if laps < 1:
            raise ValueError("Laps override must be at least 1.")

        return laps

    def _update_lap_hint(self):
        try:
            track_name = self.track_var.get()
            track = TRACKS[track_name]
            laps = race_laps(track_name, track, self._parse_laps_override())
            distance = laps * track["length_km"]
            self.lap_hint_var.set(
                f"{track_name}: {laps} laps, {distance:.1f} km, pit loss {track['pit_delta']:.1f}s"
            )
        except ValueError:
            self.lap_hint_var.set("Enter a whole number for laps.")

    def _on_wetness_changed(self, _value=None):
        self.start_compound_var.set(
            recommended_starting_compound(float(self.wetness_var.get()))
        )

    def reset_inputs(self):
        self.track_var.set("Italy")
        self.team_pace_var.set(-0.3)
        self.pit_stop_var.set(2.4)
        self.wetness_var.set(0.0)
        self.start_compound_var.set(
            recommended_starting_compound(float(self.wetness_var.get()))
        )
        self.max_stops_var.set(2)
        self.laps_override_var.set("")
        self._update_lap_hint()
        self.predict()

    def predict(self):
        try:
            laps_override = self._parse_laps_override()
            max_stops = max(0, min(2, int(self.max_stops_var.get())))
            self.results = predict_strategies(
                self.track_var.get(),
                TRACKS[self.track_var.get()],
                starting_compound=self.start_compound_var.get(),
                team_pace=float(self.team_pace_var.get()),
                pit_stop_avg=float(self.pit_stop_var.get()),
                wetness=float(self.wetness_var.get()),
                max_stops=max_stops,
                override_laps=laps_override,
                limit=15,
            )
        except Exception as exc:
            messagebox.showerror("Prediction failed", str(exc))
            return

        self._update_lap_hint()
        self._populate_table()

        if self.results:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
            self._display_result(self.results[0])

    def _populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, result in enumerate(self.results):
            pit_laps = ", ".join(str(lap) for lap in result.pit_laps) or "-"
            values = (
                result.rank,
                " - ".join(result.compounds),
                result.stops,
                pit_laps,
                self._format_time(result.total_time),
                f"+{result.gap_to_best:.2f}s",
                result.validity,
            )
            self.tree.insert("", tk.END, iid=str(index), values=values)

    def _on_strategy_selected(self, _event):
        selection = self.tree.selection()

        if not selection:
            return

        index = int(selection[0])
        self._display_result(self.results[index])

    def _display_result(self, result):
        self.selected_result = result
        self._update_summary(result)
        self._draw_charts(result)

    def _update_summary(self, result):
        stints = "\n".join(
            f"Lap {stint.start_lap}-{stint.end_lap}: {stint.compound} ({stint.laps} laps)"
            for stint in result.stints
        )
        pit_laps = ", ".join(str(lap) for lap in result.pit_laps) or "No stops"
        text = (
            f"Rank {result.rank}\n"
            f"Total time: {self._format_time(result.total_time)}\n"
            f"Gap to best: +{result.gap_to_best:.2f}s\n"
            f"Pit laps: {pit_laps}\n"
            f"Pit loss: {result.pit_loss:.2f}s\n\n"
            f"{stints}"
        )

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state=tk.DISABLED)

    def _draw_charts(self, result):
        self.stint_axis.clear()
        self.lap_axis.clear()

        for stint in result.stints:
            color = COMPOUND_COLORS.get(stint.compound, "#7d8590")
            self.stint_axis.barh(
                ["Strategy"],
                stint.laps,
                left=stint.start_lap - 1,
                color=color,
                edgecolor="#20242c",
                linewidth=0.8,
            )
            self.stint_axis.text(
                stint.start_lap - 1 + stint.laps / 2,
                0,
                stint.compound,
                ha="center",
                va="center",
                fontsize=9,
                color="#111111",
            )

        self.stint_axis.set_title("Stints")
        self.stint_axis.set_xlabel("Lap")
        self.stint_axis.set_yticks([])
        self.stint_axis.set_xlim(0, len(result.lap_times))
        self.stint_axis.grid(axis="x", color="#d8dce3", linewidth=0.8)

        laps = list(range(1, len(result.lap_times) + 1))
        self.lap_axis.plot(laps, result.lap_times, color="#1f5eff", linewidth=2)
        for pit_lap in result.pit_laps:
            self.lap_axis.axvline(pit_lap, color="#20242c", linestyle="--", linewidth=1)

        self.lap_axis.set_title("Predicted Lap Time")
        self.lap_axis.set_xlabel("Lap")
        self.lap_axis.set_ylabel("Seconds")
        self.lap_axis.grid(color="#d8dce3", linewidth=0.8)

        self.figure.tight_layout(pad=2.2)
        self.canvas.draw_idle()

    def _format_time(self, seconds):
        minutes = int(seconds // 60)
        remainder = seconds - minutes * 60
        return f"{minutes}:{remainder:05.2f}"


def main():
    app = StrategyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
