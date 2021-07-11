#!/usr/bin/env python3

import json
import sys
import requests
import os

POSES = 'https://poses.live'


def read_token():
    with open("./token", 'r') as f:
        token = f.readline()
    return token


def header_auth(token):
    return {
        'Authorization':
            'Bearer ' + token
    }


def hello(token):
    r = requests.get(
        POSES + '/api/hello',
        headers=header_auth(token)
    )
    return r.json()


def post_solution(token, num_problem):
    SOLUTIONS_PATH = './solutions'
    filename = '{}.solution'.format(num_problem)
    filepath = '{}/{}'.format(SOLUTIONS_PATH, filename)
    with open(filepath, 'r') as f:
        solution = json.load(f)

    r = requests.post(
        POSES + '/api/problems/{}/solutions'.format(num_problem),
        headers=header_auth(token),
        json=solution
    )
    return r.json()


def save_pose_id(num_problem, pose_id):
    POSES_IDS_PATH = './poses_ids'
    filename = '{}.id'.format(num_problem)
    filepath = '{}/{}'.format(POSES_IDS_PATH, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            poses = json.load(f)
    else:
        poses = {'ids': []}

    poses['ids'].append(pose_id)

    with open(filepath, 'w') as f:
        json.dump(poses, f)


def read_last_pose_id(num_problem):
    POSES_IDS_PATH = './poses_ids'
    filename = '{}.id'.format(num_problem)
    filepath = '{}/{}'.format(POSES_IDS_PATH, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            poses = json.load(f)
    else:
        return -1

    return poses['ids'][-1]


def check_solution(token, num_problem):
    pose_id = read_last_pose_id(num_problem)

    r = requests.get(
        POSES + '/api/problems/{}/solutions/{}'.format(num_problem, pose_id),
        headers=header_auth(token),
    )
    return r.json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("not enough args")
        sys.exit(1)

    token = read_token()
    if sys.argv[1] == 'post':
        if len(sys.argv) < 3:
            print("not enough args")
            sys.exit(1)

        num = sys.argv[2]
        reply = post_solution(token, num)
        print(reply)
        if 'error' not in reply:
            save_pose_id(num, reply['id'])

    elif sys.argv[1] == 'check':
        if len(sys.argv) < 3:
            print("not enough args")
            sys.exit(1)

        num = sys.argv[2]

        print(check_solution(token, num))

    elif sys.argv[1] == 'hello':
        print(hello(token))
