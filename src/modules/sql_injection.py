import requests

def login_test(url, dictionary_login):
    try:
        response = requests.post(url, data=dictionary_login)
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return
