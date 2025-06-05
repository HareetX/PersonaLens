#!/bin/bash

# Run the script to generate dialogue for all 1500 users
python3 -m src.generate_dialogue --start_index 0 --end_index 1499 

# Run the script to generate dialogue for a sample of 50 users for single-domain tasks
python3 -m src.generate_dialogue -s5

# Run the script to generate dialogue for a sample of 50 users using Claude 3.5 Haiku as assistant
python3 -m src.generate_dialogue -s5 -m claude-3-5-haiku-v1

# Run the script to generate dialogue for a sample of 50 users for single-domain tasks, including demographic information in the assistant prompt
python3 -m src.generate_dialogue -s5 -d

# Run the script to generate dialogue for a sample of 50 users for multi-domain tasks
python3 -m src.generate_dialogue_md -s5