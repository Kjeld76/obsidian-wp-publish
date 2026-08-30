"""Store the application password once in the OS credential store."""
import getpass

import credentials

cfg = credentials.load_config()
pw = getpass.getpass("Application password for %s (%s): " % (cfg["site"], cfg["username"]))
credentials.set_app_password(cfg["site"], cfg["username"], pw)
print("Stored. The input was not logged anywhere.")
