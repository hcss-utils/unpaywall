# Unpaywall

This repository contains an **unpaywall** python wrapper that 
downloads metadata and raw_pdf for a given DOI as well as a bash wrapper that
runs **s2orc-doc2json** utility to parse pdfs into jsons. 

**You need to have Python, Java, and Bash installed on your system in order to use it.**

## Installation

Begin by cloning the repo, so you can get the required files:
```sh
git clone https://github.com/hcss-utils/unpaywall.git
cd unpaywall
git submodule update --init --recursive
```

In your terminal, you should now be located in your `unpaywall` folder. 

Let's install virtual environment: 

*Linux/MacOS*:
```sh
python3 -m venv env
source env/bin/activate
```

Now let's install dependencies:

```sh
pip install -r requirements.txt
pip install -e .
pip install -r s2orc-doc2json/requirements.txt
pip install -e s2orc-doc2json
```

If this command runs without any error messages, you can then move onto the next step,
which is installing Java as well as Grobid server. 

Once you have Java installed (look it up in google), run the following scripts: 

```sh
bash s2orc-doc2json/scripts/setup_grobid.sh 
bash s2orc-doc2json/scripts/run_grobid.sh # after 87% it's not stuck - you could use grobid already
```

See [s2orc-doc2json](s2orc-doc2json/README.md) for more information.

## Usage

Update [lens-scopus-wos.csv](data/processed/lens-scopus-wos.csv). Then execute [run.sh](scripts/run.sh) to parse pdfs into json (make sure you still have grobid running in another terminal tab):

```sh
cd scripts
bash run.sh
```
