import wx


class Menu:
    def __init__(self, menuViewModel):
        self.menuViewModel = menuViewModel

    def build_main_menu(self, window):
        menuBar = wx.MenuBar()

        # Create a Menu
        fileMenu = wx.Menu()
        # Add Menu Items
        menuOpen = fileMenu.Append(wx.ID_OPEN, "&Open Project...", "Open project")
        menuSave = fileMenu.Append(wx.ID_SAVE, "&Save\tCtrl+S", "Save project")
        menuExit = fileMenu.Append(wx.ID_EXIT, "E&xit", "Exit")

        # Add the Menu to the Menu Bar
        menuBar.Append(fileMenu, "&Project")

        # Set the Menu Bar
        window.SetMenuBar(menuBar)

        # Bind Events to Menu Items
        window.Bind(wx.EVT_MENU, self.menuViewModel.OnOpen, menuOpen)
        window.Bind(wx.EVT_MENU, self.menuViewModel.OnSave, menuSave)
        window.Bind(wx.EVT_MENU, self.menuViewModel.OnExit, menuExit)


    def create_accelerators(self, window):
        acceleratorTable = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), wx.ID_SAVE),
            # add more shortcuts here
        ])
        window.SetAcceleratorTable(acceleratorTable)
