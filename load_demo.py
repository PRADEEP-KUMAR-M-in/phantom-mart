# Puts the demo shop (or a clean empty database) into the app, in one step.
#
#   python sample_data/load_demo.py            load the demo shop (sample data)
#   python sample_data/load_demo.py --empty    go back to a clean, empty database
#   add --yes to skip the question
#
# If you already have a phantommart.db, a copy is saved in the backups folder first.
# Close the app before running this.

import datetime
import os
import shutil
import sys

from refresh_demo_dates import refresh_dates

here = os.path.dirname(os.path.abspath(__file__))
project = os.path.dirname(here)
target = os.path.join(project, "phantommart.db")
backups = os.path.join(project, "backups")

use_empty = "--empty" in sys.argv
skip_question = "--yes" in sys.argv

source = os.path.join(here, "phantommart_empty.db" if use_empty else "phantommart_demo.db")
if not os.path.exists(source):
    sys.exit(f"Could not find {os.path.basename(source)} in the sample_data folder.")

if os.path.exists(target):
    print("You already have a database:", target)
    print("It will be replaced with the", "EMPTY database." if use_empty else "DEMO shop.")
    print("A backup copy is saved in the backups folder first.")
    if not skip_question and input("Type yes to continue: ").strip().lower() != "yes":
        sys.exit("Nothing was changed.")

    os.makedirs(backups, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    saved = os.path.join(backups, f"before_load_{stamp}.db")
    shutil.copy2(target, saved)
    print("Backup saved:", saved)

shutil.copy2(source, target)

if not use_empty:
    print(refresh_dates(target))        # make the newest bills dated today

print()
print("Ready. Start the app with:  python main.py")
print("Log in as admin / admin123  (manager / mgr123, cashier / cash123)")
