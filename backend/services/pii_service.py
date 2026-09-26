def mask_account_number(account_number):
    if not account_number:
        return "XXXX"
    account_number = str(account_number)
    if len(account_number) < 4:
        return "XXXX"
    return "XXXXXX" + account_number[-4:]


def mask_pan(pan):
    if not pan:
        return "XXXXX"
    pan = str(pan)
    if len(pan) < 4:
        return "XXXXX"
    return "XXXXX" + pan[-4:]