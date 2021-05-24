import os
import sqlite3

from . import proc

DEFSIZ = 1000
SIZE_ENV = "HISTSIZE"
HISTORY_FN = "history.db"

class History():
    __schema = """
        CREATE TABLE IF NOT EXISTS history (exe TEXT, entry TEXT)
    """

    def __init__(self):
        # XXX: Maybe consult os.environ["HISTFILE"]
        if "XDG_DATA_DIR" in os.environ:
            data_dir = os.environ["XDG_DATA_DIR"]
        else:
            data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share')

        data_dir = os.path.join(data_dir, "saneterm")
        os.makedirs(data_dir, exist_ok=True)

        histfile = os.path.join(data_dir, HISTORY_FN)
        self.histsize = int(os.environ[SIZE_ENV]) if SIZE_ENV in os.environ else DEFSIZ

        self.__con = sqlite3.connect(histfile)
        self.__cur = self.__con.cursor()

        self.__cur.execute(self.__schema)

    def close(self):
        self.__con.close()

    def add_entry(self, fd, entry):
        entry = entry.rstrip('\n')
        if len(entry) == 0:
            return
        exe = self.__get_exec(fd)

        # Insert new entry into table and make sure the **total** amount
        # of entries in the entire table does not exceed self.histsize.
        # If this value is exceeded, remove the first (i.e. oldest) entries.
        self.__cur.execute("INSERT INTO history VALUES (?, ?)", (exe, entry))
        self.__cur.execute("""
                DELETE FROM history WHERE ( SELECT count(*) FROM history ) > :max
                    AND rowid IN (
                        SELECT rowid FROM history ORDER BY rowid ASC LIMIT
                            (( SELECT count(*) FROM history ) - :max )
                    );
                """, {"max": self.histsize});

        self.__con.commit()

    def get_entry(self, fd, relidx):
        exe = self.__get_exec(fd)

        self.__cur.execute("""
                SELECT entry FROM history WHERE exe=:exe LIMIT 1 OFFSET
                    (( SELECT count(*) FROM history WHERE exe=:exe ) - :relidx);
                """, {"exe": exe, "relidx": relidx})

        res = self.__cur.fetchone()
        if res is None:
            return None

        return res[0]

    def __get_exec(self, fd):
        pid = os.tcgetpgrp(fd);
        return proc.executable(pid)
