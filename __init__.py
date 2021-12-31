from collections.abc import Callable, Collection
from random import choice
from typing import Optional, Tuple, Any, KeysView, Union, List
import yaml

from .try_snake_saver import run_game as run_terminal_game

__all__ = ["run_terminal_game"]


class LogicError(Exception):
    pass


class ReadOnlyError(Exception):
    pass


class GameOver(Exception):
    pass


class GameWon(Exception):
    pass


class Cell:
    def __init__(self) -> None:
        super().__init__()
        self._is_food = False
        self._next_snake: Optional[Cell] = None
        self.connections: "dict[Cell, Optional[Cell]]"
        self.coordinates: Tuple[int, int]

    @property
    def is_snake(self) -> bool:
        return self.next_snake is not None

    @property
    def next_snake(self) -> "Optional[Cell]":
        return self._next_snake

    @next_snake.setter
    def next_snake(self, value: "Optional[Cell]") -> None:
        if self.is_food and value is not None:
            raise LogicError("Cell is food, cannot also be snake")
        self._next_snake = value

    @property
    def is_food(self) -> bool:
        return self._is_food

    @is_food.setter
    def is_food(self, value: bool) -> None:
        if self.is_snake and value:
            raise LogicError("Cell is snake, cannot also be food")
        self._is_food = value

    @property
    def neighbours(self) -> "KeysView[Cell]":
        return self.connections.keys()

    def __repr__(self) -> str:
        return str(self.coordinates)

    @classmethod
    def _is_passable(cls, possible_cell: "Optional[Cell]") -> bool:
        return not (possible_cell is None or possible_cell.is_snake)

    def find_next_snake_head(self) -> "Cell":
        for connection in self.neighbours:
            if connection.is_food:
                return connection
            if connection.is_snake:
                continue
            previous_cell = self
            current_cell = connection
            next_cell = current_cell.connections[previous_cell]
            seen_cells = set((previous_cell, current_cell))
            while self._is_passable(next_cell):
                assert next_cell is not None
                if next_cell in seen_cells:
                    break
                else:
                    seen_cells.add(next_cell)
                if next_cell.is_food:
                    return connection
                previous_cell = current_cell
                current_cell = next_cell
                next_cell = current_cell.connections[previous_cell]

        # Type safety
        if self.next_snake is None:
            raise LogicError("Current snake head has no next snake")

        # If you can't see food, go forwards
        forward_cell = self.connections[self.next_snake]
        if self._is_passable(forward_cell):
            assert forward_cell is not None
            return forward_cell
        else:
            option_list = list(
                filter(
                    lambda x: not x.is_snake,
                    self.neighbours
                )
            )
            if not option_list:
                raise GameOver("Snake head trapped")
            return choice(
                option_list
            )

    def get_next_snake_head(self) -> "Tuple[Cell, bool]":
        if self.next_snake is None:
            raise LogicError("Current snake head has no next snake")

        next_snake_head = self.find_next_snake_head()

        found_food = next_snake_head.is_food
        if found_food:
            next_snake_head.is_food = False
        else:
            self.next_snake.truncate_snake(self)

        next_snake_head.next_snake = self

        return next_snake_head, found_food

    def truncate_snake(self, snake_head) -> None:
        if self.next_snake is None:
            raise LogicError("Current snake head has no next snake")
        if self.next_snake.next_snake is None or self.next_snake.next_snake is snake_head:
            self.next_snake = None
        else:
            self.next_snake.truncate_snake(snake_head)


class CellHistory():
    def __init__(self, cell: Cell) -> None:
        self._cell: Cell = cell
        self.is_snake: bool = cell.is_snake
        self.is_food: bool = cell.is_food

    def __getattr__(self, value: str) -> Any:
        return self._cell.__getattribute__(value)


class Board:
    def __init__(self, config) -> None:
        self.config = config
        self.cells: "set[Cell]" = set()
        self.snake_head: Cell

    def choose_cell(self, filter_func: Callable[[Cell], bool] = lambda x: True, cells: Optional[Collection[Cell]] = None) -> Cell:
        if cells is not None:
            possible_cells = filter(filter_func, cells)
        else:
            possible_cells = filter(filter_func, self.cells)
        return choice(list(possible_cells))

    def set_initial_snake(self, length: int):
        self.snake_head = self.choose_cell()
        previous_snake = self.snake_head
        for _ in range(length):
            next_snake = self.choose_cell(lambda x: not x.is_snake, previous_snake.neighbours)
            previous_snake.next_snake = next_snake
            previous_snake = next_snake

    def assign_food(self):
        try:
            food_cell = self.choose_cell(lambda x: not x.is_snake)
        except IndexError:
            raise GameWon
        food_cell.is_food = True

    def advance(self):
        self.snake_head, food_found = self.snake_head.get_next_snake_head()
        if food_found:
            self.assign_food()

    def freeze_state(self):
        return BoardHistory(self)


class BoardHistory:
    def __init__(self, board: Board) -> None:
        self.board = board
        self.cells: "set[CellHistory]" = set()
        for cell in board.cells:
            self.cells.add(CellHistory(cell))

    def render(self):
        self.board.render_cells(self.cells)

    def __getattr__(self, value: str) -> Any:
        return self._cell.__getattribute__(value)


class RectBoard(Board):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.set_up_cells()
        self.set_initial_snake(self.config["initial_snake_length"])
        self.assign_food()

    def set_up_cells(self) -> None:
        width = self.config["dimensions"]["width"]
        height = self.config["dimensions"]["height"]

        for _ in range(width * height):
            self.cells.add(Cell())

        cell_list = list(self.cells)

        for ind, cell in enumerate(cell_list):

            cell_connections: dict[Cell, Optional[Cell]] = {}

            x_coord = ind % width

            if x_coord == 0:
                cell_connections[cell_list[ind + 1]] = None
            elif x_coord == width - 1:
                cell_connections[cell_list[ind - 1]] = None
            else:
                cell_connections[cell_list[ind + 1]] = cell_list[ind - 1]
                cell_connections[cell_list[ind - 1]] = cell_list[ind + 1]

            y_coord = ind // width

            if y_coord == 0:
                cell_connections[cell_list[ind + width]] = None
            elif y_coord == height - 1:
                cell_connections[cell_list[ind - width]] = None
            else:
                cell_connections[cell_list[ind + width]] = cell_list[ind - width]
                cell_connections[cell_list[ind - width]] = cell_list[ind + width]

            cell.connections = cell_connections
            cell.coordinates = (x_coord, y_coord)

    def render_cells(self, cells: "Union[set[Cell], set[CellHistory]]") -> None:
        for y in range(self.config["dimensions"]["height"]):
            cell_chars = []
            this_row: List[Union[Cell, CellHistory]] = sorted(
                filter(
                    lambda c: c.coordinates[1] == y, cells
                ),
                key=lambda c: c.coordinates[0]
            )
            for cell in this_row:
                if cell.is_food:
                    cell_chars.append("F")
                elif cell.is_snake:
                    cell_chars.append("S")
                else:
                    cell_chars.append(".")
            print(" ".join(cell_chars))
        print()


class Game:
    def __init__(self, config_file) -> None:
        with open(config_file, "r") as cf:
            self.config = yaml.safe_load(cf)
        self.board = RectBoard(self.config["board"])

    def output(self) -> List[Board]:
        board_list = [self.board.freeze_state()]
        while True:
            try:
                self.board.advance()
            except (GameOver, GameWon):
                break
            board_list.append(self.board.freeze_state())
        return board_list

    def render(self, board: BoardHistory) -> None:
        self.board.render_cells(board.cells)
