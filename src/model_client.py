import requests


def ask(prompt: str, max_new_tokens: int = 256) -> str:
    # 把 Python 字典作为 JSON 发给服务端。
    response = requests.post(
        "http://127.0.0.1:8008/chat",
        json={"prompt": prompt, "max_new_tokens": max_new_tokens},
        timeout=1000,
    )
    print(response.json())
    # 如果服务端返回错误状态，抛出异常，便于定位问题。
    response.raise_for_status()
    return response.json()["answer"]


if __name__ == "__main__":
    try:
        answer = ask("请用一句话介绍星际争霸II。")
        print(answer)
    except requests.exceptions.Timeout:
        print("等待回答超时，请检查服务端终端。")
    except requests.exceptions.ConnectionError:
        print("无法连接模型服务，请先启动 model_service.py。")
    except requests.exceptions.HTTPError as error:
        print(f"服务返回错误：{error.response.status_code}")
        print(error.response.text)
