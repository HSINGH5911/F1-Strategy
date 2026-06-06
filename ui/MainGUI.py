from tkinter import *
from tkinter import ttk, font

from preloaded_visualizations.LapTimes import show_lap_time_data
from preloaded_visualizations.Track_Map import show_track
from preloaded_visualizations.Tire_Strats import show_tire_strats
from preloaded_visualizations.Driver_Comparision import show_comparison_data
from preloaded_visualizations.Laptime_Distribution import show_dist_data

root = Tk()
root.geometry('800x600')

frm = ttk.Frame(root)
frm.pack(fill='both', expand=True)

def view_data():
    data_frm = ttk.Frame(frm)
    data_frm.pack(fill='both', expand=True)

    data_welcome = ttk.Label(data_frm, text="What data do you want to see?")
    data_welcome.place(relx=0.5, rely=0.2, anchor='center')

    view_tire_strats = ttk.Button(
        data_frm,
        text="View Tire Strats",
        command=lambda: view_tire_strat(data_frm)
    )
    view_tire_strats.place(relx=0.5, rely=0.3, anchor='center')


def view_tire_strat(data_frm):
    tire_strat_frm = ttk.Frame(data_frm)
    tire_strat_frm.pack(fill='both', expand=True)

    year_label = ttk.Label(frm, text="Year")
    year_label.place(relx=0.3, rely=0.2, anchor='center')



def view_sim():
    print("Sim")

def create_welcome():
    welcome_font = font.Font(
        family='Times New Roman',
        size=20,
        weight='bold'
    )

    welcome_label = ttk.Label(
        frm,
        text="Welcome to F1 Strategy Sim",
        font=welcome_font
    )
    welcome_label.place(relx=0.5, rely=0.25, anchor='center')

    view_data_btn = ttk.Button(
        frm,
        text="View Data",
        command=view_data
    )
    view_data_btn.place(relx=0.5, rely=0.4, anchor='center')

    view_sim_btn = ttk.Button(
        frm,
        text="View Sim",
        command=view_sim
    )
    view_sim_btn.place(relx=0.5, rely=0.5, anchor='center')

create_welcome()
root.mainloop()
