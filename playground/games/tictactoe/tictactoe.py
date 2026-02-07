import random
import re
from random import sample

from PyQt5.QtGui import QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QMainWindow

from playground.games import BaseGame, BaseGameLogic
from playground.games.tictactoe.AI import Minimax
from playground.games.tictactoe.tictactoe_ui import Ui_MainWindow
from playground.registry import GAME_REGISTRY
from playground.state_code import GameStatus


class TicTacToeLogic(BaseGameLogic):
    """Logic for Tic Tac Toe game."""

    def __init__(self, game_cfg):
        self.game_cfg = game_cfg
        self.board = [i + 1 for i in range(9)]
        self.bot = None
        self.opponent = None
        self.winner = None
        self.is_finish = False
        self.status = GameStatus.IN_PROGRESS
        self.moves_history = []
        self._initialize_players()

    def _initialize_players(self):
        players = sample(['X', 'O'], 2)
        self.bot = players[0]
        self.opponent = players[1] if self.game_cfg.player_first else players[
            0]  # noqa
        self.bot = players[0] if self.game_cfg.player_first else players[1]

    def make_move(self, index, player):
        if self.board[index] not in ['X', 'O'] and not self.is_finish:
            self.board[index] = player
            self._check_winner()
            return True
        return False

    def _check_winner(self):
        win_positions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
                         (2, 5, 8), (0, 4, 8), (2, 4, 6)]
        for pos in win_positions:
            if self.board[pos[0]] == self.board[pos[1]] == self.board[pos[2]]:
                self.winner = self.board[pos[0]]
                self.is_finish = True
                self.status = GameStatus.WIN if self.winner == self.opponent else GameStatus.LOSE  # noqa
                return
        if all(cell in ['X', 'O'] for cell in self.board) and not self.winner:
            self.is_finish = True
            self.status = GameStatus.TIE

    def input_move(self, move):
        if self.status != GameStatus.IN_PROGRESS:
            return self.status
        col_map = {'1': 0, '2': 1, '3': 2}
        row_map = {'A': 0, 'B': 1, 'C': 2}
        match = re.match(r'([A-Ca-c])([1-3])|([1-3])([A-Ca-c])', move)
        if match:
            row = match.group(1).upper() if match.group(1) else match.group(
                4).upper()
            col = match.group(2) if match.group(2) else match.group(3)
            index = row_map[row] * 3 + col_map[col]
            if self.make_move(index, self.opponent):
                self.moves_history.append(move)
                return self.status
        self.status = GameStatus.INVALID_MOVE
        return self.status

    def get_game_status(self):
        return self.status

    def reset_board(self):
        self.board = [i + 1 for i in range(9)]
        self.winner = None
        self.is_finish = False
        self.status = GameStatus.IN_PROGRESS
        self.moves_history = []

    def get_random_state(self):
        self.reset_board()
        positions = [1, 0, -1]
        random_state = sample(positions * 3, 9)
        if not any(value == -1 for value in random_state):
            rand_index = random.randint(0, 8)
            random_state[rand_index] = -1
        for i, value in enumerate(random_state):
            if value == 1:
                self.board[i] = 'X'
            elif value == 0:
                self.board[i] = 'O'
        return [random_state[i:i + 3] for i in range(0, 9, 3)]

    def get_rule_state(self):
        self.reset_board()
        while True:
            positions = [-1] * 9
            x_count = random.randint(1, 5)
            o_count = x_count if random.choice([True, False]) else x_count - 1
            if o_count < 0:
                o_count = 0
            if x_count + o_count >= 9:
                continue
            positions[:x_count] = [1] * x_count
            positions[x_count:x_count + o_count] = [0] * o_count
            random.shuffle(positions)
            for i, val in enumerate(positions):
                if val == 1:
                    self.board[i] = 'X'
                elif val == 0:
                    self.board[i] = 'O'
            self._check_winner()
            if self.is_finish:
                self.reset_board()
                continue
            board_state = [positions[i:i + 3] for i in range(0, 9, 3)]
            valid_movements = []
            row_map = {0: 'A', 1: 'B', 2: 'C'}
            col_map = {0: '1', 1: '2', 2: '3'}
            for i, val in enumerate(positions):
                if val == -1:
                    r, c = divmod(i, 3)
                    move_str = row_map[r] + col_map[c]
                    valid_movements.append(move_str)
            return board_state, valid_movements

    def calculate_score(self):
        """Calculate score based on steps taken and game outcome."""
        player_steps = len(self.moves_history)
        base_score = player_steps * 10
        bonus_score = 0
        if self.status == GameStatus.WIN:
            bonus_score = 50
        elif self.status == GameStatus.TIE:
            bonus_score = 20
        total_score = base_score + bonus_score
        return total_score

    def parse_e2e(self, lmm_output):
        """Parse e2e output to a move."""
        match = re.search(r'Movement:\s*([A-Ca-c][1-3]|[1-3][A-Ca-c])',
                          lmm_output, re.IGNORECASE)
        if match:
            move = match.group(1).upper()
            if move[0].isdigit():
                move = move[1] + move[0]
            return move
        return GameStatus.INVALID_MOVE

 
    def get_forward_dynamics_state(self):
      """Generate state for forward dynamics task."""
      self.reset_board()
      
      # Create a valid in-progress game state
      board_state, valid_moves = self.get_rule_state()
      
      # All possible moves
      all_possible_moves = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']
      
      # 50% valid, 50% invalid move
      if random.choice([True, False]) and valid_moves:
          action = random.choice(valid_moves)
          is_valid = True
      else:
          occupied_moves = [m for m in all_possible_moves if m not in valid_moves]
          action = random.choice(occupied_moves) if occupied_moves else random.choice(all_possible_moves)
          is_valid = False
      
      # Save current state (BEFORE any move)
      current_board = self.board.copy()
      current_state = board_state
      
      # DON'T execute the move here - just return the state info
      # Let the benchmark code handle screenshot timing
      
      return {
          'current_state': current_state,
          'action': action,
          'is_valid': is_valid,
          'current_board': current_board,
          'valid_moves': valid_moves  # Add this for easier processing
      }
    
    def _board_to_matrix(self):
        """Convert board to 3x3 matrix representation."""
        matrix = []
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                cell = self.board[i + j]
                if cell == 'X':
                    row.append(1)
                elif cell == 'O':
                    row.append(0)
                else:
                    row.append(-1)
            matrix.append(row)
        return matrix


    def get_inverse_dynamics_state(self):
        """Generate state for inverse dynamics task."""
        self.reset_board()
        
        board_state_before, valid_moves = self.get_rule_state()
        
        if not valid_moves:
            return self.get_inverse_dynamics_state()
        
        if len(valid_moves) < 3:
          return self.get_inverse_dynamics_state()

        # Check 3: Must have at least 1 invalid move available
        all_possible_moves = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']
        occupied_moves = [m for m in all_possible_moves if m not in valid_moves]
        if not occupied_moves:
          return self.get_inverse_dynamics_state()

        # Save BOTH formats for before state
        board_before = self.board.copy()  # ← Add this
        current_state = board_state_before
        
        # Choose and apply action
        action_taken = random.choice(valid_moves)
        col_map = {'1': 0, '2': 1, '3': 2}
        row_map = {'A': 0, 'B': 1, 'C': 2}
        row = action_taken[0]
        col = action_taken[1]
        index = row_map[row] * 3 + col_map[col]
        self.board[index] = self.opponent
        
        # Save BOTH formats for after state
        board_after = self.board.copy()  # ← Add this
        next_state = self._board_to_matrix()
        
        # Generate distractors...
        other_valid_moves = [m for m in valid_moves if m != action_taken]
        invalid_move = random.choice(occupied_moves) if occupied_moves else None
        
        num_valid_distractors = min(2, len(other_valid_moves))
        sampled_valid_distractors = random.sample(other_valid_moves, num_valid_distractors) if other_valid_moves else []
        
        distractors = sampled_valid_distractors.copy()
        if invalid_move:
            distractors.append(invalid_move)
        random.shuffle(distractors)
        
        return {
            'state_before': current_state,
            'state_after': next_state,
            'board_before': board_before,   # ← Add this
            'board_after': board_after,     # ← Add this
            'action_taken': action_taken,
            'valid_distractors': sampled_valid_distractors,
            'invalid_distractor': invalid_move,
            'all_distractors': distractors,
            'player_symbol': self.opponent,
            'all_valid_moves_before': valid_moves
        }



    def _check_winning_move(self, board, index, player):
      """Check if placing player symbol at index results in a win."""
      # Simulate the move
      temp_board = board.copy()
      temp_board[index] = player
      
      # Check all win positions
      win_positions = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
                      (2, 5, 8), (0, 4, 8), (2, 4, 6)]
      for pos in win_positions:
          if temp_board[pos[0]] == temp_board[pos[1]] == temp_board[pos[2]] == player:
              return True
      return False

    def _get_valid_indices(self, board):
        """Get all empty cell indices."""
        return [i for i in range(9) if board[i] not in ['X', 'O']]

    def _has_opponent_winning_move(self, board, player):
        """Check if opponent has any winning move available after player's move."""
        opponent = 'O' if player == 'X' else 'X'
        valid_indices = self._get_valid_indices(board)
        
        for idx in valid_indices:
            if self._check_winning_move(board, idx, opponent):
                return True
        return False

    def get_reward_modeling_state(self):
        """Generate state for reward modeling task.
        
        Rewards:
        +1: Winning move (completes 3-in-a-row)
        -1: Valid move that allows opponent to win next turn
        0: Valid safe move OR invalid move
        """
        self.reset_board()
        
        board_state, valid_moves = self.get_rule_state()
        
        if not valid_moves:
            return self.get_reward_modeling_state()
        
        # Map moves to indices
        col_map = {'1': 0, '2': 1, '3': 2}
        row_map = {'A': 0, 'B': 1, 'C': 2}
        
        # Categorize all valid moves
        winning_moves = []
        blunder_moves = []  # Moves that let opponent win
        safe_moves = []
        
        for move in valid_moves:
            row = move[0]
            col = move[1]
            idx = row_map[row] * 3 + col_map[col]
            
            # Check if this is a winning move
            if self._check_winning_move(self.board, idx, self.opponent):
                winning_moves.append(move)
            else:
                # Simulate the move and check if opponent can win
                temp_board = self.board.copy()
                temp_board[idx] = self.opponent
                
                if self._has_opponent_winning_move(temp_board, self.opponent):
                    blunder_moves.append(move)
                else:
                    safe_moves.append(move)
        
        # Get invalid moves
        all_possible_moves = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']
        invalid_moves = [m for m in all_possible_moves if m not in valid_moves]
        
        # Create move pool with their rewards
        move_pool = []
        if winning_moves:
            move_pool.append(('winning', winning_moves, 1))
        if blunder_moves:
            move_pool.append(('blunder', blunder_moves, -1))
        if safe_moves:
            move_pool.append(('safe', safe_moves, 0))
        if invalid_moves:
            move_pool.append(('invalid', invalid_moves, 0))
        
        # If we don't have enough variety, retry
        if len(move_pool) < 2:
            return self.get_reward_modeling_state()
        
        # Sample a move type
        move_type, moves, reward = random.choice(move_pool)
        action = random.choice(moves)
        
        return {
            'state': board_state,
            'action': action,
            'reward': reward,
            'move_type': move_type,  # For debugging
            'board_state': self.board.copy(),
            'player_symbol': self.opponent
        }

class TicTacToeRenderer(QMainWindow):
    """Renderer for Tic Tac Toe UI."""

    def __init__(self, logic):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.logic = logic
        self.select_font = QFont()
        self.select_font.setPointSize(35)
        self._update_ui()



    def _update_ui(self):
        color_map = {'X': 'red', 'O': 'blue'}
        color = color_map.get(self.logic.opponent, 'black')
        self.ui.label_2.setText(
            f'You are playing as <span style="color:{color}">{self.logic.opponent}</span>'  # noqa
        )
        for i, cell in enumerate(self.logic.board):
            button = self.ui.buttons[i]
            if cell in ['X', 'O']:
                button.setFont(self.select_font)
                button.setText(cell)
                button.setStyleSheet('color:blue' if cell ==
                                     'O' else 'color:red')
            else:
                button.setText('')
                button.setStyleSheet('')

    def get_screenshot(self):
        board_width = 500
        board_height = 600
        screenshot = QPixmap(board_width, board_height)
        painter = QPainter(screenshot)
        self.render(painter)
        painter.end()
        return screenshot


@GAME_REGISTRY.register('tictactoe')
class TicTacToe(BaseGame):
    AI_component = True

    def __init__(self, game_cfg):
        super().__init__(game_cfg)
        self.logic = TicTacToeLogic(game_cfg)
        self.renderer = None
        self.minimax = Minimax(
            self.logic.bot,
            self.logic.opponent) if game_cfg.player_first else None
        if not game_cfg.player_first:
            self.ai_move()

    def get_screenshot(self):
        if self.renderer is None:
            self.renderer = TicTacToeRenderer(self.logic)
        self.renderer._update_ui()
        return self.renderer.get_screenshot()

    def input_move(self, move):
        return self.logic.input_move(move)

    def get_game_status(self):
        return self.logic.get_game_status()

    def get_random_state(self):
        return self.logic.get_random_state()

    def get_rule_state(self):
        return self.logic.get_rule_state()


    def get_forward_dynamics_state(self):
        """Expose forward dynamics state generation."""
        return self.logic.get_forward_dynamics_state()

    def get_inverse_dynamics_state(self):
        """Expose inverse dynamics state generation."""
        return self.logic.get_inverse_dynamics_state()  

    def get_reward_modeling_state(self):
        """Expose reward modeling state generation."""
        return self.logic.get_reward_modeling_state()
        
    def ai_move(self):
        if not self.AI_component or self.logic.is_finish:
            return None
        game_match = self.minimax.generate_2d(self.logic.board)
        move_index = self.minimax.find_best_move(game_match)
        if self.logic.make_move(move_index, self.logic.bot):
            return f'{chr(65 + move_index // 3)}{move_index % 3 + 1}'
        return None

    def calculate_score(self):
        return self.logic.calculate_score()

    def parse_e2e(self, lmm_output):
        return self.logic.parse_e2e(lmm_output)
