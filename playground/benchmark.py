import json
import os
import os.path as osp
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
            self.render_forward_dynamics(game_cfg, save_path)
        else:
            raise ValueError(f'Invalid task: {task}')

      
    def render_forward_dynamics(self, game_cfg, save_path):
        """Generate forward dynamics MCQ data."""
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
            choices = self._generate_mcq_choices(game, game_class, game_cfg, 
                                                dynamics_data, next_state, save_path, i)
            
            annotation = {
                'file_before': f'{i:07d}_before.jpg',
                'action': dynamics_data['action'],
                'gt': {
                    'current_state': dynamics_data['current_state'],
                    'action': dynamics_data['action'],
                    'is_valid': dynamics_data['is_valid'],
                    'correct_choice': 0,
                    'choices': choices
                }
            }
            annotations.append(annotation)
        
        with open(osp.join(save_path, 'annotation.json'), 'w', encoding='utf-8') as json_file:
            json.dump({
                'task': 'forward_dynamics',
                'game': game_cfg.game_name,
                'annotations': annotations,
            }, json_file)
    
    def _generate_mcq_choices(self, game, game_class, game_cfg, dynamics_data, next_state, save_path, i):
        """Generate 4 MCQ choices."""
        choices = []
        
        # Choice 0: Correct answer
        # Game already has the move executed (if valid)
        if dynamics_data['is_valid']:
            correct_screenshot = game.get_screenshot()
            correct_screenshot.save(osp.join(save_path, f'{i:07d}_choice_0.jpg'))
            choices.append({
                'action': dynamics_data['action'],
                'next_state': next_state,
                'file': f'{i:07d}_choice_0.jpg',
                'description': 'Correct transition'
            })
        else:
            # Invalid move: restore original state for screenshot
            game.logic.board = dynamics_data['current_board'].copy()
            game.get_screenshot().save(osp.join(save_path, f'{i:07d}_choice_0.jpg'))
            choices.append({
                'action': dynamics_data['action'],
                'next_state': dynamics_data['current_state'],
                'file': f'{i:07d}_choice_0.jpg',
                'description': 'Invalid move - no change'
            })
                
        # # Choice 1: Different action (a'_t) and its next state
        # game2 = game_class(game_cfg)
        # game2.logic.board = dynamics_data['current_board'].copy()
        # dynamics_data2 = game2.get_forward_dynamics_state()
        # # Make sure it's a different action
        # while dynamics_data2['action'] == dynamics_data['action']:
        #     dynamics_data2 = game2.get_forward_dynamics_state()
        
        # if dynamics_data2['is_valid']:
        #     game2.input_move(dynamics_data2['action'])
        # screenshot = game2.get_screenshot()
        # screenshot.save(osp.join(save_path, f'{i:07d}_choice_1.jpg'))
        # choices.append({
        #     'action': dynamics_data2['action'],
        #     'next_state': dynamics_data2['next_state'],
        #     'file': f'{i:07d}_choice_1.jpg',
        #     'description': 'Different action'
        # })


        # Choice 1: Different action from same initial state
        game2 = game_class(game_cfg)
        game2.logic.board = dynamics_data['current_board'].copy()
        game2.logic.status = GameStatus.IN_PROGRESS
        game2.logic.is_finish = False
        game2.logic.winner = None
        game2.renderer = None  # Force renderer re-creation
        
        # Get valid moves and pick a different one
        valid_moves = dynamics_data.get('valid_moves', [])
        different_moves = [m for m in valid_moves if m != dynamics_data['action']]
        
        if different_moves:
            alt_action = random.choice(different_moves)
        else:
            # Fallback: pick any different move
            all_moves = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3']
            possible = [m for m in all_moves if m != dynamics_data['action']]
            alt_action = random.choice(possible) if possible else 'B2'  # Last resort
        
        # Execute the move
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


        # Choice 2: Random VALID game state (using get_rule_state)
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
        
        # Choice 3: Invalid game image (corrupted/impossible state)
        game4 = game_class(game_cfg)
        # Create impossible state: all X's or all O's
        game4.logic.board = ['X'] * 9  # Impossible state
        screenshot = game4.get_screenshot()
        screenshot.save(osp.join(save_path, f'{i:07d}_choice_3.jpg'))
        choices.append({
            'action': 'N/A',
            'next_state': [[1, 1, 1], [1, 1, 1], [1, 1, 1]],
            'file': f'{i:07d}_choice_3.jpg',
            'description': 'Invalid/impossible game state'
        })
        
        return choices


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
        with open(osp.join(save_path, 'annotation.json'),
                  'w',
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
        with open(osp.join(save_path, 'annotation.json'),
                  'w',
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
        with open(osp.join(save_path, 'annotation.json'),
                  'w',
                  encoding='utf-8') as json_file:
            json.dump(
                {
                    'task': 'rule',
                    'game': game_cfg.game_name,
                    'annotations': annotations,
                }, json_file)
