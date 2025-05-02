#!/usr/bin/env python3
import os
import sys
import pty
import shlex

from config import RUN_MANUAL

def run(cmd_args):
    """
    1) מטעה את הכלי לחשוב שהוא בריצה ידנית (PTY).
    2) עובר ע”י bash -lc ומוסיף ENV NO_COLOR=1 כדי לבטל יצירת קודי צבע.
    """

    # מכינים מחרוזת אחת עם כל הארגומנטים מצוטטים
    cmd = " ".join(shlex.quote(a) for a in cmd_args)

    # מוסיפים ENV שישבית כל יצירת ANSI-color בכלי
    # ומגדירים טרמינל מינימלי
    full = f"export NO_COLOR=1 TERM=dumb; {cmd}"

    # אם יש wrapper חיצוני (לדוגמה: "script -q /dev/stdout -c"), נשתמש בו
    if RUN_MANUAL:
        wrapper = RUN_MANUAL if isinstance(RUN_MANUAL, (list, tuple)) else shlex.split(RUN_MANUAL)
        # מצרפים את הפקודה המלאה כ־single string
        argv = wrapper + [full]
    else:
        # אחרת פשוט נעבור דרך bash -lc בתוך PTY
        argv = ["bash", "-lc", full]

    # לבסוף, מריצים ב־PTY אמיתי
    pty.spawn(argv)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <tool> [args…]")
        sys.exit(1)
    run(sys.argv[1:])
