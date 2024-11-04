import openai
# openai==0.28
import os
import streamlit as st
import subprocess
from io import StringIO
import tempfile

import requests

# カスタムCSSを定義
custom_css = """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    
    /* Streamlit全体のフォントを変更 */
    html, body, [class*="css"] {
        font-family: 'monospace', sans-serif;
    }

    /* 背景色の変更 */
    .stApp {
        background-color: #f0f8ff;
    }

    /* サイドバーの背景色 */
    .css-1d391kg {  /* サイドバー全体のコンテナ */
        background-color: #87cefa;
    }

    </style>
    """

# カスタムCSSを適用
st.markdown(custom_css, unsafe_allow_html=True)

st.title("Java エラー解説チャット")

############ github用 ############
JDoodle_Client_ID = st.secrets["client_id"]
JDoodle_Client_Secret = st.secrets["client_secret"]
openai.api_key = st.secrets["api_key"]
##################################

# session_satte "openai_model"：gptモデル設定
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4"

# session_satte'chat_history'：会話履歴を保存
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# session_satte "input_history"：入力履歴保存
if 'input_history' not in st.session_state:
    st.session_state.input_history = []

# 辞書my_dict: プロンプトを格納
my_dict = {
    "簡潔に教えて": "最初に直す箇所を１つだけあげてください",
    "もう少し教えて": "プログラムのエラーを解説してください。コードは含めないでください",
    "色々知りたい": "プログラムのエラーを解説してください。必要ならば、部分的にコードを提示してください。"
}

# 解説のレベルをラジオボタンで選択
self_sys_prompt = "プログラムのエラーを解説してください。必要ならば、部分的にコードを提示してください。"

# テキストを表示（サイドバー）
st.sidebar.markdown("<h2 style='font-size: 22px;'>①解説のレベルを選択</h2>", unsafe_allow_html=True)

# ラジオボタン（サイドバー）
action = st.sidebar.radio(" ", ("簡潔に教えて", "もう少し教えて", "色々知りたい"))

if action == list(my_dict.keys())[0]:
    self_sys_prompt = my_dict[list(my_dict.keys())[0]]

if action == list(my_dict.keys())[1]:
    self_sys_prompt = my_dict[list(my_dict.keys())[1]]

if action == list(my_dict.keys())[2]:
    self_sys_prompt = my_dict[list(my_dict.keys())[2]]

# テキストを表示（サイドバー）
st.sidebar.markdown("<h2 style='font-size: 22px;'>②Javaファイルアップロード</h2>", unsafe_allow_html=True)

# ファイルアップロード（サイドバー）
uploaded_file = st.sidebar.file_uploader(" ", type=["java"])

# 関数response_generation：OpenAI APIを用いて応答生成
# 引数　error_code: コード＋エラー文、prom: システムへのプロンプト
# 返り値　full_response: 生成した解説
def response_generation(error_code, prom):
    # systemプロンプト
    print("self_sys_prompt:")
    print(prom)

    # 応答格納用変数
    full_response = ""
    message_placeholder = st.empty()

    for response in openai.ChatCompletion.create(
        model = st.session_state["openai_model"],
        messages = [
            {"role": "system", "content": prom},
            {"role": "user", "content": error_code}
        ],
        stream = True,
    ):
        full_response += response.choices[0].delta.get("content", "")
        # message_placeholder.markdown(full_response + " ")
    # message_placeholder.markdown(full_response)
    return full_response

# 関数response_generation：実験用解説生成、api使用なし
def response_generation_dummy(error_code, prom):
    # systemプロンプト
    print("self_sys_prompt:")
    print(prom)

    # 応答格納用変数
    full_response = "APIを節約中です。self_sys_promptは「"
    full_response += prom
    full_response += "」です。"
    return full_response

# 関数append_to_file：指定したファイルに書き込む
def append_to_file(text, file_path):
    # 'a'モードはファイルが存在する場合に追記し、存在しない場合は新しいファイルを作成
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(str(text) + '\n')


# 関数file_jdoo：アップロードしたファイルをjavacし、関数response_generationを呼び出す
# 引数java_code_d（ファイルの中身そのまま）, string_data_d_j（ファイルの中身string化）
# 返り値sys_response_d（コンパイル結果を元にした解説結果）
def file_jdoo(java_code_d, string_data_d_j):
    # 応答履歴格納用変数
    sys_response_d = ""

    # JDoodle APIにリクエストを送信
    api_url = "https://api.jdoodle.com/v1/execute"
    data = {
        "script": string_data_d_j,
        "language": "java",
        "versionIndex": "3",  # Javaバージョン（3 = JDK 1.8.0_66）
        "clientId": JDoodle_Client_ID,
        "clientSecret": JDoodle_Client_Secret
    }

    response = requests.post(api_url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        output = result.get("output", "No output")
        # st.code(output, language="text")

        # コンパイルエラーのチェック
        if "error" in result['output'].lower():
            # st.write("コンパイルエラー発生！")
            string_data_d_j += result['output']

            # gptへの入力格納用変数
            java_code_d += result['output']
            java_code_d += "\n"

            # user_prompt
            java_code_d += "プログラムのエラーを説明してください"
            sys_response_d = response_generation(java_code_d, self_sys_prompt)
        else:
            sys_response_d += "❤️コンパイル成功❤️\n"
            sys_response_d += result['output']
        
    else:
        st.write(f"Error: {response.status_code}")
        sys_response_d += "何らかのトラブルが発生しました"

    return sys_response_d

# 関数file_jdoo_dummy：アップロードしたファイルをjavacわざとしない！
# 引数string_data_d（ファイルの中身）、返り値sys_response_d（コンパイル結果を元にした解説結果、ではなくダミーの文言）
def file_jdoo_dummy(string_data_d):
    # 応答履歴格納用変数
    sys_response_d = "jdoodle節約ですわ"
    string_data_d += sys_response_d
    sys_response_d = response_generation_dummy(string_data_d, self_sys_prompt)
    return sys_response_d


# 関数file_check: ファイルの中身をチェック、同じだったら警告
def file_check(java_code_d):
    if java_code_d in st.session_state.input_history:
        st.warning("過去にも同じファイルが入力されましたよ")
    else:
        st.success("ファイルがアップロードされました")

    st.session_state.input_history.append(java_code_d)


# アップロードされたファイルをjdoodleでjavac
if uploaded_file:
    java_code = uploaded_file.read().decode("utf-8")

    # ファイルの中身をチェック
    # file_check(java_code)

    # 応答履歴格納用変数
    sys_response = ""

    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    string_data = stringio.read()

    # javacして、解説生成
    # sys_response = file_jdoo(java_code, string_data)

    # javacしない、解説も生成しない
    sys_response = file_jdoo_dummy(string_data)

    st.session_state.chat_history.append({"role": "assistant", "content": sys_response})
    st.session_state.chat_history.append({"role": "user", "content": string_data})
    
    append_to_file("入力：", 'memo.txt')
    append_to_file(string_data, 'memo.txt')
    append_to_file("応答：", 'memo.txt')
    append_to_file(sys_response, 'memo.txt')
    append_to_file("", 'memo.txt')

# 最新のメッセージを取得
last_user_message = None
last_assistant_message = None

for message in reversed(st.session_state.chat_history):

    if message["role"] == "assistant" and last_assistant_message is None:
        last_assistant_message = message
    elif message["role"] == "user" and last_user_message is None:
        last_user_message = message
    
    if last_user_message and last_assistant_message:
        break


# 会話履歴を新しい順に表示
for message in reversed(st.session_state.chat_history):
    
    if message["role"] == "user":
        if message == last_user_message:
            print("最新の入力（ユーザー）")
            st.image("./images/postit2_pink.png", width=100)
            st.write("最新の入力")
            st.code(message["content"], language='java')
            last_user_message = None
        else:
            print("今ここ（ユーザー）")
            st.code(message["content"], language='java')
            

    if message["role"] == "assistant":
        # if self_sys_prompt == my_dict[list(my_dict.keys())[0]]:
        #     st.markdown(list(my_dict.keys())[0])
        # elif self_sys_prompt == my_dict[list(my_dict.keys())[1]]:
        #     st.markdown(list(my_dict.keys())[1])
        # else:
        #     st.markdown(list(my_dict.keys())[2])
        if message == last_assistant_message:
            print("最新の出力（アシスタント）")
            st.write("最新の出力")
            st.write(message["content"])
            last_assistant_message = None
        else:
            print("今ここ（アシスタント）")
            st.write(message["content"])
