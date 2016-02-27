import os
import pip


def get_requirements():
     # Establish the root path on the operating system
    basedir = os.path.abspath(os.path.dirname(__file__))
    # Change the working directory to the backup directory
    os.chdir(basedir)
    source_file = 'requirements.txt'
    pip.main(['install', '-r', source_file])
    return

get_requirements()

