import wx
import wx.xrc
import wx.dataview
import logging
from models.settings_manager import SettingsManager
#  Changes vs version from wxFormBuilder:
#           Above imports;
#           .AddSpacer((0, 0), 1, wx.EXPAND, 5) -> .AddStretchSpacer(5)
#           Functions below
#           Settings in init
#           SetSizeHintsSz -> SetSizeHints

class StartupDashboard(wx.Frame):
    """Determine a project file path to open - either new / imported or already existing."""
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=u"Welcome - SpectraMatcher", pos=wx.DefaultPosition,
                          size=wx.Size(1000, 500), style=wx.CLOSE_BOX | wx.FRAME_SHAPED | wx.NO_BORDER,
                          name=u"welcome_dashboard")

        self.logger = logging.getLogger(__name__)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        self.settings = SettingsManager()
        self.palette = self.settings.get("palette", {"C0": [0, 0, 121], "C1": [48, 10, 120], "C2": [187, 187, 255]})
        self.SetBackgroundColour(self.getPaletteColour("C1"))
        self.projectPath = ""
        self.status = "None"
        self.recent = self.settings.get("recentProjects")

        DashboardbSizerH1 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_panel_dashboard_left = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.m_panel_dashboard_left.SetMinSize(wx.Size(250, -1))

        bSizerDashboardVLeft = wx.BoxSizer(wx.VERTICAL)

        # bSizerDashboardVLeft.AddSpacer((0, 0), 1, wx.EXPAND, 5)
        bSizerDashboardVLeft.AddStretchSpacer(5)

        self.m_staticWelcomeText = wx.StaticText(self.m_panel_dashboard_left, wx.ID_ANY, u"SpectraMatcher\nWelcome!",
                                                 wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.m_staticWelcomeText.Wrap(-1)
        self.m_staticWelcomeText.SetFont(wx.Font(26, 72, 93, 90, False, "Palatino Linotype"))
        self.m_staticWelcomeText.SetForegroundColour(wx.Colour(193, 193, 255))

        bSizerDashboardVLeft.Add(self.m_staticWelcomeText, 0, wx.ALL | wx.EXPAND, 5)

        # bSizerDashboardVLeft.AddSpacer((0, 0), 1, wx.EXPAND, 5)
        bSizerDashboardVLeft.AddStretchSpacer(5)

        self.m_panel_dashboard_left.SetSizer(bSizerDashboardVLeft)
        self.m_panel_dashboard_left.Layout()
        bSizerDashboardVLeft.Fit(self.m_panel_dashboard_left)
        DashboardbSizerH1.Add(self.m_panel_dashboard_left, 1, wx.EXPAND | wx.ALL, 5)

        self.m_panel_dashboard_right = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, -1), wx.TAB_TRAVERSAL)
        self.m_panel_dashboard_right.SetMinSize(wx.Size(550, -1))

        bSizerDashboardVRight = wx.BoxSizer(wx.VERTICAL)

        bSizerDashboardVRight.AddStretchSpacer(4)

        bSizerHDashboardButtons = wx.BoxSizer(wx.HORIZONTAL)

        bSizerHDashboardButtons.AddSpacer(6)
        self.m_button_new = wx.Button(self.m_panel_dashboard_right, wx.ID_ANY, u"&New Project...", wx.DefaultPosition,
                                      wx.Size(-1, 50), 0)
        self.formatButton(self.m_button_new)
        bSizerHDashboardButtons.Add(self.m_button_new, 3, wx.EXPAND, 5)

        bSizerHDashboardButtons.AddSpacer(12)

        self.m_button_open = wx.Button(self.m_panel_dashboard_right, wx.ID_ANY, u"&Open Project...", wx.DefaultPosition,
                                       wx.Size(-1, 50), 0)
        self.formatButton(self.m_button_open)
        bSizerHDashboardButtons.Add(self.m_button_open, 3, wx.EXPAND, 5)
        bSizerHDashboardButtons.AddSpacer(6)

        bSizerHDashboardButtons.AddStretchSpacer(1)

        bSizerDashboardVRight.Add(bSizerHDashboardButtons, 1, wx.EXPAND, 5)

        bSizerHRecents = wx.BoxSizer(wx.HORIZONTAL)

        bSizerVRecents = wx.BoxSizer(wx.VERTICAL)

        bSizerVRecents.AddSpacer(24)

        self.m_staticText1 = wx.StaticText(self.m_panel_dashboard_right, wx.ID_ANY, u"Recent projects:",
                                           wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_staticText1.Wrap(-1)
        self.m_staticText1.SetFont(wx.Font(12, 74, 90, 90, False, "Arial"))
        self.m_staticText1.SetForegroundColour(wx.Colour(221, 221, 255))

        bSizerVRecents.Add(self.m_staticText1, 0, wx.ALL, 5)

        self.m_dataViewRecentFiles = wx.dataview.DataViewListCtrl(self.m_panel_dashboard_right, wx.ID_ANY,
                                                              wx.DefaultPosition, wx.Size(-1, -1),
                                                              wx.dataview.DV_NO_HEADER | wx.dataview.DV_ROW_LINES | wx.dataview.DV_SINGLE | wx.HSCROLL)
        self.m_dataViewRecentFiles.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT))
        self.m_dataViewRecentFiles.SetBackgroundColour(wx.Colour(230, 230, 255))
        self.m_dataViewRecentFiles.SetMinSize(wx.Size(300, -1))

        bSizerVRecents.Add(self.m_dataViewRecentFiles, 3, wx.ALL | wx.EXPAND, 5)

        bSizerHOpenRecentButton = wx.BoxSizer(wx.HORIZONTAL)

        bSizerHOpenRecentButton.AddStretchSpacer(5)

        self.m_button_open_recent = wx.Button(self.m_panel_dashboard_right, wx.ID_ANY, u"Open Selected",
                                              wx.DefaultPosition, wx.Size(-1, 50), 0)
        self.m_button_open_recent.Enable(False)

        self.formatButton(self.m_button_open_recent)

        bSizerHOpenRecentButton.Add(self.m_button_open_recent, 0, wx.ALL, 5)

        bSizerVRecents.Add(bSizerHOpenRecentButton, 1, wx.EXPAND, 5)

        bSizerHRecents.Add(bSizerVRecents, 6, wx.EXPAND, 5)

        # bSizerHRecents.AddSpacer((0, 0), 1, wx.EXPAND, 0)
        bSizerHRecents.AddStretchSpacer(1)

        bSizerDashboardVRight.Add(bSizerHRecents, 1, wx.EXPAND, 5)

        bSizerDashboardVRight.AddStretchSpacer(3)

        self.m_panel_dashboard_right.SetSizer(bSizerDashboardVRight)
        self.m_panel_dashboard_right.Layout()
        bSizerDashboardVRight.Fit(self.m_panel_dashboard_right)
        DashboardbSizerH1.Add(self.m_panel_dashboard_right, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(DashboardbSizerH1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.populateRecent()

        # Connect Events
        self.m_button_new.Bind(wx.EVT_LEFT_UP, self.OnButtonNewClick)
        self.m_button_open.Bind(wx.EVT_LEFT_UP, self.OnButtonOpenClick)
        self.m_dataViewRecentFiles.Bind(wx.dataview.EVT_DATAVIEW_SELECTION_CHANGED, self.OnRecentProjectSelected)
        self.m_dataViewRecentFiles.Bind(wx.dataview.EVT_DATAVIEW_ITEM_ACTIVATED, self.OnRecentProjectActivated)
        self.m_button_open_recent.Bind(wx.EVT_LEFT_UP, self.OnButtonOpenRecentClick)

        self.logger.info(f"Dashboard init done.")
        self.Show()

    def __del__(self):
        pass

    def formatButton(self, button):
        button.SetForegroundColour(self.getPaletteColour("C0"))
        button.SetBackgroundColour(self.getPaletteColour("C2"))
        button.SetFont(wx.Font(12, 74, 90, 92, False, "Arial"))

    def getPaletteColour(self, key):
        if key in self.palette:
            return wx.Colour(self.palette[key][0],
                             self.palette[key][1],
                             self.palette[key][2],)
        else:
            return wx.Colour(0, 0, 0)

    def populateRecent(self):
        self.m_dataViewRecentFiles.AppendTextColumn("path")
        if self.recent:
            for recentPath in self.recent:
                self.m_dataViewRecentFiles.AppendItem([recentPath])
            self.m_dataViewRecentFiles.SetFocus()

    def OnButtonNewClick(self, event):
        # with wx.FileDialog(self, "New SpectraMatcher project", wildcard="SPM files (*.spm)|*.spm",
        #                    style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
        #
        #     if fileDialog.ShowModal() == wx.ID_CANCEL:
        #         return  # the user changed their mind
        #     path = fileDialog.GetPath()
        self.projectPath = ""
        self.status = "New"
        self.Close()

    def OnButtonOpenClick(self, event):
        with wx.FileDialog(self, "Open SpectraMatcher project", wildcard="SPM files (*.spm)|*.spm",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return  # the user changed their mind

            self.projectPath = fileDialog.GetPath()
            self.status = "Open"
            self.Close()

    def OnRecentProjectActivated(self, event):
        if self.recent:
            self.projectPath = self.recent[self.m_dataViewRecentFiles.GetSelectedRow()]
            self.status = "Open"
            self.Close()

    def OnRecentProjectSelected(self, event):
        self.m_button_open_recent.Enable(True)

    def OnButtonOpenRecentClick(self, event):
        self.OnRecentProjectActivated(event)

