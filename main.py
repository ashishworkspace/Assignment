from flask import Flask, jsonify, render_template
import boto3

app = Flask(__name__)
iam = boto3.client("iam")
dynamodb = boto3.resource('dynamodb')


#  Creating Dynamodb table of name 'users'
def createdb():
    table = dynamodb.create_table(
        TableName='users',
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'
            }

        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            }

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    table.wait_until_exists()


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

# Running the createdb() if database table is not created
try: 
    createdb()   
except:
    pass

table = dynamodb.Table('users')

      
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

if __name__ == '__main__':
    app.run(debug=True)
