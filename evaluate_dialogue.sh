#!/bin/bash

# Run the script to evaluate personalization for all 1500 users on dialogues generated with Claude 3 Sonnet as assistant 
python3 -m src.evaluate_dialogue --start_index 0 --end_index 1499 -m claude-3-sonnet-v1 -d personalization 

# Run the script to evaluate dialogue for a sample of 50 users for single-domain tasks
python3 -m src.evaluate_dialogue -s5 -m claude-3-sonnet-v1 -d personalization 

# Run the script to evaluate dialogue for a sample of 50 users for multi-domain tasks
python3 -m src.evaluate_dialogue -s5 -m claude-3-sonnet-v1 -d personalization -md

# Run the script to evaluate dialogue on naturalness of user for a sample of 50 users for single-domain tasks
python3 -m src.evaluate_dialogue -s5 -m claude-3-sonnet-v1 -d naturalness  

# Run the script to evaluate dialogue on naturalness of assistant for a sample of 50 users for single-domain tasks
python3 -m src.evaluate_dialogue -s5 -m claude-3-sonnet-v1 -d naturalness -a