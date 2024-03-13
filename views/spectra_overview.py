import dearpygui.dearpygui as dpg
from models.state_plot import StatePlot
from viewmodels.spectra_overview_viewmodel import SpectraOverviewViewmodel
from utility.noop import noop


class SpectraOverview:  # TODO> List like project setup: Name, color buttons, show/hide buttons
    def __init__(self, viewmodel: SpectraOverviewViewmodel):
        self.viewmodel = viewmodel

    def add_spectrum(self, state_plot: StatePlot):
        with dpg.collapsing_header(label=state_plot.name):
            pass
