import copy
import json
import os
import os.path as osp
import re
import shutil
import sys
import random

from pjtools.configurator import AutoConfigurator
from PyQt5.QtWidgets import QApplication

from playground.registry import GAME_REGISTRY
from playground.utils import set_random_seed
from playground.state_code import GameStatus


class Generator:

    def __init__(self, base_cfg):
        cfg = AutoConfigurator.fromfile(base_cfg)
        self.benchmark_setting = cfg.benchmark_setting
        self.seed = set_random_seed()
        self.sample_size = self.benchmark_setting.sample_size

    def generate_benchmark(self):
        for task in self.benchmark_setting.offline_task:
            for game in self.benchmark_setting.games:
                save_path = osp.join(self.benchmark_setting.benchmark_path,
                                     task, game)
                if not osp.exists(save_path):
                    os.makedirs(save_path)
                if osp.exists(osp.join(save_path, 'annotation.json')):
                    print(
                        f'Benchmark data for {task} in {game} has been found.')
                else:
                    self.render(task, game, save_path)

    def render(self, task, game, save_path):
        game_cfg = AutoConfigurator.fromfile(f'configs/games/{game}.py')
        app = QApplication(sys.argv)  # noqa
        if task == 'perceive':
            self.render_perceive(game_cfg, save_path)
        elif task == 'rule':
            self.render_rule(game_cfg, save_path)
        elif task == 'qa':
            self.render_qa(game_cfg, save_path)
        elif task == 'forward_dynamics':
            self._dispatch(task, game_cfg, save_path)
        elif task == 'inverse_dynamics':
            self._dispatch(task, game_cfg, save_path)
        elif task == 'reward_modeling':
            self._dispatch(task, game_cfg, save_path)
        else:
            raise ValueError(f'Invalid task: {task}')

    # ================================================================
    # Dispatcher
    # ================================================================

    def _dispatch(self, task, game_cfg, save_path):
        """Route to game-specific renderer: _render_{task}_{game_name}."""
        method_name = f'_render_{task}_{game_cfg.game_name}'
        renderer = getattr(self, method_name, None)
        if renderer is None:
            raise NotImplementedError(
                f'{task} not implemented for {game_cfg.game_name}. '
                f'Expected method: {method_name}()')
        renderer(game_cfg, save_path)

    # ================================================================
    # Forward Dynamics — TicTacToe
    # ================================================================

    def _render_forward_dynamics_tictactoe(self, game_cfg, save_path):
        """Generate forward dynamics MCQ data for TicTacToe."""
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []

        for i in range(self.sample_size):
            game = game_class(game_cfg)

            # Get initial state and action (board is still in BEFORE state)
            dynamics_data = game.get_forward_dynamics_state()

            # Capture screenshot of ACTUAL initial state (s_t)
            screenshot_before = game.get_screenshot()
            screenshot_before.save(osp.join(save_path, f'{i:07d}_before.jpg'))

            # NOW execute the move for choice 0
            if dynamics_data['is_valid']:
                game.input_move(dynamics_data['action'])
                next_state = game.logic._board_to_matrix()
            else:
                next_state = None  # Invalid move, no change

            # Generate 4 choices
            choices, correct_index = self._generate_mcq_choices_tictactoe(
                game, game_class, game_cfg, dynamics_data, next_state,
                save_path, i)

            annotation = {
                'file_before': f'{i:07d}_before.jpg',
                'action': dynamics_data['action'],
                'gt': {
                    'current_state': dynamics_data['current_state'],
                    'action': dynamics_data['action'],
                    'is_valid': dynamics_data['is_valid'],
                    'correct_index': correct_index,
                    'choices': choices
                }
            }
            annotations.append(annotation)

            if (i + 1) % 100 == 0:
                print(
                    f'Forward dynamics tictactoe: {i + 1}/{self.sample_size}')

        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump({
                'task': 'forward_dynamics',
                'game': game_cfg.game_name,
                'annotations': annotations,
            }, json_file)

    def _generate_mcq_choices_tictactoe(self, game, game_class, game_cfg,
                                        dynamics_data, next_state, save_path,
                                        i):
        """Generate 4 MCQ choices for TicTacToe forward dynamics."""
        choices = []

        # Choice 0: Correct answer
        if dynamics_data['is_valid']:
            correct_screenshot = game.get_screenshot()
            correct_screenshot.save(
                osp.join(save_path, f'{i:07d}_choice_0.jpg'))
            choices.append({
                'action': dynamics_data['action'],
                'next_state': next_state,
                'file': f'{i:07d}_choice_0.jpg',
                'description': 'Correct transition'
            })
        else:
            game.logic.board = dynamics_data['current_board'].copy()
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_choice_0.jpg'))
            choices.append({
                'action': dynamics_data['action'],
                'next_state': dynamics_data['current_state'],
                'file': f'{i:07d}_choice_0.jpg',
                'description': 'Invalid move - no change'
            })

        # Choice 1: Different action from same initial state
        game2 = game_class(game_cfg)
        game2.logic.board = dynamics_data['current_board'].copy()
        game2.logic.status = GameStatus.IN_PROGRESS
        game2.logic.is_finish = False
        game2.logic.winner = None
        game2.renderer = None

        valid_moves = dynamics_data.get('valid_moves', [])
        different_moves = [
            m for m in valid_moves if m != dynamics_data['action']
        ]

        if different_moves:
            alt_action = random.choice(different_moves)
        else:
            all_moves = [
                'A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3'
            ]
            possible = [m for m in all_moves if m != dynamics_data['action']]
            alt_action = random.choice(possible) if possible else 'B2'

        game2.input_move(alt_action)
        alt_next_state = game2.logic._board_to_matrix()

        screenshot = game2.get_screenshot()
        screenshot.save(osp.join(save_path, f'{i:07d}_choice_1.jpg'))
        choices.append({
            'action': alt_action,
            'next_state': alt_next_state,
            'file': f'{i:07d}_choice_1.jpg',
            'description': 'Different action'
        })

        # Choice 2: Random VALID game state
        game3 = game_class(game_cfg)
        rule_state, _ = game3.get_rule_state()
        screenshot = game3.get_screenshot()
        screenshot.save(osp.join(save_path, f'{i:07d}_choice_2.jpg'))
        choices.append({
            'action': 'N/A',
            'next_state': rule_state,
            'file': f'{i:07d}_choice_2.jpg',
            'description': 'Random unrelated state'
        })

        # Choice 3: Invalid game image (impossible state)
        game4 = game_class(game_cfg)
        game4.logic.board = ['X'] * 9
        screenshot = game4.get_screenshot()
        screenshot.save(osp.join(save_path, f'{i:07d}_choice_3.jpg'))
        choices.append({
            'action': 'N/A',
            'next_state': [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
            'file': f'{i:07d}_choice_3.jpg',
            'description': 'Invalid/impossible game state'
        })

        # Shuffle choices and rename files to match
        indices = [0, 1, 2, 3]
        random.shuffle(indices)
        shuffled_choices = [choices[idx] for idx in indices]
        correct_index = indices.index(0)

        for new_idx, old_idx in enumerate(indices):
            old_file = osp.join(save_path, f'{i:07d}_choice_{old_idx}.jpg')
            new_file = osp.join(save_path, f'{i:07d}_shuffled_{new_idx}.jpg')
            shutil.copy(old_file, new_file)
        for new_idx in range(4):
            os.replace(
                osp.join(save_path, f'{i:07d}_shuffled_{new_idx}.jpg'),
                osp.join(save_path, f'{i:07d}_choice_{new_idx}.jpg'))
        for new_idx, choice in enumerate(shuffled_choices):
            choice['file'] = f'{i:07d}_choice_{new_idx}.jpg'

        return shuffled_choices, correct_index

    # ================================================================
    # Forward Dynamics — Sudoku
    # ================================================================

    def _render_forward_dynamics_sudoku(self, game_cfg, save_path):
        """Generate forward dynamics MCQ data for Sudoku."""
        game_class = GAME_REGISTRY.get('sudoku')
        annotations = []

        for i in range(self.sample_size):
            game = game_class(game_cfg)
            dynamics_data = game.get_forward_dynamics_state()

            # === Screenshot BEFORE (state s_t) ===
            game.logic.puzzle = copy.deepcopy(dynamics_data['current_state'])
            game.logic.assigned = copy.deepcopy(dynamics_data['assigned'])
            game.renderer = None
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_before.jpg'))

            # === Choice 0: Correct next state ===
            if dynamics_data['is_valid']:
                game.logic.puzzle = copy.deepcopy(dynamics_data['next_state'])
                game.renderer = None
                game.get_screenshot().save(
                    osp.join(save_path, f'{i:07d}_choice_0.jpg'))
            else:
                game.logic.puzzle = copy.deepcopy(
                    dynamics_data['current_state'])
                game.renderer = None
                game.get_screenshot().save(
                    osp.join(save_path, f'{i:07d}_choice_0.jpg'))

            # === Choice 1: Different valid action applied ===
            other_valid = [
                m for m in dynamics_data['valid_moves']
                if m != dynamics_data['action']
            ]
            if other_valid:
                alt_action = random.choice(other_valid)
                match = re.match(r'([A-I])(\d)\s(\d)', alt_action)
                row = ord(match.group(1)) - ord('A')
                col = int(match.group(2)) - 1
                num = int(match.group(3))

                alt_state = copy.deepcopy(dynamics_data['current_state'])
                alt_state[row][col] = num

                game.logic.puzzle = alt_state
                game.renderer = None
                game.get_screenshot().save(
                    osp.join(save_path, f'{i:07d}_choice_1.jpg'))
            else:
                alt_state = copy.deepcopy(dynamics_data['current_state'])
                game.logic.puzzle = alt_state
                game.renderer = None
                game.get_screenshot().save(
                    osp.join(save_path, f'{i:07d}_choice_1.jpg'))

            # === Choice 2: Right number, wrong cell ===
            wrong_cell_state = copy.deepcopy(dynamics_data['current_state'])
            match = re.match(r'([A-I])(\d)\s(\d)', dynamics_data['action'])
            action_row = ord(match.group(1)) - ord('A')
            action_col = int(match.group(2)) - 1
            action_num = int(match.group(3))

            empty_cells = [(y, x) for y in range(9) for x in range(9)
                           if wrong_cell_state[y][x] == 0
                           and (y, x) != (action_row, action_col)]
            if empty_cells:
                wr, wc = random.choice(empty_cells)
                wrong_cell_state[wr][wc] = action_num

            game.logic.puzzle = wrong_cell_state
            game.logic.assigned = copy.deepcopy(dynamics_data['assigned'])
            game.renderer = None
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_choice_2.jpg'))

            # === Choice 3: Invalid board (violates Sudoku constraints) ===
            invalid_state = copy.deepcopy(dynamics_data['current_state'])
            invalid_state[action_row][action_col] = action_num
            same_row_empty = [x for x in range(9)
                              if invalid_state[action_row][x] == 0
                              and x != action_col]
            if same_row_empty:
                dup_col = random.choice(same_row_empty)
                invalid_state[action_row][dup_col] = action_num

            game.logic.puzzle = invalid_state
            game.logic.assigned = copy.deepcopy(dynamics_data['assigned'])
            game.renderer = None
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_choice_3.jpg'))

            # === Shuffle choices and rename files ===
            indices = [0, 1, 2, 3]
            random.shuffle(indices)
            correct_index = indices.index(0)

            for new_idx, old_idx in enumerate(indices):
                old_file = osp.join(save_path,
                                    f'{i:07d}_choice_{old_idx}.jpg')
                new_file = osp.join(save_path,
                                    f'{i:07d}_shuffled_{new_idx}.jpg')
                shutil.copy(old_file, new_file)
            for new_idx in range(4):
                os.replace(
                    osp.join(save_path, f'{i:07d}_shuffled_{new_idx}.jpg'),
                    osp.join(save_path, f'{i:07d}_choice_{new_idx}.jpg'))

            annotations.append({
                'file_before': f'{i:07d}_before.jpg',
                'choices': [f'{i:07d}_choice_{n}.jpg' for n in range(4)],
                'gt': {
                    'correct_index': correct_index,
                    'action': dynamics_data['action'],
                    'is_valid': dynamics_data['is_valid'],
                }
            })

            if (i + 1) % 100 == 0:
                print(
                    f'Forward dynamics sudoku: {i + 1}/{self.sample_size}')

        with open(osp.join(save_path, 'annotation.json'), 'w') as f:
            json.dump(
                {
                    'task': 'forward_dynamics',
                    'game': 'sudoku',
                    'annotations': annotations
                }, f, indent=2)

        print(f'Forward dynamics sudoku benchmark generated: {save_path}')

    # ================================================================
    # Inverse Dynamics — TicTacToe
    # ================================================================

    def _render_inverse_dynamics_tictactoe(self, game_cfg, save_path):
        """Generate inverse dynamics data for TicTacToe."""
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []

        for i in range(self.sample_size):
            game = game_class(game_cfg)

            inverse_data = game.get_inverse_dynamics_state()

            # Screenshot 1: BEFORE state (s_t)
            game.logic.board = self._tictactoe_state_to_board(
                inverse_data['state_before'], game.logic.opponent)
            screenshot_before = game.get_screenshot()
            screenshot_before.save(
                osp.join(save_path, f'{i:07d}_before.jpg'))

            # Screenshot 2: AFTER state (s_t+1)
            game.logic.board = self._tictactoe_state_to_board(
                inverse_data['state_after'], game.logic.opponent)
            screenshot_after = game.get_screenshot()
            screenshot_after.save(
                osp.join(save_path, f'{i:07d}_after.jpg'))

            # Create multiple choice options
            all_options = [inverse_data['action_taken']
                           ] + inverse_data['all_distractors']
            random.shuffle(all_options)
            correct_index = all_options.index(inverse_data['action_taken'])

            annotation = {
                'file_before': f'{i:07d}_before.jpg',
                'file_after': f'{i:07d}_after.jpg',
                'gt': {
                    'state_before': inverse_data['state_before'],
                    'state_after': inverse_data['state_after'],
                    'action_taken': inverse_data['action_taken'],
                    'all_options': all_options,
                    'correct_index': correct_index,
                    'valid_distractors': inverse_data['valid_distractors'],
                    'invalid_distractor': inverse_data['invalid_distractor'],
                    'player_symbol': inverse_data['player_symbol']
                }
            }
            annotations.append(annotation)

            if (i + 1) % 100 == 0:
                print(
                    f'Inverse dynamics tictactoe: {i + 1}/{self.sample_size}')

        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'inverse_dynamics',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file, indent=2)

        print(f'Inverse dynamics tictactoe benchmark generated: {save_path}')

    # ================================================================
    # Inverse Dynamics — Sudoku
    # ================================================================

    def _render_inverse_dynamics_sudoku(self, game_cfg, save_path):
        """Generate inverse dynamics data for Sudoku."""
        game_class = GAME_REGISTRY.get('sudoku')
        annotations = []

        for i in range(self.sample_size):
            game = game_class(game_cfg)
            inverse_data = game.get_inverse_dynamics_state()

            # Screenshot BEFORE (s_t)
            game.logic.puzzle = copy.deepcopy(inverse_data['state_before'])
            game.logic.assigned = copy.deepcopy(inverse_data['assigned'])
            game.renderer = None
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_before.jpg'))

            # Screenshot AFTER (s_t+1)
            game.logic.puzzle = copy.deepcopy(inverse_data['state_after'])
            game.renderer = None
            game.get_screenshot().save(
                osp.join(save_path, f'{i:07d}_after.jpg'))

            # Create MCQ options (text, not images)
            all_options = [inverse_data['action_taken']
                           ] + inverse_data['all_distractors']
            random.shuffle(all_options)
            correct_index = all_options.index(inverse_data['action_taken'])

            annotation = {
                'file_before': f'{i:07d}_before.jpg',
                'file_after': f'{i:07d}_after.jpg',
                'gt': {
                    'state_before': inverse_data['state_before'],
                    'state_after': inverse_data['state_after'],
                    'action_taken': inverse_data['action_taken'],
                    'all_options': all_options,
                    'correct_index': correct_index,
                    'valid_distractors': inverse_data['valid_distractors'],
                    'invalid_distractor': inverse_data['invalid_distractor'],
                }
            }
            annotations.append(annotation)

            if (i + 1) % 100 == 0:
                print(
                    f'Inverse dynamics sudoku: {i + 1}/{self.sample_size}')

        with open(osp.join(save_path, 'annotation.json'), 'w') as f:
            json.dump({
                'task': 'inverse_dynamics',
                'game': 'sudoku',
                'annotations': annotations
            }, f, indent=2)

        print(f'Inverse dynamics sudoku benchmark generated: {save_path}')

    # ================================================================
    # Reward Modeling — TicTacToe
    # ================================================================

    def _render_reward_modeling_tictactoe(self, game_cfg, save_path):
        """Generate reward modeling data for TicTacToe."""
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []

        for i in range(self.sample_size):
            game = game_class(game_cfg)

            reward_data = game.get_reward_modeling_state()

            screenshot = game.get_screenshot()
            screenshot.save(osp.join(save_path, f'{i:07d}.jpg'))

            choices = [
                {'value': 0, 'label': 'No immediate reward'},
                {'value': 1, 'label': 'Positive reward (winning move)'},
                {'value': -1,
                 'label': 'Negative reward (allows opponent win)'},
                {'value': 'uncertain', 'label': 'Uncertain (stochastic)'}
            ]

            correct_index = None
            for idx, choice in enumerate(choices):
                if choice['value'] == reward_data['reward']:
                    correct_index = idx
                    break

            annotation = {
                'file': f'{i:07d}.jpg',
                'gt': {
                    'state': reward_data['state'],
                    'action': reward_data['action'],
                    'reward': reward_data['reward'],
                    'move_type': reward_data['move_type'],
                    'correct_index': correct_index,
                    'choices': choices
                }
            }
            annotations.append(annotation)

            if (i + 1) % 100 == 0:
                print(
                    f'Reward modeling tictactoe: {i + 1}/{self.sample_size}')

        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'reward_modeling',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file, indent=2)

        print(f'Reward modeling tictactoe benchmark generated: {save_path}')

    # ================================================================
    # Helpers — TicTacToe
    # ================================================================

    def _tictactoe_state_to_board(self, state_matrix, opponent_symbol='X'):
        """Convert TicTacToe state matrix back to board list for rendering.

        Args:
            state_matrix: 3x3 matrix with values 1 (X), 0 (O), -1 (empty)
            opponent_symbol: The player's symbol

        Returns:
            list: Board representation compatible with game logic
        """
        board = []
        cell_counter = 1

        for row in state_matrix:
            for cell in row:
                if cell == 1:
                    board.append('X')
                elif cell == 0:
                    board.append('O')
                else:
                    board.append(cell_counter)
                cell_counter += 1

        return board

    # ================================================================
    # Shared renderers (game-agnostic tasks)
    # ================================================================

    def render_perceive(self, game_cfg, save_path):
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []
        for i in range(self.sample_size):
            game = game_class(game_cfg)
            gt = game.get_random_state()
            screenshot = game.get_screenshot()
            screenshot.save(osp.join(save_path, f'{i:07d}.jpg'))
            annotation = {
                'file': f'{i:07d}.jpg',
                'gt': gt,
            }
            annotations.append(annotation)
        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'perceive',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file)

    def render_qa(self, game_cfg, save_path):
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []
        for i in range(self.sample_size):
            game = game_class(game_cfg)
            random_state = game.get_random_state()
            QA = game_cfg.qa(game_cfg.game_description['qa'])
            qa_pairs = QA.get_qa_pairs(random_state)
            example_qa = '\n'.join(f'Question: {q}\nAnswer: {a}'
                                   for q, a in qa_pairs[:QA.shot])
            question, answer = qa_pairs[QA.shot]
            screenshot = game.get_screenshot()
            screenshot.save(osp.join(save_path, f'{i:07d}.jpg'))
            annotation = {
                'file': f'{i:07d}.jpg',
                'gt': {
                    'question': question,
                    'answer': answer,
                    'example_qa': example_qa
                },
            }
            annotations.append(annotation)
        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'qa',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file)

    def render_rule(self, game_cfg, save_path):
        game_class = GAME_REGISTRY.get(game_cfg.game_name)
        annotations = []
        for i in range(self.sample_size):
            game = game_class(game_cfg)
            rule_state, valid_movements = game.get_rule_state()
            screenshot = game.get_screenshot()
            screenshot.save(osp.join(save_path, f'{i:07d}.jpg'))
            annotation = {
                'file': f'{i:07d}.jpg',
                'gt': {
                    'rule_state': rule_state,
                    'valid_movements': valid_movements
                },
            }
            annotations.append(annotation)
        with open(osp.join(save_path, 'annotation.json'), 'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'rule',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file)