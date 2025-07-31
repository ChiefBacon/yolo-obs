from colorama import Fore
from datetime import datetime
from rich import print as rprint

class SimpleLogger():
    def __init__(self, log_file: str, compatibility: bool = False):
        self.log_file = log_file
        self.compatibility = compatibility

    def logInfo(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'ℹ️' if not self.compatibility else "i"}] - {message}\n")
        rprint(f'[cyan]{'ℹ️' if not self.compatibility else "i"} - {message}')

    def logWarning(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'⚠️' if not self.compatibility else "!"}] - {message}\n")
        rprint(f'[yellow]{'⚠️' if not self.compatibility else "!"} - {message}')

    def logError(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'❌' if not self.compatibility else "x"}] - {message}\n")
        print(f'[red]{'❌' if not self.compatibility else "x"} - {message}')

    def logSuccess(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'✅' if not self.compatibility else "✓"}] - {message}\n")
        rprint(f'[green]{'✅' if not self.compatibility else "✓"} - {message}')

    def logDebug(self, message: str, encoding='UTF-8'):
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'🐛' if not self.compatibility else "d"}] - {message}\n")
        print(f'[magenta]{'🐛' if not self.compatibility else "d"} - {message}')
