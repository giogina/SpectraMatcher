class MenuViewModel:
    def __init__(self, project):
        self.exitCallback = None
        self.project = project

    def setExitCallback(self, callback):
        self.exitCallback = callback

    def OnOpen(self, event):
        # Event handler for the Open Project menu item
        pass

    def OnSave(self, event):
        self.project.save()

    def OnExit(self, event):
        if self.exitCallback:
            self.exitCallback()


