from imslib.core import run

from game import MainWidget

if __name__ == "__main__":
    
    level_data_path = 'level_data/demo_level_2.json'

    run(
        MainWidget(
            level_data_path = level_data_path
        )
    )