# capstone-bot

[This tutorial](https://www.twilio.com/blog/build-a-whatsapp-chatbot-with-python-flask-and-twilio) has a walkthrough similar to the instructions in this document as well as more information about WhatsApp bots.

## Requirements

- Python 3.6+
- A phone with an active number and WhatsApp installed
- A [free Twilio account](https://www.twilio.com/) (set up the WhatsApp Sandbox according to the instructions in the aforementioned tutorial)
- [ngrok](https://ngrok.com/)

## Set up

### Visual Studio Code

If you're using VS Code, get the following extensions:

- ms-python.autopep8
- ms-python.isort
- ms-python.python
- ms-python.vscode-pylance
- njpwerner.autodocstring
- redhat.fabric8-analytics
- You may also want ms-toolsai.jupyter for Jupyter notebooks

Create a `.vscode/` directory and add a `settings.json` inside it. Set the relevant entries:

```json
{
    "[python]": {
        "editor.formatOnSave": true,
        "editor.formatOnPaste": true,
        "editor.formatOnType": true,
        "editor.defaultFormatter": "ms-python.autopep8",
    },
    "autopep8.args": ["-a", "-a"],
    "autopep8.importStrategy": "fromEnvironment",
    "python.formatting.provider": "none",
    "python.languageServer": "Pylance",
    "python.linting.mypyEnabled": true,
    "python.linting.mypyArgs": ["--show-error-codes"],
    "python.linting.pylintEnabled": true,
    "python.linting.pylintArgs": ["--rcfile=${workspaceFolder}/.pylintrc"],
    "autoDocstring.docstringFormat": "pep257",
    "autoDocstring.generateDocstringOnEnter": true,
}
```

Under the run and debug tab, select "create a launch.json file" and select "Python" "Flask" to create `.vscode/launch.json`. Change the value of `"args"` to `["run", "--debugger"]`. Now you can run the server from inside the IDE.

### Dependencies

You will need to [create a virtual environment](https://docs.python.org/3/tutorial/venv.html). Inside this repository, run `python3 -m venv venv` followed by, on Unix-based systems, `. ./venv/bin/activate` or, on Windows, `venv\Scripts\activate.bat`. Then install the dependencies with `pip install -r requirements.txt`. **Any time you add a dependency, it must be added to `requirements.txt` via `pip freeze > requirements.txt`.**

## Running

If you created a configuration file in VS Code, you can run with the run or debug buttons in the IDE. Otherwise, use `flask run --debugger`. Don't forget that the virtual environment needs to be activated first.

Next, use ngrok to expose a temporary, public URL for the server: `ngrok http 5000`. Copy the forwarding URL from the output (the address that is *not* http://localhost:5000) and paste this address followed by "/bot" into your Sandbox Configuration settings in your Twilio console in the "When a message comes in" field. The corresponding method should be set to "POST". It should look like this:

Now you can try texting the number you texted earlier for the Sandbox.
