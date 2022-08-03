# NPLinker Web Application

NPLinker web application (webapp) enables you to visualize NPLinker predictions in an interactive way.


## Run with docker

The simplest option for most users will be to run NPLinker webapp using docker, removing the need to install Python and other dependencies. If you are a Windows user, it's also the only way to run NPLinker.

To install docker, see [Docker guide](https://docs.docker.com/get-docker/).

After installing docker, see the [NPLinker wiki page](https://github.com/sdrogers/nplinker/wiki/WebappInstallation) for detailed installation and usage instructions.

## Run without docker

You can also run NPLinker webapp on Linux and MacOS in a Python environment:

```
# clone this repo
git clone https://github.com/NPLinker/nplinker-webapp.git
cd nplinker-webapp

# create a virtual environment
python -m venv env
source env/bin/activate

# install dependencies
pip install -r requirements.txt
install-nplinker-deps

# set environment variable
# nplinker.toml is your nplinker config file
export NPLINKER_CONFIG="PATH_OF_YOUR_nplniker.toml"
# for example: export NPLINKER_CONFIG="/home/nplinker/nplinker.toml"

# start webapp
bokeh serve nplinker

# NPLinker webapp will be served on http://localhost:5006/nplinker
```


## Contributing
If you want to contribute to the development of nplinker, have a look at the [contribution guidelines](CONTRIBUTING.md) and [README for developers](README.dev.md).
