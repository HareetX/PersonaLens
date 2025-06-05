#!/bin/bash

# gather evaluation results for personalization on Claude 3 Sonnet models
python3 -m util.gather_evaluation -s5 -m claude-3-sonnet-v1 -d personalization 

# gather evaluation results for personalization on Claude 3 Sonnet models for multi-domain tasks
python3 -m util.gather_evaluation -s5 -m claude-3-sonnet-v1 -d personalization -md

# gather evaluation results for user utterance naturalness on Claude 3 Sonnet models for single-domain tasks
python3 -m util.gather_evaluation -s5 -m claude-3-sonnet-v1 -d naturalness -f _user

# gather evaluation results for assistant utterance naturalness on Claude 3 Sonnet models for single-domain tasks
python3 -m util.gather_evaluation  -s5 -m claude-3-sonnet-v1 -d naturalness -f _asst