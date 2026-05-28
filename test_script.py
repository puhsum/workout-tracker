try:
    print("Script started")
    import os
    print("os imported")
    import re
    print("re imported")
    from datetime import datetime
    print("datetime imported")
    from pathlib import Path
    print("Path imported")
    print("All imports successful")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
