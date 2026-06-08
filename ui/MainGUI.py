"""Tkinter entry point for browsing F1 strategy data.

This module intentionally keeps the GUI lightweight: it collects input from the
user, then delegates the data loading and plotting work to the visualization
helpers in ``preloaded_visualizations``.
"""

from pathlib import Path
from tkinter import Tk, font, messagebox, ttk

from preloaded_visualizations.Tire_Strats import show_tire_strats, write_to_file


APP_TITLE = "F1 Strategy Sim"
WINDOW_SIZE = "800x600"
FIRST_FASTF1_YEAR = 2011
LAST_STRATEGY_LOAD_YEAR = 2025


class F1StrategySimGUI:
    """Small Tkinter app for launching data visualizations."""

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)

        # All screens are rendered inside this frame. Changing screens means
        # clearing it and adding a new set of widgets.
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.show_welcome_screen()

    # ------------------------------------------------------------------
    # General screen helpers
    # ------------------------------------------------------------------

    def clear_screen(self):
        """Remove every widget from the active screen."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def add_centered_label(self, text, relx, rely, **kwargs):
        """Create a label centered at a relative position."""
        label = ttk.Label(self.main_frame, text=text, **kwargs)
        label.place(relx=relx, rely=rely, anchor="center")
        return label

    def add_centered_button(self, text, relx, rely, command):
        """Create a button centered at a relative position."""
        button = ttk.Button(self.main_frame, text=text, command=command)
        button.place(relx=relx, rely=rely, anchor="center")
        return button

    def add_labeled_entry(self, label_text, rely, width=16):
        """Add a label/entry row and return the entry widget."""
        label = ttk.Label(self.main_frame, text=label_text)
        label.place(relx=0.36, rely=rely, anchor="e")

        entry = ttk.Entry(self.main_frame, width=width)
        entry.place(relx=0.39, rely=rely, anchor="w")
        return entry

    def add_back_button(self, command):
        """Add a consistent back button in the upper-left corner."""
        button = ttk.Button(self.main_frame, text="Back", command=command)
        button.place(relx=0.05, rely=0.05, anchor="nw")
        return button

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------

    def show_welcome_screen(self):
        """Render the first screen users see."""
        self.clear_screen()

        welcome_font = font.Font(
            family="Times New Roman",
            size=20,
            weight="bold",
        )

        self.add_centered_label(
            "Welcome to F1 Strategy Sim",
            relx=0.5,
            rely=0.25,
            font=welcome_font,
        )
        self.add_centered_button(
            "View Data",
            relx=0.5,
            rely=0.4,
            command=self.show_data_menu,
        )
        self.add_centered_button(
            "View Sim",
            relx=0.5,
            rely=0.5,
            command=self.show_sim_placeholder,
        )

    def show_data_menu(self):
        """Render data-related actions."""
        self.clear_screen()
        self.add_back_button(self.show_welcome_screen)

        self.add_centered_label(
            "What data do you want to see?",
            relx=0.5,
            rely=0.2,
        )
        self.add_centered_button(
            "View Tire Strategies",
            relx=0.5,
            rely=0.35,
            command=self.show_tire_strategy_form,
        )
        self.add_centered_button(
            "Load Tire Strategies",
            relx=0.5,
            rely=0.45,
            command=self.show_tire_strategy_loader,
        )

    def show_tire_strategy_form(self):
        """Collect the session details needed to plot tire strategies."""
        self.clear_screen()
        self.add_back_button(self.show_data_menu)

        self.add_centered_label(
            "View Tire Strategies",
            relx=0.5,
            rely=0.2,
        )

        year_entry = self.add_labeled_entry("Year", rely=0.35)
        location_entry = self.add_labeled_entry("Location", rely=0.45)
        session_entry = self.add_labeled_entry("Session", rely=0.55)

        self.add_centered_button(
            "Submit",
            relx=0.5,
            rely=0.68,
            command=lambda: self.view_tire_strategies(
                year_entry,
                location_entry,
                session_entry,
            ),
        )

    def show_tire_strategy_loader(self):
        """Collect a race location and cache every strategy from 2011-2025."""
        self.clear_screen()
        self.add_back_button(self.show_data_menu)

        self.add_centered_label(
            "Load Tire Strategies",
            relx=0.5,
            rely=0.25,
        )

        self.add_centered_label(
            "This loads race strategies from 2011 through 2025.",
            relx=0.5,
            rely=0.34,
        )

        location_entry = self.add_labeled_entry("Location", rely=0.48)

        self.add_centered_button(
            "Submit",
            relx=0.5,
            rely=0.62,
            command=lambda: self.load_tire_strategies(location_entry),
        )

    def show_sim_placeholder(self):
        """Show a friendly placeholder until the simulator GUI is connected."""
        self.clear_screen()
        self.add_back_button(self.show_welcome_screen)

        self.add_centered_label(
            "Simulation view coming soon.",
            relx=0.5,
            rely=0.4,
        )

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def view_tire_strategies(self, year_entry, location_entry, session_entry):
        """Validate the tire-strategy form and open the requested plot."""
        try:
            year = self.read_year(year_entry)
            location = self.read_required_text(location_entry, "Location")
            session_type = self.read_required_text(session_entry, "Session")
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))
            return

        self.run_plot(
            lambda: show_tire_strats(year, location, session_type),
            success_message=None,
        )

    def load_tire_strategies(self, location_entry):
        """Download and cache tire-strategy data for one race, 2011-2025."""
        try:
            location = self.read_required_text(location_entry, "Location")
        except ValueError as error:
            messagebox.showerror("Invalid input", str(error))
            return

        output_file = self.tire_strategy_output_file(location)
        years = range(FIRST_FASTF1_YEAR, LAST_STRATEGY_LOAD_YEAR + 1)

        self.run_plot(
            lambda: write_to_file(years, location, "r", output_file),
            success_message=f"Tire strategies saved to:\n{output_file}",
        )

    # ------------------------------------------------------------------
    # Validation and file helpers
    # ------------------------------------------------------------------

    @staticmethod
    def read_required_text(entry, field_name):
        """Return stripped entry text or raise a clear validation error."""
        value = entry.get().strip()
        if not value:
            raise ValueError(f"{field_name} is required.")
        return value

    @classmethod
    def read_year(cls, entry):
        """Parse a valid FastF1 year from an entry widget."""
        raw_year = cls.read_required_text(entry, "Year")

        try:
            year = int(raw_year)
        except ValueError as error:
            raise ValueError("Year must be a whole number.") from error

        if year < FIRST_FASTF1_YEAR:
            raise ValueError(
                f"Year must be {FIRST_FASTF1_YEAR} or later."
            )

        return year

    @staticmethod
    def tire_strategy_output_file(location):
        """Build the project-relative path for cached tire-strategy data."""
        safe_location = location.replace(" ", "_")
        return (
            Path(__file__).resolve().parents[1]
            / "data_found"
            / "Tire_Strategies"
            / f"{safe_location}_Tire_Strats.json"
        )

    @staticmethod
    def run_plot(action, success_message=None):
        """Run a plotting/data action and show GUI-friendly errors."""
        try:
            action()
        except Exception as error:
            messagebox.showerror("Action failed", str(error))
            return

        if success_message:
            messagebox.showinfo("Done", success_message)


def main():
    """Launch the Tkinter GUI."""
    root = Tk()
    F1StrategySimGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
