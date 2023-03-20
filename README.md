# capstone-bot

## For development

[This tutorial](https://www.twilio.com/blog/build-a-whatsapp-chatbot-with-python-flask-and-twilio) has a walkthrough similar to the instructions in this document as well as more information about WhatsApp bots.

### Requirements

- Python 3.10+ running on Linux
- Docker (if using your own self-hosted LibreTranslate)
- Git (if using your own self-hosted LibreTranslate)
- A phone with an active number and WhatsApp installed
- A [free Twilio account](https://www.twilio.com/) (set up the WhatsApp Sandbox according to the instructions in the aforementioned tutorial)
- [ngrok](https://ngrok.com/)

### Setup

#### Visual Studio Code

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

Also create `.vscode/launch.json` with the following:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_DEBUG": "1",
                "TWILIO_NUMBER": "+14155238886",
                "TWILIO_ACCOUNT_SID": "<account SID>",
                "TWILIO_AUTH_TOKEN": "<auth token>"
            },
            "args": [
                "run",
                "--debugger",
                "--port",
                "8080"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

Notice that some of the values of the environment variables are left up to you to populate:

- `TWILIO_NUMBER`: the Twilio sandbox phone number with no punctuation except for the "+" before the country code
- `TWILIO_ACCOUNT_SID`: your account SID from your Twilio Console's "Get Set Up" page (see below)
- `TWILIO_AUTH_TOKEN`: your account auth token, also from your "Get Set Up" page

![image](https://user-images.githubusercontent.com/62478826/225091129-7480cb50-223e-4e53-b801-dafcd1e3442d.png)

Now you can run the server from inside the IDE.

#### Dependencies

You will need to [create a virtual environment](https://docs.python.org/3/tutorial/venv.html) and install all required dependencies. Inside this repository, run

```bash
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
```

**Any time you add a dependency, it must be added to `requirements.txt` via**

```bash
pip freeze > requirements.txt
```

You won't need to reinstall dependencies unless they change and you won't need to recreate the virtual environment, but it must be activated each time you want to develop or run the server.

After activating the virtual environment, run

```bash
pre-commit install
```

to create a pre-commit git hook script. You should only need to do this once. Every time you commit, it may reformat your docstrings, meaning you may need to commit again. Try to keep these confined within an 80 character line; pylint will remind you but unfortunately I can't find a good way to handle the formatting.

#### LibreTranslate

Translations are provided by [LibreTranslate](https://libretranslate.com/). You can use their service if you get an API, but these instructions will assume you want to deploy your own server for your personal use.

To deploy your self-hosted LibreTranslate, first clone the repository:

```bash
git clone https://github.com/LibreTranslate/LibreTranslate
cd LibreTranslate
```

From there, build and run with

```bash
docker build -f docker/Dockerfile -t libretranslate .
docker run -it -p 5000:5000 libretranslate --api-keys
```

If you are deploying on a GPU machine with CUDA 11.2 and [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed, you can speed up translations by instead building and running with

```bash
docker-compose -f docker-compose.cuda.yml up -d --build
```

You will be able to visit the web UI for the server at http://0.0.0.0:5000.

### Running

#### In VS Code (option 1)

If you created a configuration file in VS Code, you can run with the run or debug buttons in the IDE.

#### With a script (option 2)

You may want to create your own start script called `start.sh`. Depending on your terminal emulator, you may need to change the first command (shown below is an example using the Konsole terminal emulator, the line directly beneath the shebang). Fill in the `export` statements with the account SID and auth token described under ["Setup"](https://github.com/hkcountryman/capstone-bot#visual-studio-code). It should look something like this:

```bash
#!/usr/bin/bash
konsole --hold -e "ngrok http 8080" &  # run `ngrok http 5000` in a new terminal window without closing it
export TWILIO_NUMBER="+14155238886"  # Twilio sandbox phone number
export TWILIO_ACCOUNT_SID="<account SID>"  # fill in from Twilio sandbox settings
export TWILIO_AUTH_TOKEN="<auth token>"  # fill in from Twilio sandbox settings
export LIBRETRANSLATE="http://0.0.0.0:5000"
source ./venv/bin/activate  # activate virtual environment
flask run --debugger --port 8080  # run Flask in debug mode for hot reloading while developing
```

#### Manually (option 3)

Otherwise, first set the environment variables `TWILIO_NUMBER`, `TWILIO_ACCOUNT_SID`, and `TWILIO_AUTH_TOKEN`, the values of which are described above under ["Setup"](https://github.com/hkcountryman/capstone-bot#visual-studio-code):

```bash
export TWILIO_NUMBER="+14155238886"
export TWILIO_ACCOUNT_SID="<account SID>"
export TWILIO_AUTH_TOKEN="<auth token>"
export LIBRETRANSLATE="http://0.0.0.0:5000"
```

Then, with the virtual environment active, run the server:

```bash
flask run --debugger --port 8080
```

Next, use ngrok to expose a temporary, public URL for the server:

```bash
ngrok http 8080
```

#### Connect Twilio sandbox to ngrok URL (for all options)

Set your auth token in ngrok via `ngrok authtoken <YOUR_AUTHTOKEN>`. You only need to do this once.

Copy the forwarding URL from ngrok's output (the address that is *not* http://localhost:5000) and paste this address followed by "/bot" into your Sandbox Configuration settings in your Twilio console in the "When a message comes in" field. The corresponding method should be set to "POST". It should look like this:

![image](https://user-images.githubusercontent.com/62478826/224860669-ad7b0ce5-1bd3-4803-a622-3da0ae7f0d28.png)

Now you can try texting the number you texted earlier for the Sandbox.

## To run the server (production)

### Requirements

- Python 3.10+ running on Linux
- Docker (if using your own self-hosted LibreTranslate)
- Git (if using your own self-hosted LibreTranslate)

### Setup

#### Dependencies

You will need to [create a virtual environment](https://docs.python.org/3/tutorial/venv.html) and install all required dependencies. Inside this repository, run

```bash
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
```

#### LibreTranslate

Translations are provided by [LibreTranslate](https://libretranslate.com/). You can use their service if you get an API, but these instructions will assume you want to deploy your own server for your personal use.

To deploy your self-hosted LibreTranslate, first clone the repository:

```bash
git clone https://github.com/LibreTranslate/LibreTranslate
cd LibreTranslate
```

From there, build and run with

```bash
docker build -f docker/Dockerfile -t libretranslate .
docker run -it -p 5000:5000 libretranslate --api-keys
```

If you are deploying on a GPU machine with CUDA 11.2 and [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed, you can speed up translations by instead building and running with

```bash
docker-compose -f docker-compose.cuda.yml up -d --build
```

You will be able to visit the web UI for the server at http://0.0.0.0:5000.

**Note: If you prefer, you can install and run using Python or Kubernetes. See [LibreTranslate's readme](https://github.com/LibreTranslate/LibreTranslate#readme).**

### Running


