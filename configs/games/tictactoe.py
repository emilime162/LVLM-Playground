from playground.games import TicTacToeQuestionAnswering

_base_ = ['configs/base.py']

game_name = 'tictactoe'
game_description = dict(
    e2e=('Tic Tac Toe is played on a 3x3 grid. Players take turns placing X '
         'or O in the cells. The goal is to be the first to form an unbroken '
         'line of three marks horizontally, vertically, or diagonally. The '
         'game starts with an empty board, and the O player goes first. The '
         'grid is labeled with rows A to C and columns 1 to 3. You are '
         'playing as O, aiming to win by placing marks strategically. Each '
         'position can only be occupied by one mark, so do not choose a spot '
         'that is already taken. Based on the board state screenshots, please '
         'first observe the current situation, then carefully think and '
         'explain your strategy briefly, and finally output your movement for '
         'this status. Please strictly follow the following format:\n'
         'Observation: <observation>\n'
         'Strategy: <strategy>\n'
         'Movement: <position>\n'
         'where the observation should briefly summarize the current '
         'situation, the strategy is a brief explanation of how you plan to '
         'win the game, and the position can be any combination of rows A to '
         'C and columns 1 to 3, for example, A1, 2B, or c3.'),
    # Original version
    perceive=(
        'Tic Tac Toe is a game played on a 3x3 grid where players take turns '
        'placing X or O in the cells. Given a screenshot of the game board, '
        'please determine the current game state using a 3x3 matrix. In this '
        'matrix, an empty cell should be represented by -1, X should be '
        'represented by 1, and O should be represented by 0. Please strictly '
        'follow the format:\n'
        'Game State: <boardmatrix>\n'
        'where <boardmatrix> is a 3x3 matrix. For example,\n'
        'Game State: [[-1, -1, -1], [-1, -1, -1], [-1, -1, -1]]\n'
        'represents an empty board.'),

    # Cot
    # perceive = (
    #     'Please analyze the 3x3 Tic Tac Toe grid in the given image. You must follow a two-step process to generate the final game state matrix.'
    #     '\n\nSTEP 1: PERCEPTION (Internal Check)'
    #     '\nFirst, identify the content of each cell, reading from top-left to bottom-right (row by row). For this step, use the characters \'X\', \'O\', or \'E\' (to represent an Empty cell). List the results.'
    #     '\n\nSTEP 2: MAPPING and FINAL OUTPUT'
    #     '\nBased on the results of STEP 1, strictly convert the state into a 3x3 matrix using the following numerical mapping:'
    #     '\n- E (Empty cell) MUST be represented by -1.'
    #     '\n- X cell MUST be represented by 1.'
    #     '\n- O cell MUST be represented by 0.'
    #     '\n\nSTRICT FINAL OUTPUT FORMAT (You must include both sections):'
    #     '\n<STEP 1 Output - List the rows/contents here>'
    #     '\nGame State: <3x3 matrix>'
    # ), 


# in context learning
    # perceive=(
    #     'Tic Tac Toe is a game played on a 3x3 grid where players take turns '
    #     'placing X or O in the cells. Your task is to determine the current game state '
    #     'using a 3x3 matrix where:\n'
    #     '- Empty cell = -1\n'
    #     '- X = 1\n'
    #     '- O = 0\n\n'
        
    #     '=== EXAMPLE ===\n'
    #     'The first image shows an example Tic Tac Toe board. '
    #     'The correct game state for this example board is:\n'
    #     'Game State: [[-1, 1, 1], [0, 1, -1], [0, 0, 0]]\n\n'
        
    #     '=== YOUR TASK ===\n'
    #     'Now, analyze the second image (the test board). '
    #     'Determine its game state following the same format.\n'
    #     'Please strictly output:\n'
    #     'Game State: <boardmatrix>\n'
    #     'where <boardmatrix> is a 3x3 matrix representing the second image only.'),

    rule=(
        'Tic Tac Toe is played on a 3x3 grid. Players take turns placing X or '
        'O in the cells. The game starts with an empty board. The grid is '
        'labeled with rows A to C and columns 1 to 3. Each position can only '
        'be occupied by one mark. Based on the board state, '
        'please find an empty cell where you can place your next stone.\n'
        'Please strictly follow the following format:\n'
        'Movement: <position>\n'
        'where the position can be any combination of rows A to C and columns '
        '1 to 3, for example, A1, B2, or C3.'
    ),
    qa=(
        'Tic Tac Toe is a game played on a 3x3 grid where two players take '
        'turns placing X or O in the cells. The goal is to form a horizontal, '
        'vertical, or diagonal line with three of your own marks. The grid is '
        'labeled with rows A to C and columns 1 to 3. Please answer the '
        'following question based on the provided screenshot of the current '
        'game state:\n'
        '{question}\n'
        'Answer: <answer>\n'
        'where <answer> should be one of A, B, C, or D.'
    )
)

player_first = True
qa = TicTacToeQuestionAnswering
