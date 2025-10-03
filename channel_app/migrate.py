import os
import sys
from alembic.config import Config
from alembic import command

def migrate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(base_dir, 'alembic.ini')

    alembic_cfg = Config(ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "database", "migrations"))

    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")

        sys.exit(1)