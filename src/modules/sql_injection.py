import requests

def login_test(url, dictionary_login):
    response = requests.post(url, data=dictionary_login)

    print(response.text)