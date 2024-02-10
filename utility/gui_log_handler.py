import logging


class GuiLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry)