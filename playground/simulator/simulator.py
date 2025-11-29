import os
import os.path as osp
import re
import imageio
import torch

from playground.registry import GAME_REGISTRY
from playground.state_code import GameStatus


class GameSimulator:

    def __init__(self,
                 game_cfg,
                 agent,
                 seed,
                 save_path,
                 task,
                 step_counter=0,
                 log_file=None):
        self.game_name = game_cfg.game_name
        self.max_trials = game_cfg.maximum_trials
        self.game_instance = None
        self.current_game_dir = save_path
        self.task = task
        self.step_counter = step_counter
        self.trial = 0
        self.agent = agent
        self.seed = seed
        self.display = game_cfg.display
        self.game_cfg = game_cfg
        self.log_file = log_file

    def log(self, message):
        """Log a message to the game log."""
        with open(self.log_file, 'a') as f:
            f.write(message + '\n')
            f.flush()
        print(message)

    def make_video(self):
        """Make a video from the game screenshots."""
        images = []
        for file_name in sorted(os.listdir(self.current_game_dir)):
            if file_name.endswith('.jpg') and file_name.startswith('step_'):
                images.append(os.path.join(self.current_game_dir, file_name))

        if not images:
            print('No images found to make a video.')
            return

        video_path = os.path.join(self.current_game_dir, 'game_video.mp4')
        writer = imageio.get_writer(video_path, fps=1)

        for image in images:
            writer.append_data(imageio.imread(image))

        writer.close()
        print(f'Video saved as {video_path}')

    def get_screenshot(self):
        """Get the current game state screenshot."""
        if not self.game_instance:
            raise ValueError(
                'No game instance. Call new_game() to start a new game.')

        screenshot = self.game_instance.get_screenshot()
        if screenshot:
            filename = f'step_{self.step_counter:07d}.jpg'
            filepath = os.path.join(self.current_game_dir, filename)
            screenshot.save(filepath)
            print(f'Screenshot saved as {filepath}')
            self.step_counter += 1
            return filepath
        return None

    def input_move(self, move):
        """Input a move into the game."""
        if not self.game_instance:
            raise ValueError(
                'No game instance. Call new_game() to start a new game.')
        try:
            result = self.game_instance.input_move(move)
        except:  # noqa
            result = GameStatus.INVALID_MOVE
        return result

    def get_game_status(self):
        """Get the current status of the game."""
        if not self.game_instance:
            raise ValueError(
                'No game instance. Call new_game() to start a new game.')
        return self.game_instance.get_game_status()

    def perceive(self, batch):
        """Run the game simulation in perception mode."""
        if not self.agent:
            raise ValueError('No agent set. Call set_agent() to set an agent.')

        if self.game_instance is None:
            self.new_game()

        prompt = self.game_cfg.game_description[self.task]
        screenshot_path = batch['screenshot_path']
        gt = batch['gt']

        if screenshot_path:
            try:
                lmm_output = self.agent.get_decision(screenshot_path, prompt)
            except Exception as e:
                lmm_output = None
                self.log(f'Failed to get decision from LMM: {e}')

            self.log(f'LMM Output: {lmm_output}')
            self.log(f'Ground truth: {gt}')
            return dict(raw=lmm_output)
        else:
            raise ValueError('Failed to get screenshot.')
    
    
    # def perceive(self, batch):
    #     """Run the game simulation in perception mode."""
    #     if not self.agent:
    #         raise ValueError('No agent set. Call set_agent() to set an agent.')
    #     if self.game_instance is None:
    #         self.new_game()
        
    #     prompt = self.game_cfg.game_description[self.task]
    #     test_image_path = batch['screenshot_path']
    #     example_image_path = 'example_image/0000100.jpg'
    #     gt = batch['gt']
        

    #     # Check which path is missing
    #     if not example_image_path:
    #         raise ValueError('Failed to get example image path from batch.')
    #     if not test_image_path:
    #         raise ValueError('Failed to get test image path.')

    #     if example_image_path and test_image_path:
    #         try:
    #             print("example_image_path:", example_image_path)
    #             print("test_image_path:", test_image_path)
    #             lmm_output = self.agent.get_decision(example_image_path, test_image_path, prompt)
    #         except Exception as e:
    #             lmm_output = None
    #             self.log(f'Failed to get decision from LMM: {e}')
    #         self.log(f'LMM Output: {lmm_output}')
    #         self.log(f'Ground truth: {gt}')
    #         return dict(raw=lmm_output)
    #     else:
    #         raise ValueError('Failed to get example or test image paths.')   



    def rule(self, batch):
        """Run the game simulation in rule mode"""
        if not self.agent:
            raise ValueError('No agent set. Call set_agent() to set an agent.')

        if self.game_instance is None:
            self.new_game()

        rule_state = batch['gt']['rule_state']
        screenshot_path = batch['screenshot_path']
        valid_movements = batch['gt']['valid_movements']

        prompt = self.game_cfg.game_description[self.task]
        try:
            lmm_output = self.agent.get_decision(screenshot_path, prompt)
        except Exception as e:
            lmm_output = None
            self.log(f'Failed to get decision from LMM: {e}')

        self.log(f'Game state: {rule_state}')
        self.log(f'LMM Output: {lmm_output}')
        self.log(f'Valid movements: {valid_movements}')
        return dict(raw=lmm_output)

    def qa(self, batch):
        """Run the game simulation in QA mode"""
        if not self.agent:
            raise ValueError('No agent set. Call set_agent() to set an agent.')

        if self.game_instance is None:
            self.new_game()

        question, gt = batch['gt']['question'], batch['gt']['answer']
        question = f'Question: {question}'
        QA = batch['game_cfg'].qa(batch['game_cfg'].game_description['qa'])
        prompt = QA.general_prompt.format(question=question)
        screenshot_path = batch['screenshot_path']

        if screenshot_path:
            try:
                lmm_output = self.agent.get_decision(screenshot_path, prompt)
            except Exception as e:
                lmm_output = None
                self.log(f'Failed to get decision from LMM: {e}')

            self.log(f'Prompt:\n {prompt}')
            self.log(f'LMM Output: {lmm_output}')
            self.log(f'Ground truth: {gt}')
            return dict(raw=lmm_output)
        else:
            raise ValueError('Failed to get screenshot.')





    def forward_dynamics(self, batch):
        """Run the game simulation in forward dynamics mode."""
        if not self.agent:
            raise ValueError('No agent set.')
        
        if self.game_instance is None:
            self.new_game()
        
        # Extract data
        action = batch['gt']['action']
        is_valid = batch['gt']['is_valid']
        current_state = batch['gt']['current_state']
        
        # Get image paths
        before_image = batch['screenshot_path']
        base_path = before_image.replace('_before.jpg', '')
        choice_images = [f'{base_path}_choice_{i}.jpg' for i in range(4)]
        all_images = [before_image] + choice_images
        print("=" * 50)
        print("DEBUG: Image paths being used:")
        print(f"Before image: {before_image}")
        print(f"Base path: {base_path}")
        for i, img in enumerate(choice_images):
            print(f"Choice {i}: {img}")
        print("=" * 50)
        
        # ✓ Use config prompt and format with action
        prompt_template = self.game_cfg.game_description[self.task]
        prompt = prompt_template.format(action=action)


        if all_images:
            try:
                if hasattr(self.agent, 'get_decision_multi_image'):
                    lmm_output = self.agent.get_decision_multi_image(all_images, prompt)
                else:
                    self.log("Warning: Agent doesn't support multi-image.")
                    lmm_output = self.agent.get_decision(before_image, prompt)
            except Exception as e:
                lmm_output = None
                self.log(f'Failed to get decision from LMM: {e}')
            
            self.log(f'Prompt:\n {prompt}')
            self.log(f'LMM Output: {lmm_output}')
            self.log(f'Ground truth: 0')
            return dict(raw=lmm_output)
        else:
            raise ValueError('Failed to get screenshot.')
        
        # try:
        #     if hasattr(self.agent, 'get_decision_multi_image'):
        #         lmm_output = self.agent.get_decision_multi_image(all_images, prompt)
        #     else:
        #         self.log("Warning: Agent doesn't support multi-image.")
        #         lmm_output = self.agent.get_decision(before_image, prompt)
        # except Exception as e:
        #     lmm_output = None
        #     self.log(f'Failed to get decision: {e}')
        
        # predicted_choice = self._parse_choice_number(lmm_output)
        # is_correct = (predicted_choice == 0)
        
        # # Log results
        # self.log(f'Action: {action}')
        # self.log(f'Is Valid: {is_valid}')
        # self.log(f'LMM Output: {lmm_output}')
        # self.log(f'Predicted: {predicted_choice}, Correct: 0')
        # self.log(f'Result: {"✓ CORRECT" if is_correct else "✗ INCORRECT"}')
        
        # return dict(
        #     raw=lmm_output,
        #     predicted_choice=predicted_choice,
        #     correct_choice=0,
        #     is_correct=is_correct,
        #     action=action,
        #     is_valid_action=is_valid
        # )

    # def _parse_choice_number(self, lmm_output):
    #     """
    #     Extract choice number (0-3) from LMM output.
        
    #     Handles various output formats:
    #     - "Answer: 2" -> 2
    #     - "The correct choice is 0" -> 0
    #     - "3" -> 3
    #     - "Choice 1 is correct" -> 1
        
    #     Args:
    #         lmm_output: Raw text output from the language model
            
    #     Returns:
    #         int: Extracted choice number (0-3), or -1 if parsing failed
    #     """
    #     if not lmm_output:
    #         return -1
        
    #     lmm_output_str = str(lmm_output)
        
    #     # Pattern 1: "Answer: X" or "Answer:X"
    #     match = re.search(r'Answer:\s*([0-3])', lmm_output_str, re.IGNORECASE)
    #     if match:
    #         return int(match.group(1))
        
    #     # Pattern 2: "Choice X" or "choice X"
    #     match = re.search(r'choice\s*([0-3])', lmm_output_str, re.IGNORECASE)
    #     if match:
    #         return int(match.group(1))
        
    #     # Pattern 3: Just a standalone number 0-3
    #     match = re.search(r'\b([0-3])\b', lmm_output_str)
    #     if match:
    #         return int(match.group(1))
        
    #     # Pattern 4: "The answer is X" or "It is X"
    #     match = re.search(r'(?:answer|it)\s+is\s+([0-3])', lmm_output_str, re.IGNORECASE)
    #     if match:
    #         return int(match.group(1))
        
    #     # If no valid number found, return -1 (invalid)
    #     self.log(f"Warning: Could not parse choice number from: {lmm_output_str[:100]}")
    #     return -1









    def new_game(self, step_counter=0):
        """Initialize a new game instance."""
        game_class = GAME_REGISTRY.get(self.game_name)
        if not game_class:
            raise ValueError(f"Game '{self.game_name}' is not registered.")

        self.game_instance = game_class(self.game_cfg)
        os.makedirs(self.current_game_dir, exist_ok=True)

        self.step_counter = step_counter
        self.trial = 0

        self.log_file = osp.join(self.current_game_dir, 'game.log')

    def run_e2e(self, batch):
        """Run the end-to-end game simulation with detailed history."""
        if not self.agent:
            raise ValueError('No agent set. Call set_agent() to set an agent.')

        self.new_game()
        prompt = self.game_cfg.game_description[self.task]
        invalid_attempts = 0
        last_screenshot_path = None
        history = []

        while self.get_game_status() == GameStatus.IN_PROGRESS:
            self.log(f'Step {self.step_counter}')
            if last_screenshot_path is None:
                last_screenshot_path = self.get_screenshot()
            screenshot_path = last_screenshot_path

            lmm_output = self.agent.get_decision(screenshot_path, prompt)
            move = self.game_instance.parse_e2e(lmm_output)
            self.log(f'LMM Output: {lmm_output}')
            self.log(f'Parsed movement: {move}')

            if move == GameStatus.INVALID_MOVE:
                result = GameStatus.INVALID_MOVE
            else:
                result = self.input_move(move)
            self.log(f'Move result: {result}')

            step_record = {
                'step': self.step_counter,
                'screenshot_path': screenshot_path,
                'llm_raw_output': lmm_output,
                'parsed_move':
                move if move != GameStatus.INVALID_MOVE else 'invalid',
                'move_result':
                result.value if isinstance(result, GameStatus) else result,
                'ai_move': None
            }

            if result == GameStatus.INVALID_MOVE:
                invalid_attempts += 1
                if move == GameStatus.INVALID_MOVE:
                    self.log('Invalid move detected.')
                else:
                    self.log('Invalid move executed.')

                if invalid_attempts >= self.max_trials:
                    self.log(
                        f'Max invalid trials ({self.max_trials}) reached.')
                    score = self.game_instance.calculate_score()
                    self.log(f'Game ended with score: {score}')
                    history.append(step_record)
                    return {
                        'score': score,
                        'steps': self.step_counter,
                        'history': history
                    }
                history.append(step_record)
                continue

            last_screenshot_path = self.get_screenshot()
            step_record['screenshot_path'] = last_screenshot_path

            if self.game_instance.AI_component:
                ai_move = self.game_instance.ai_move()
                if ai_move:
                    self.log(f'AI move: {ai_move}')
                    step_record['ai_move'] = ai_move
                    last_screenshot_path = self.get_screenshot()

            history.append(step_record)

            final_status = self.get_game_status()
            if final_status != GameStatus.IN_PROGRESS:
                break

        if last_screenshot_path is None or self.get_game_status(
        ) != GameStatus.IN_PROGRESS:
            last_screenshot_path = self.get_screenshot()

        score = self.game_instance.calculate_score()
        self.log(f'Game ended with status: {final_status}, Score: {score}')

        return {'score': score, 'steps': self.step_counter, 'history': history}

    def cleanup(self):
        if self.game_instance:
            del self.game_instance
        del self.agent
        torch.cuda.empty_cache()
