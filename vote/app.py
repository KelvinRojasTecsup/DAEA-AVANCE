from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json
import logging
import math

option_a = os.getenv('OPTION_A', "Blues Traveler")
option_b = os.getenv('OPTION_B', "Broken Bells")
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

def calculate_cosine_similarity(A, B):
    valid_indices = [i for i, (x, y) in enumerate(zip(A, B)) if x is not None and y is not None]
    A_valid = [A[i] for i in valid_indices]
    B_valid = [B[i] for i in valid_indices]

    dot_product = sum(x * y for x, y in zip(A_valid, B_valid))
    norm_A = math.sqrt(sum(x**2 for x in A_valid))
    norm_B = math.sqrt(sum(y**2 for y in B_valid))

    similarity = dot_product / (norm_A * norm_B) if norm_A * norm_B != 0 else 0
    return similarity

@app.route("/", methods=['POST', 'GET'])
def hello():
    voter_id = request.cookies.get('voter_id')
    if not voter_id:
        voter_id = hex(random.getrandbits(64))[2:-1]

    similarity = None

    if request.method == 'POST':
        redis = get_redis()
        Blues_Traveler = [3.5, 2, 5, 3, 4, None, 5, 3]
        Broken_Bells = [2, 3.5, 1, 4, 4, 4.5, 2, None]

        similarity = calculate_cosine_similarity(Blues_Traveler, Broken_Bells)

        app.logger.info('Calculated cosine similarity: %s', similarity)
        data = json.dumps({'voter_id': voter_id, 'similarity': similarity})
        redis.rpush('similarities', data)

        if redis.exists('similarities'):
            app.logger.info('Data uploaded to Redis successfully')
        else:
            app.logger.error('Failed to upload data to Redis')

    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        hostname=hostname,
        similarity=similarity,
    ))
    resp.set_cookie('voter_id', voter_id)
    return resp

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)