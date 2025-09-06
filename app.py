from flask import Flask, Response, request, jsonify
import json
import random
import os
from datetime import datetime

app = Flask(__name__)

# Game constants
CELL_SIZE = 20
BOARD_WIDTH = 20
BOARD_HEIGHT = 15
COLORS = {
    'bg': '#0d1117',      # GitHub dark theme
    'snake': '#238636',    # GitHub green
    'head': '#2ea043',     # Lighter green for head
    'food': '#da3633',     # GitHub red
    'grid': '#21262d'      # Subtle grid lines
}

# In-memory game state (use Redis/DB for production)
game_state = None

def get_initial_state():
    return {
        "board": [BOARD_WIDTH, BOARD_HEIGHT],
        "snake": [[10, 7], [9, 7], [8, 7]],
        "dir": "right",
        "food": [15, 7],
        "score": 0,
        "game_over": False,
        "last_move": datetime.now().isoformat()
    }

def generate_food(snake, board_w, board_h):
    """Generate random food position"""
    while True:
        x = random.randint(0, board_w - 1)
        y = random.randint(0, board_h - 1)
        if [x, y] not in snake:
            return [x, y]

def move_snake(state, direction):
    """Update snake position"""
    if state.get('game_over'):
        return state
    
    snake = state['snake'][:]
    head = snake[0][:]
    
    # Update direction (prevent reverse)
    valid_moves = {
        'up': state['dir'] != 'down',
        'down': state['dir'] != 'up', 
        'left': state['dir'] != 'right',
        'right': state['dir'] != 'left'
    }
    
    if direction in valid_moves and valid_moves[direction]:
        state['dir'] = direction
    
    # Move head
    if state['dir'] == 'up':
        head[1] -= 1
    elif state['dir'] == 'down':
        head[1] += 1
    elif state['dir'] == 'left':
        head[0] -= 1
    elif state['dir'] == 'right':
        head[0] += 1
    
    # Check collisions
    if (head[0] < 0 or head[0] >= BOARD_WIDTH or 
        head[1] < 0 or head[1] >= BOARD_HEIGHT or
        head in snake):
        state['game_over'] = True
        return state
    
    # Add new head
    snake.insert(0, head)
    
    # Check food
    if head == state['food']:
        state['score'] += 10
        state['food'] = generate_food(snake, BOARD_WIDTH, BOARD_HEIGHT)
    else:
        snake.pop()
    
    state['snake'] = snake
    state['last_move'] = datetime.now().isoformat()
    return state

def render_svg(state):
    """Generate SVG"""
    width = BOARD_WIDTH * CELL_SIZE
    height = BOARD_HEIGHT * CELL_SIZE
    
    svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
    <rect width="{width}" height="{height}" fill="{COLORS['bg']}"/>
'''
    
    # Grid
    for x in range(0, width + 1, CELL_SIZE):
        svg += f'    <line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{COLORS['grid']}" stroke-width="1" opacity="0.1"/>\n'
    for y in range(0, height + 1, CELL_SIZE):
        svg += f'    <line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{COLORS['grid']}" stroke-width="1" opacity="0.1"/>\n'
    
    # Food
    fx, fy = state['food']
    food_x = fx * CELL_SIZE + 2
    food_y = fy * CELL_SIZE + 2
    food_size = CELL_SIZE - 4
    svg += f'    <rect x="{food_x}" y="{food_y}" width="{food_size}" height="{food_size}" fill="{COLORS['food']}" rx="3"/>\n'
    
    # Snake
    for i, (sx, sy) in enumerate(state['snake']):
        snake_x = sx * CELL_SIZE + 1
        snake_y = sy * CELL_SIZE + 1
        snake_size = CELL_SIZE - 2
        color = COLORS['head'] if i == 0 else COLORS['snake']
        opacity = '1.0' if i == 0 else f'{max(0.6, 1.0 - i * 0.05)}'
        
        svg += f'    <rect x="{snake_x}" y="{snake_y}" width="{snake_size}" height="{snake_size}" fill="{color}" opacity="{opacity}" rx="2"/>\n'
    
    # Game over overlay
    if state.get('game_over'):
        svg += f'''    <rect x="0" y="0" width="{width}" height="{height}" fill="black" opacity="0.7"/>
    <text x="{width//2}" y="{height//2 - 20}" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="24" font-weight="bold">GAME OVER</text>
    <text x="{width//2}" y="{height//2 + 10}" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="16">Score: {state['score']}</text>
    <text x="{width//2}" y="{height//2 + 35}" text-anchor="middle" fill="{COLORS['snake']}" font-family="Arial, sans-serif" font-size="12">Click any direction to restart</text>
'''
    else:
        # Score
        svg += f'    <text x="10" y="{height - 10}" fill="{COLORS['snake']}" font-family="Arial, sans-serif" font-size="14" font-weight="bold">Score: {state["score"]}</text>\n'
    
    svg += '</svg>'
    return svg

@app.route('/game.svg')
def get_game_svg():
    """Serve the game board as SVG"""
    global game_state
    if game_state is None:
        game_state = get_initial_state()
    
    svg_content = render_svg(game_state)
    return Response(svg_content, mimetype='image/svg+xml')

@app.route('/move/<direction>')
def move_game(direction):
    """API endpoint to move snake"""
    global game_state
    
    if game_state is None:
        game_state = get_initial_state()
    
    # Reset if game over
    if game_state.get('game_over'):
        game_state = get_initial_state()
        game_state['dir'] = direction
        game_state['food'] = generate_food(game_state['snake'], BOARD_WIDTH, BOARD_HEIGHT)
    
    # Validate direction
    if direction not in ['up', 'down', 'left', 'right']:
        return jsonify({'error': 'Invalid direction'}), 400
    
    # Move snake
    game_state = move_snake(game_state, direction)
    
    return jsonify({
        'success': True,
        'direction': direction,
        'score': game_state['score'],
        'game_over': game_state.get('game_over', False)
    })

@app.route('/status')
def get_status():
    """Get current game status"""
    global game_state
    if game_state is None:
        game_state = get_initial_state()
    
    return jsonify({
        'score': game_state['score'],
        'direction': game_state['dir'],
        'game_over': game_state.get('game_over', False),
        'last_move': game_state.get('last_move'),
        'snake_length': len(game_state['snake'])
    })

@app.route('/reset')
def reset_game():
    """Reset the game"""
    global game_state
    game_state = get_initial_state()
    game_state['food'] = generate_food(game_state['snake'], BOARD_WIDTH, BOARD_HEIGHT)
    
    # Check for redirect parameter
    redirect_url = request.args.get('redirect')
    if redirect_url:
        from flask import redirect
        return redirect(redirect_url)
    
    return jsonify({'success': True, 'message': 'Game reset'})

@app.route('/')
def home():
    """API documentation"""
    return '''
    <h1>🐍 Snake Game API</h1>
    <h2>Endpoints:</h2>
    <ul>
        <li><code>GET /game.svg</code> - Game board SVG</li>
        <li><code>GET /move/&lt;direction&gt;</code> - Move snake (up/down/left/right)</li>
        <li><code>GET /status</code> - Game status JSON</li>
        <li><code>GET /reset</code> - Reset game</li>
    </ul>
    
    <h2>Test the API:</h2>
    <a href="/move/right">Move Right</a> | 
    <a href="/move/up">Move Up</a> | 
    <a href="/move/left">Move Left</a> | 
    <a href="/move/down">Move Down</a><br><br>
    <a href="/game.svg">View Game Board</a> | 
    <a href="/status">Game Status</a> | 
    <a href="/reset">Reset Game</a>
    '''

if __name__ == '__main__':
    # Initialize game
    game_state = get_initial_state()
    game_state['food'] = generate_food(game_state['snake'], BOARD_WIDTH, BOARD_HEIGHT)
    
    # Run server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)