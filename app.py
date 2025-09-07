from flask import Flask, Response, request, jsonify, redirect, url_for
import random, os
from datetime import datetime

app = Flask(__name__)

CELL_SIZE = 20
BOARD_WIDTH = 20
BOARD_HEIGHT = 15
COLORS = {
    'bg': '#0d1117',
    'snake': '#238636',
    'head': '#2ea043',
    'food': '#da3633',
    'grid': '#21262d'
}

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
    while True:
        x = random.randint(0, board_w - 1)
        y = random.randint(0, board_h - 1)
        if [x, y] not in snake:
            return [x, y]

def move_snake(state, direction):
    if state.get('game_over'):
        return state
    snake = state['snake'][:]
    head = snake[0][:]
    valid_moves = {
        'up': state['dir'] != 'down',
        'down': state['dir'] != 'up', 
        'left': state['dir'] != 'right',
        'right': state['dir'] != 'left'
    }
    if direction in valid_moves and valid_moves[direction]:
        state['dir'] = direction
    if state['dir'] == 'up': head[1] -= 1
    elif state['dir'] == 'down': head[1] += 1
    elif state['dir'] == 'left': head[0] -= 1
    elif state['dir'] == 'right': head[0] += 1
    if (head[0] < 0 or head[0] >= BOARD_WIDTH or head[1] < 0 or head[1] >= BOARD_HEIGHT or head in snake):
        state['game_over'] = True
        return state
    snake.insert(0, head)
    if head == state['food']:
        state['score'] += 10
        state['food'] = generate_food(snake, BOARD_WIDTH, BOARD_HEIGHT)
    else:
        snake.pop()
    state['snake'] = snake
    state['last_move'] = datetime.now().isoformat()
    return state

def render_svg(state):
    width, height = BOARD_WIDTH*CELL_SIZE, BOARD_HEIGHT*CELL_SIZE
    svg = f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<rect width="{width}" height="{height}" fill="{COLORS["bg"]}"/>'
    # grid lines
    for x in range(0, width+1, CELL_SIZE):
        svg += f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="{COLORS["grid"]}" stroke-width="1" opacity="0.1"/>'
    for y in range(0, height+1, CELL_SIZE):
        svg += f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="{COLORS["grid"]}" stroke-width="1" opacity="0.1"/>'
    # food
    fx, fy = state['food']
    svg += f'<rect x="{fx*CELL_SIZE+2}" y="{fy*CELL_SIZE+2}" width="{CELL_SIZE-4}" height="{CELL_SIZE-4}" fill="{COLORS["food"]}" rx="3"/>'
    # snake
    for i, (sx, sy) in enumerate(state['snake']):
        color = COLORS['head'] if i==0 else COLORS['snake']
        opacity = '1.0' if i==0 else f'{max(0.6, 1.0-i*0.05)}'
        svg += f'<rect x="{sx*CELL_SIZE+1}" y="{sy*CELL_SIZE+1}" width="{CELL_SIZE-2}" height="{CELL_SIZE-2}" fill="{color}" opacity="{opacity}" rx="2"/>'
    if state.get('game_over'):
        svg += f'<rect x="0" y="0" width="{width}" height="{height}" fill="black" opacity="0.7"/>'
        svg += f'<text x="{width//2}" y="{height//2-20}" text-anchor="middle" fill="white" font-size="24" font-weight="bold">GAME OVER</text>'
        svg += f'<text x="{width//2}" y="{height//2+10}" text-anchor="middle" fill="white" font-size="16">Score: {state["score"]}</text>'
    else:
        svg += f'<text x="10" y="{height-10}" fill="{COLORS["snake"]}" font-size="14" font-weight="bold">Score: {state["score"]}</text>'
    svg += '</svg>'
    return svg

@app.route('/board.svg')
def get_board_svg():
    global game_state
    if game_state is None:
        game_state = get_initial_state()
    svg = render_svg(game_state)
    # Append timestamp to bust cache
    timestamp = int(datetime.now().timestamp())
    return Response(svg, mimetype='image/svg+xml', headers={"Cache-Control": f"no-store, must-revalidate, max-age=0", "ETag": str(timestamp)})

@app.route('/move/<direction>')
def move_game(direction):
    global game_state
    if game_state is None:
        game_state = get_initial_state()
    if game_state.get('game_over'):
        game_state = get_initial_state()
        game_state['dir'] = direction
        game_state['food'] = generate_food(game_state['snake'], BOARD_WIDTH, BOARD_HEIGHT)
    if direction not in ['up','down','left','right']:
        return jsonify({'error':'Invalid direction'}),400
    game_state = move_snake(game_state, direction)
    redirect_url = request.args.get('redirect')
    if redirect_url:
        return redirect(redirect_url, code=303)
    return jsonify({'success': True, 'direction': direction, 'score': game_state['score'], 'game_over': game_state['game_over']})

# status, reset, home unchanged

if __name__ == '__main__':
    game_state = get_initial_state()
    game_state['food'] = generate_food(game_state['snake'], BOARD_WIDTH, BOARD_HEIGHT)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)
