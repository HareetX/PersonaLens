# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.  
# SPDX-License-Identifier: CC-BY-NC-4.0

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
import diskcache
from os import path
from time import sleep
import argparse
from util.evaluation_prompts import *


DOMAINS = ['Alarm', 'Books', 'Buses', 'Calendar', 'Events', 'Finance', 'Flights', 'Games', 'Hotels', 'Media', 'Messaging', 'Movies', 'Music', 'Rental Cars', 'Restaurants', 'Services', 'Shopping', 'Sports', 'Train', 'Travel']

BEDROCK_SERVICE = "bedrock-runtime"


model_id_dict = {
    "anthropic.claude-3-5-sonnet-20240620-v1:0": "claude-3-5-sonnet-v1",
    "us.anthropic.claude-3-opus-20240229-v1:0": "claude-3-opus-v1",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0": "claude-3-5-sonnet-v1",
    "anthropic.claude-3-sonnet-20240229-v1:0": "claude-3-sonnet-v1",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0": "claude-3-5-haiku-v1",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0": "claude-3-5-sonnet-v2",
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0": "claude-3-7-sonnet-v1",
    "meta.llama3-70b-instruct-v1:0": "llama-3-70b-instruct-v1",
    "us.meta.llama3-1-70b-instruct-v1:0": "llama-3-1-70b-instruct-v1",
    "us.meta.llama3-2-90b-instruct-v1:0": "llama-3-2-90b-instruct-v1",
    "us.meta.llama3-3-70b-instruct-v1:0": "llama-3-3-70b-instruct-v1",
    "us.meta.llama3-1-8b-instruct-v1:0": "llama-3-1-8b-instruct-v1",
    "mistral.mistral-7b-instruct-v0:2": "mistral-7b-instruct-v2",
    "mistral.mixtral-8x7b-instruct-v0:1": "mixtral-8x7b-instruct-v1"
}

model_id_reverse_dict = {
    "claude-3-5-sonnet-v1": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "claude-3-sonnet-v1": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-5-haiku-v1": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "claude-3-5-sonnet-v2": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-7-sonnet-v1": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "llama-3-70b-instruct-v1": "meta.llama3-70b-instruct-v1:0",
    "llama-3-1-70b-instruct-v1": "us.meta.llama3-1-70b-instruct-v1:0",
    "llama-3-3-70b-instruct-v1": "us.meta.llama3-3-70b-instruct-v1:0",
    "llama-3-1-8b-instruct-v1": "us.meta.llama3-1-8b-instruct-v1:0",
    "mistral-7b-instruct-v2": "mistral.mistral-7b-instruct-v0:2",
    "mixtral-8x7b-instruct-v1": "mistral.mixtral-8x7b-instruct-v0:1"
}

if "DATA_DIR" in os.environ:
    DATA_DIR = os.environ["DATA_DIR"]
else:
    DATA_DIR = path.join(os.getenv("HOME"), 'workspace', 'data')

CACHES_DIR = path.join(DATA_DIR, 'caches')

class ClaudeLLM:
    def __init__(self, model_id='anthropic.claude-3-sonnet-20240229-v1:0', region="us-east-1", max_tokens=512,
                 temperature=0.5, system_prompt="") -> None:
        self.model_id = model_id
        self.region = region
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.cache = diskcache.Cache(path.join(CACHES_DIR, model_id))
        self.__init_session()

    def __init_session(self):
        self.session = boto3.Session()
        self.client = self.session.client(
            BEDROCK_SERVICE,
            region_name=self.region
        )

    def __invoke(self, prompt):
        backoff_time = 0.5
        while True:
            try:
                body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                        "system": self.system_prompt,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", 
                                     "text": prompt
                                    }
                                ],
                            }
                        ],
                    }

                return self.client.invoke_model(
                    body=json.dumps(body),
                    modelId=self.model_id
                )
            except ClientError as e:
                code = e.response['Error']['Code']
                # print(e.response)
                if code == 'ThrottlingException':
                    logging.warning(f"[ThrottlingException] Waiting for ({backoff_time:.1f})s.")
                    sleep(backoff_time)
                    backoff_time *= 2
                elif code == 'ExpiredTokenException':
                    logging.warning(f"[ExpiredTokenException] Refreshing session security token.")
                elif code == 'ModelErrorException':
                    logging.warning(f'error calling {self.model_id}, trying again')
                    return self.__invoke(prompt)
                elif code == 'ServiceUnavailableException':
                    logging.warning(f'Service Unavailable error calling {self.model_id}, trying again')
                    sleep(backoff_time)
                    backoff_time *= 2
                    return self.__invoke(prompt)
                elif code == 'ModelTimeoutException':
                    logging.warning(f'Model timeout error calling {self.model_id}, trying again')
                    sleep(backoff_time)
                    backoff_time *= 2
                    return self.__invoke(prompt)
                else:
                    raise Exception(f"Unhandled boto ClientError: {code}")

    def invoke(self, prompt, use_caching=True):
        if prompt in self.cache and use_caching:
            completion = self.cache[prompt]
        else:
            response = self.__invoke(prompt)
            completion = json.loads(response.get('body').read())["content"][0]["text"]
            self.cache[prompt] = completion
        return completion

    def get_msg_body(self, prompt):
        body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self.system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", 
                                "text": prompt
                            }
                        ],
                    }
                ],
            }
        return body

    def single_turn_request(self, utterance):
        # return self.invoke(f"\n\nHuman:{utterance}\n\nAssistant:")
        return self.invoke(f"{utterance}", use_caching=False)

# Function to save the LLM answer to the specified path
def save_user_answer(user_id, task_id, answer, model_id_asst, model_id_eval, eval_dimension, evalname="", path="evaluation"):
    # Create the user-specific directory if it doesn't exist
    save_path = f"output/{path}/user{user_id}/{model_id_asst}/{eval_dimension}/{model_id_eval}"
    os.makedirs(save_path, exist_ok=True)
    
    # Save the answer to a file
    with open(os.path.join(save_path, f"{task_id}{evalname}.txt"), "w") as f:
        f.write(answer)



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M")
    parser = argparse.ArgumentParser(description="Generate personas for user profiles.")

    # Define arguments for start and end indices
    parser.add_argument("-s", "--start_index", type=int, default=0, help="The starting index of the user profiles.")
    parser.add_argument("-e", "--end_index", type=int, default=1499, help="The ending index of the user profiles.")
    parser.add_argument("-m", "--model_id_asst", type=str, default='claude-3-sonnet-v1', help="The model id of the assistant used in the dialogue generation.")
    parser.add_argument("-i", "--model_id_eval", type=str, default='claude-3-5-sonnet-v2', help="The model id of the judge for evaluating the dialogue.")
    parser.add_argument("-r", "--bedrock_region", type=str, default='us-west-2', help="The Bedrock region.")
    parser.add_argument("-s2", "--sample_20", action="store_true", help="Whether to use small sample of 20 users.")
    parser.add_argument("-s3", "--sample_30", action="store_true", help="Whether to use small sample of 30 users.")
    parser.add_argument("-s5", "--sample_50", action="store_true", help="Whether to use small sample of 50 users.")
    parser.add_argument("-s10", "--sample_100", action="store_true", help="Whether to use small sample of 100 users.")
    parser.add_argument("-l", "--icl", action="store_true", help="Whether to use in-context learning.")
    parser.add_argument("-p", "--icl_path", type=str, default="icl", help="Path for in-context learning experiment.")
    parser.add_argument("-a", "--assistant", action="store_true", help="Whether to run eval on assistant.")
    parser.add_argument("-md", "--multi_domain", action="store_true", help="Whether to run eval on multi-domain tasks.")
    parser.add_argument("-d", "--eval_dimension", type=str, default='naturalness', help="The evaluation dimension for the dialogue.")

    # Parse arguments
    args = parser.parse_args()

    llm = ClaudeLLM(
            model_id=model_id_reverse_dict[args.model_id_eval],
            region=args.bedrock_region,
            temperature=0, 
            max_tokens=4000)
    
    ratings = {}

    sample_20_idxs = [66, 132, 139, 207, 230, 340, 386, 389, 415, 428, 597, 746, 774, 854, 900, 1111, 1197, 1231, 1322, 1458]
    sample_30_idxs = [7, 66, 132, 139, 207, 230, 251, 313, 340, 376, 386, 389, 415, 428, 597, 746, 774, 788, 822, 854, 900, 1111, 1142, 1150, 1197, 1231, 1322, 1458, 1492, 1495]
    sample_50_idxs = [7, 53, 66, 107, 132, 139, 167, 195, 207, 230, 251, 313, 340, 376, 386, 389, 415, 418, 428, 439, 517, 532, 597, 630, 641, 660, 674, 701, 746, 774, 788, 802, 822, 854, 900, 1111, 1142, 1145, 1150, 1197, 1231, 1322, 1335, 1362, 1377, 1439, 1458, 1492, 1493, 1495]
    sample_100_idxs = [7, 21, 53, 66, 86, 107, 132, 139, 157, 166, 167, 168, 195, 207, 230, 248, 251, 312, 313, 340, 352, 363, 365, 376, 386, 389, 394, 415, 418, 428, 431, 439, 470, 482, 517, 532, 597, 619, 630, 641, 657, 659, 660, 664, 674, 686, 689, 701, 744, 745, 746, 774, 788, 802, 813, 822, 838, 840, 842, 847, 854, 857, 870, 878, 880, 900, 913, 928, 942, 954, 997, 1069, 1111, 1114, 1118, 1120, 1142, 1145, 1150, 1151, 1167, 1184, 1197, 1231, 1246, 1322, 1330, 1335, 1345, 1362, 1377, 1384, 1434, 1439, 1458, 1461, 1492, 1493, 1495, 1496]
    
    assert len(sample_30_idxs) == 30
    assert len(sample_50_idxs) == 50
    assert len(sample_100_idxs) == 100

    if args.sample_30:
        sample = sample_30_idxs
    elif args.sample_50:
        sample = sample_50_idxs
    elif args.sample_100:
        sample = sample_100_idxs
    elif args.sample_20:
        sample = sample_20_idxs
    else:
        sample = range(args.start_index, args.end_index + 1)

    assert args.eval_dimension in ["naturalness", "coherence", "task_completion", "personalization"]

    if args.eval_dimension == "naturalness":
        if args.assistant:
            evalname = "_asst"
            TEMPLATE_EVAL = EVAL_DIALOGUE_NATURALNESS_ASSISTANT
        else:
            evalname = "_user"
            TEMPLATE_EVAL = EVAL_DIALOGUE_NATURALNESS_USER
    elif args.eval_dimension == "coherence":
        if args.assistant:
            evalname = "_asst"
            TEMPLATE_EVAL = EVAL_DIALOGUE_COHERENCE_ASSISTANT
        else:
            evalname = "_user"
            TEMPLATE_EVAL = EVAL_DIALOGUE_COHERENCE_USER
    elif args.eval_dimension == "task_completion":
        evalname = ""
        TEMPLATE_EVAL = EVAL_DIALOGUE_TASK_COMPLETION
    elif args.eval_dimension == "personalization":
        evalname = ""
        TEMPLATE_EVAL = EVAL_DIALOGUE_PERSONALIZATION
    else:
        print(f"Your specified eval dimension {args.eval_dimension} is not matched.")
        exit()
    
    dialogue_path = "dialogue/"
    evaluation_path = "evaluation"
    
    count = 0
    inputs = []
    for i in sample:
        directory_path = f"output/{dialogue_path}/user{i}/{args.model_id_asst}"
        
        with open(f"data/profile/user{i}/profile.json") as f:
            user_profile = json.load(f)

        if args.multi_domain:
            with open(f"data/profile/user{i}/tasks_md.json") as f:
                tasks = json.load(f)
        else:
            with open(f"data/profile/user{i}/tasks.json") as f:
                tasks = json.load(f)
        
        for _, task in tasks.items():
            file_name = f"{task['task_id']}_dialogue.json"
            file_path = os.path.join(directory_path, file_name)
            with open(file_path) as f:
                data = json.load(f)

            task_id = data['task_id']
            relevant_domains = task['Relevant Domains']
            demographic_profile = user_profile['demographics']
            situation_context = task['situations']
            task_description = task['User Intent']
            
            # Format demographic profile
            demo_str = "\n".join([f"- {k}: {v}" for k, v in demographic_profile.items()])

            # Format situation context
            situation_str = "\n".join([f"- {k}: {v}" for k, v in situation_context.items()])
            
            # Format conversation
            dialogue_formatted = "\n".join([f"[{msg['role'].upper()}]: {msg['content']}" 
                                for msg in data['dialogue']])
            
            if args.multi_domain:
                # Format user preferences
                pref_str = ""
                for domain in relevant_domains:
                    pref_str += "\n"+domain+":\n"
                    pref_str += "\n".join([f"- {k}: {', '.join(map(str, v))}" if isinstance(v, list) else f"- {k}: {v}" for k, v in user_profile['affinities'][domain].items()])
                    pref_str += "\n"
    
                # Format interaction summary
                interaction_summary = ""
                for domain in relevant_domains:
                    interaction_summary += "\n<"+domain+">\n"
                    interaction_summary += user_profile['interactions'][domain]
                    interaction_summary += "\n</"+domain+">\n"

            else:
                user_affinity = user_profile['affinities'][relevant_domains[0]]
                interaction_summary = user_profile['interactions'][relevant_domains[0]]
                
                # Format user preferences
                pref_str = "\n".join([f"- {k}: {', '.join(map(str, v))}" if isinstance(v, list) else f"- {k}: {v}" for k, v in user_affinity.items()])
          

            if args.eval_dimension in ["naturalness", "coherence"]:
                evaluation = llm.single_turn_request(
                    TEMPLATE_EVAL.format(conversation=dialogue_formatted)
                )
            elif args.eval_dimension == "task_completion":
                evaluation = llm.single_turn_request(
                    TEMPLATE_EVAL.format(conversation=dialogue_formatted, goal=task['Task Goal'])
                )
            elif args.eval_dimension == "personalization":
            
                evaluation = llm.single_turn_request(
                    TEMPLATE_EVAL.format(
                        demographic_profile=demo_str,
                        user_affinity=pref_str,
                        task_description=task_description,
                        interaction_summary=interaction_summary,
                        situation_context=situation_str,
                        conversation=dialogue_formatted)
                )
           

            logging.info(f"User{i} {task_id} dialogue {args.eval_dimension} evaluation done.")
            
            # Save the answer for the current user
            save_user_answer(i, task_id, evaluation, model_id_asst=args.model_id_asst, model_id_eval=args.model_id_eval,
                             eval_dimension=args.eval_dimension, evalname=evalname, path=evaluation_path)
        
        logging.info(f"User{i} interaction evaluation saved.")
    
   

        

    

