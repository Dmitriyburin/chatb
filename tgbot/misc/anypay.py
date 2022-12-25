import hashlib


def gen_hash(amount, payment_id, anypay_secret, anypay_shop):
    amount = str(int(amount)) + '.00'
    strsign = f"RUB:{amount}:{anypay_secret}:{anypay_shop}:{payment_id}"
    sign = hashlib.md5(strsign.encode()).hexdigest()

    strsecret = f"{anypay_shop}:{amount}:{payment_id}:{anypay_secret}"
    secret = hashlib.md5(strsecret.encode()).hexdigest()

    return sign, secret


def gen_url(amount, payment_id, desc, sign, anypay_shop):
    amount = str(int(amount)) + '.00'
    url = f'https://anypay.io/merchant?merchant_id={anypay_shop}&pay_id={payment_id}&amount={amount}&currency=RUB&desc={desc}&sign={sign}'
    return url
