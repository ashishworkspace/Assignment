import os

import boto3
from flask import Flask, jsonify, make_response, request, render_template

app = Flask(__name__)
iam = boto3.client("iam")


dynamodb = boto3.resource('dynamodb')

if os.environ.get('IS_OFFLINE'):
    dynamodb_client = boto3.client(
        'dynamodb', region_name='localhost', endpoint_url='http://localhost:8000'
    )

table = dynamodb.Table('users-table-data')
USERS_TABLE = os.environ['USERS_TABLE']

# this function is used to get data from IAM and add that record to DynamoDB
def syncIamUsersIntoDB():
    paginator = iam.get_paginator('list_users')
    for response in paginator.paginate():
        for user in response["Users"]:
            username = user['UserName']
            policy = iam.list_user_policies(UserName=username)
            table.put_item(
                Item={
                    'username': username,
                    f"{username}_policy": policy,
                    'status': 'added',
                }
            )


# Route to /useradd/<some-user-name> will add user to IAM
@app.route("/useradd/<string:username>")
def useradd(username):
    iam.create_user(UserName=username)
    policy = iam.list_user_policies(UserName=username)
    result = {
        "Name": username,
        "Status": "added"
    }
    table.put_item(
        Item={
            'username': username,
            f"{username}_policy": policy,
            'status': 'added',
        }
    )
    syncIamUsersIntoDB()
    return jsonify(result)


# Route to /userdelete/<some-user-name> will remove user form IAM
@app.route("/userdelete/<string:username>")
def userdelete(username):
    iam.delete_user(
        UserName=username
    )
    table.delete_item(
        Key={
            'username': username
        }
    )
    result = {
        "Name": username,
        "Status": "removed"
    }
    syncIamUsersIntoDB()
    return jsonify(result)


# Route to /userdetail/<some-user-name> will provide policy about that user
@app.route("/userdetail/<string:username>")
def userdetail(username):
    response = iam.get_user(
        UserName=username
    )
    policy = iam.list_user_policies(UserName=username)
    result = {
        username: response['User'],
        f"{username}_policy": policy
    }
    return jsonify(result)


# Route to /listuser will list all user from dynamodb
@app.route("/listuser")
def listuser():
    resp = table.scan(AttributesToGet=['username'])
    return jsonify(resp["Items"])


# Route to /syncuser will sync data from IAM to DynamoDB
@app.route("/syncuser")
def syncuser():
    syncIamUsersIntoDB()
    return jsonify({
        "sync status": "successful"
    })

# Route / will send you data
@app.route("/")
def home():
    return render_template('index.html')


@app.errorhandler(404)
def resource_not_found(e):
    return make_response(jsonify(error='Not found!'), 404)
