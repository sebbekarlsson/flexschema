# pyright: basic

import json
import os

def load_sample(sample_name: str) -> dict:
    CURRENT_DIR = os.path.realpath(os.path.dirname(__file__))
    SAMPLES_DIR = os.path.realpath(os.path.join(CURRENT_DIR, 'samples'))
    SAMPLE_PATH = os.path.realpath(os.path.join(SAMPLES_DIR, sample_name))

    file = open(SAMPLE_PATH, 'r')
    contents = file.read()
    file.close()
    
    return json.loads(contents)
