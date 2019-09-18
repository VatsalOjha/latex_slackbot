from flask import Flask
from flask import request
import requests
import copy
import json
import time
import re
import os
import sys
import shlex
import subprocess

app = Flask(__name__)

with open(os.path.join(os.pardir, "api_keys.json")) as f:
    data = json.load(f)
    slack_token = data["slack_token"]
    slack_incoming = data["slack_incoming_token"]


latex_template_path = "template.tex"
latex_template_replace_text = "$ equation goes here $"
message_url = 'https://slack.com/api/chat.postMessage'
file_url = 'https://slack.com/api/files.upload'
delete_url = 'https://slack.com/api/chat.delete'
start_time = 0


def delete_message(data):
    header['Content-Type'] = 'application/json'
    send_message = {
            'token': slack_token,
            'channel': data["event"]["channel"],
            'ts': data["event"]["ts"]
    }
    r = requests.post(delete_url,data=json.dumps(send_message), headers=header)
def latex_doc(equation):
    """Load the LaTeX template from the global macro path, add the input
    equation to its appropriate place in the middle, and return the text to be
    compiled as a string.
    """
    with open(latex_template_path, "r") as f:
        template = f.read()

    return template.replace(latex_template_replace_text, equation)

header = {
	'Authorization': 'Bearer '+slack_token
}
def send_image(data, image_path):
    payload = {
        "token": slack_token,
        "channels": [data["event"]["channel"]]
    }
    pic = open(image_path, 'rb')
    my_file = {
        'file': ('anime.jpg', pic, 'png')
    }
    channel = data["event"]["channel"]
    send_image_cmd = f'curl -F file=@{image_path} -F channels={channel} -H "Authorization: Bearer {slack_token}" https://slack.com/api/files.upload' 
    subprocess.run(shlex.split(send_image_cmd), check=True)
    pic.close()
    return

def write_file(path, text):
    with open(path, "w") as f:
        f.write(text)

def send_latex(data, text):
    doc = latex_doc(text)
    t = time.time() # save the time for consistency across later operations
    path = "template1.tex"
    write_file(path, doc)

    # Compile the document to PDF using pdfLaTeX
    latex_cmd = "pdflatex template1.tex"
    subprocess.run(shlex.split(latex_cmd), check=True)

    # Convert the PDF to PNG
    convert_cmd = ("pdftoppm template1.pdf latex_image -png -rx 800 "
            "-ry 800")
    subprocess.run(shlex.split(convert_cmd), check=True)

    # Send the converted image to GroupMe
    send_image(data, image_path="latex_image-1.png")
    delete_message(data)


current_process = set()
#called on messages which we want to handle
def handle_event(data):
    current_process.add(json.dumps(data))
    try:
        text = data["event"]["text"]
        if data["event"]["text"].startswith("$") and data["event"]["text"].endswith("$"):
            send_latex(data, text)
        elif data["event"]["text"].startswith("[;") and data["event"]["text"].endswith(";]"):
            text = text.strip("[]; ")
            send_latex(data, text)
    except:
        print("not text")
    current_process.remove(json.dumps(data))



###############################################################################


@app.route('/event', methods=['POST'])
def incoming():
	incoming_data = request.json
	if incoming_data["event_time"] > start_time and \
        json.dumps(incoming_data) not in current_process and \
        incoming_data["token"] == slack_incoming and \
	incoming_data["event"].get("subtype") != "bot_message":
		handle_event(incoming_data)

	return "done"

if __name__ == '__main__':
	start_time = time.time()
	app.run(debug= False, host='0.0.0.0')
