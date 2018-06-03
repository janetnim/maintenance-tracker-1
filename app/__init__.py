from flask import Flask, request
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS
from functools import wraps

from .models import User, Request as RequestModel, Store

app = Flask(__name__)
api = Api(app)
CORS(app)

session = {}

requests_store = []
users = {}


def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session:
            return fn(*args, **kwargs)
        return {"message": "You must be logged in to make a request"}, 403
    return decorated_function


def find_request(request_id, user_id):
    """ Find a specific request resource based off the id and users' id """
    return [
        _request if _request['request_id'] == request_id and
        _request["user_id"] == user_id else "does_not_belong_to"
        for _request in requests_store
        if _request['request_id'] == request_id
    ]


class RequestList(Resource):
    """ Resource for list request """

    parser = reqparse.RequestParser()
    parser.add_argument('title', required=True, type=str)
    parser.add_argument('location', required=True, type=str)
    parser.add_argument('request_type', required=True)
    parser.add_argument('description')

    @login_required
    def get(self):
        """ Get all request """
        user_id = session["user_id"]
        my_requests = Store.get_user_requests(user_id)

        if my_requests:
            return {
                "requests": [
                    request.request_to_dict() for request in my_requests
                ]
            }, 200
        return {"message": "You don't have any requests yet"}, 404

    @login_required
    def post(self):
        """ Create a new request """
        user_id = session["user_id"]
        args = RequestList.parser.parse_args()

        _request = RequestModel(
            user_id=user_id, title=args['title'], location=args['location'],
            request_type=args['request_type'], description=args['description']
        )

        Store.add_request(_request)
        return {"request": _request.request_to_dict()}, 201


class Request(Resource):
    """ Requests Resource """

    @login_required
    def get(self, request_id):
        """ Get a single request resource based off its id """
        user_id = session["username"]

        _request = find_request(request_id, user_id)

        if len(_request) == 0:
            return {"message": f"request {request_id} doesn't exit."}, 404
        elif _request[0] == "does_not_belong_to":
            return {"message": "You can only view your own requests"}, 403
        return {'request': _request[0]}, 200

    @login_required
    def put(self, request_id):
        """ Update a single request resource based off its id """
        data = request.get_json()
        user_id = session["username"]
        _request = find_request(request_id, user_id)

        if len(_request) == 0:
            return {"message": f"request {request_id} doesn't exit."}, 404
        elif _request[0] == "does_not_belong_to":
            return {"message": "You can only edit your own requests"}, 403
        _request[0]['title'] = data.get('title', _request[0]['title'])
        _request[0]['location'] = data.get('location', _request[0]['location'])
        _request[0]['request_type'] = data.get(
            'request_type', _request[0]['request_type'])
        _request[0]['description'] = data.get(
            'description', _request[0]['description'])
        return {"request": _request[0]}, 200

    @login_required
    def delete(self, request_id):
        """ Delete a single request resource based off its id """
        user_id = session["username"]
        _request = find_request(request_id, user_id)

        if len(_request) == 0:
            return {"message": f"request {request_id} doesn't exit."}, 404
        elif _request[0] == "does_not_belong_to":
            return {"message": "You can only delete your own requests"}, 403
        requests_store.remove(_request[0])
        return {"message": "Your request was successfully deleted"}, 200


class UserRegistration(Resource):
    """ User Registration Resource """
    parser = reqparse.RequestParser()
    parser.add_argument('name', required=True, type=str)
    parser.add_argument('username', required=True, type=str)
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True)
    parser.add_argument('confirm_password', required=True)

    def post(self):
        """ Create a new User """
        args = UserRegistration.parser.parse_args()

        username_taken = Store.get_user_by_username(args["username"])
        email_taken = Store.get_user_by_email(args["email"])

        if username_taken:
            return {"message": "username already taken"}, 400
        elif email_taken:
            return {"message": "email already taken"}, 400
        elif args["password"] != args["confirm_password"]:
            return {
                "message": "password and confirm_password fields do not match"
            }, 400

        user = User(username=args.get("username"), name=args.get("name"),
                    email=args.get("email"), password=args.get("password"))

        Store.add_user(user)
        return {"user": user.to_dict()}, 201


class UserSignin(Resource):
    """ User Signin Resource """
    parser = reqparse.RequestParser()
    parser.add_argument('username', required=True, type=str)
    parser.add_argument('password', required=True)

    def post(self):
        """ Signin an existing User """
        args = UserSignin.parser.parse_args()
        username = args["username"]
        password = args["password"]

        user = Store.get_user_by_username(username)
        if not user:
            return {"message": f"{username} does not have an account."}, 404
        if not user.check_password(password):
            return {"message": "username or password do not match."}, 403
        session["user_id"] = user.id
        return {"message": f"you are now signed in as {username}"}, 200


class UserSignout(Resource):
    """ User Signout Resource """

    def post(self):
        """ Should pop the user in session  """
        if session:
            session.pop("user_id")
            return{"message": "You've been signed out successfully!"}, 200
        return{"message": "Your are not logged in!"}, 404


api.add_resource(RequestList, '/api/v1/users/requests/')
api.add_resource(Request, '/api/v1/users/request/<int:request_id>/')
api.add_resource(UserRegistration, '/api/v1/users/auth/signup/')
api.add_resource(UserSignin, '/api/v1/users/auth/signin/')
api.add_resource(UserSignout, '/api/v1/users/auth/signout/')
