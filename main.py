from flask import Flask, jsonify
import boto3


app = Flask(__name__)
iam = boto3.client("iam")
dynamodb = boto3.resource('dynamodb')


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

try: 
    createdb()
except:
    pass

table = dynamodb.Table('users')


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
    return jsonify(result)


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

    return jsonify(result)


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


@app.route("/listuser")
def listuser():
    resp = table.scan(AttributesToGet=['username'])
    return jsonify(resp["Items"])


if __name__ == '__main__':
    app.run(debug=True)
