from app import UbkgAuth
from pathlib import Path

application = UbkgAuth('ubkg-auth-app.cfg', Path(__file__).absolute().parent.parent.parent).app

if __name__ == '__main__':
    print('ubkg-auth starting...')
    application.run()
