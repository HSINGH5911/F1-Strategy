import ui.Sim
from ui.Sim import StrategyGUI
print('module file', ui.Sim.__file__)
app = StrategyGUI()
print('label text:', app.laps_label.cget('text'))
app.destroy()
