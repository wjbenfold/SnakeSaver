from pathlib import Path
from time import sleep

import SnakeSaver as ss


def run_game():

    my_game = ss.Game(Path(__file__).parent / "rect_board.yml")

    boards = my_game.output()

    for board in boards:
        my_game.render(board)
        sleep(0.1)

    print("Game over")


if __name__ == "__main__":
    run_game()
