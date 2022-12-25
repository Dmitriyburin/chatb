from flask import Flask, request
from models.database import Database

import asyncio

loop = asyncio.get_event_loop()
data = Database('mongodb://localhost:27017')
app = Flask(__name__)


@app.route('/')
def main_handler():
    return 'Hello, world!'


@app.route('/pay/anypay', methods=['POST'])
def anypay_handler():
    form_data = request.form
    print(form_data)
    sign = (form_data['sign'])
    print(sign)
    loop.run_until_complete(data.edit_paid_status(sign))
    return 'Paid!'


if __name__ == '__main__':
    app.run('0.0.0.0', 8080)
