from colorama import Fore
from datetime import datetime


class SimpleLogger():
    def __init__(self, log_file: str, compatibility: bool = False):
        self.log_file = log_file
        self.compatibility = compatibility

    def logInfo(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'ℹ️' if not self.compatibility else "i"}] - {message}\n")
        print(f'{Fore.CYAN}[{'ℹ️' if not self.compatibility else "i"}] - {message}{Fore.RESET}')

    def logWarning(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'⚠️' if not self.compatibility else "!"}] - {message}\n")
        print(f'{Fore.YELLOW}[{'⚠️' if not self.compatibility else "!"}] - {message}{Fore.RESET}')

    def logError(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'❌' if not self.compatibility else "x"}] - {message}\n")
        print(f'{Fore.RED}[{'❌' if not self.compatibility else "x"}] - {message}{Fore.RESET}')

    def logSuccess(self, message: str):
        with open(self.log_file, 'a', encoding='UTF-8') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'✅' if not self.compatibility else "✓"}] - {message}\n")
        print(f'{Fore.GREEN}[{'✅' if not self.compatibility else "✓"}] - {message}{Fore.RESET}')

    def logDebug(self, message: str, encoding='UTF-8'):
        with open(self.log_file, 'a') as f:
            f.write(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [{'🐛' if not self.compatibility else "d"}] - {message}\n")
        print(f'{Fore.MAGENTA}[{'🐛' if not self.compatibility else "d"}] - {message}{Fore.RESET}')
